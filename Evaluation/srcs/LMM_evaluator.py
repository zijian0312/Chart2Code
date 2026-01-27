import os
import sys
import json
import logging
import argparse
import base64
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import pandas as pd
import openai
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
    before_sleep_log
)

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger("API_ImageEvaluator")

# --- Load Environment Variables ---
load_dotenv()

class ExecutionStatus:
    SUCCESS = "success"
    FAILED = "failed"

# --- SYSTEM PROMPT ---
STRICT_VISUAL_SYSTEM_PROMPT = """
You are an professional STRICT and METICULOUS chart image analyst. Your task is to evaluate the visual similarity of two chart images. You must maintain an uncompromising level of professionalism and rigor. Every visual deviation, no matter how subtle, must be identified and penalized heavily. A perfect score is reserved exclusively for images that are visually indistinguishable to the human eye. Your analysis must be derived strictly and solely from the totality of the visual information present in the provided images.
"""

# --- Helper: Robust JSON Parser ---
def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Robustly extract JSON from text, handling Markdown code blocks.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON inside code blocks
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # Fallback: Try to find the first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
        raise ValueError("Could not parse JSON from response")

# --- API Call Logic (With Tenacity) ---

@retry(
    retry=retry_if_exception_type((
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.APIError,
        openai.APITimeoutError
    )),
    wait=wait_random_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(6),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def call_openai_with_retry(client: openai.OpenAI, model: str, messages: list) -> Dict[str, Any]:
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    content = completion.choices[0].message.content
    return extract_json_from_text(content)

def _call_vision_api_for_evaluation(
    api_key: str,
    base_url: str,
    model: str,
    gt_image_path: str,
    gen_image_path: str
) -> Dict[str, Any]:
    
    client = openai.OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=60.0,
        max_retries=0 
    )

    try:
        def encode_image(image_path):
            p = Path(image_path)
            if not p.exists() or p.stat().st_size == 0:
                raise ValueError(f"Image is missing or empty: {image_path}")
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')

        gt_base64 = encode_image(gt_image_path)
        gen_base64 = encode_image(gen_image_path)

        messages = [
            {"role": "system", "content": STRICT_VISUAL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                            "text": """
                            Compare Chart A (Ground Truth) and Chart B (Generated) using visual information only.

                            You are an extremely strict and professional evaluator..
                            Default assumption: the charts are NOT similar.

                            # Evaluation Dimensions (ALL required)
                            1. Visual Data Fidelity: 
                            - Relative data positions and trends
                            - Ordering, spacing, and scale consistency
                            - Alignment with axes and ticks
                            - ** Minor numeric drift without trend change → minor error**
                            - ** Major visible data deviation is a major error.**
                            - ** Wrong trend, scale, or correspondence → fatal error**

                            2. Layout & Structure
                            - Subplot count and arrangement
                            - Axes positions, aspect ratio, margins
                            - Grid, legend, colorbar, text placement and so on
                            - Overall visual composition and alignment
                            - ** Small margin or spacing differences → minor error**
                            - ** Major structural mismatch is an error.**

                            3. Color & Style
                            - Color hue consistency (exact match preferred, close match acceptable)
                            - Line style, markers, thickness, transparency
                            - ** Slight shade difference but same semantic color → minor error **
                            - ** Noticeable color/style difference = major error.**

                            4. Chart Type
                            - Chart form(bar barh line 3D heatmap contour graph wordcloudx radar and so on)
                            - Dimensionality and orientation
                            - ** Same chart type with minor stylistic differences → no penalty**
                            - ** Wrong chart type = fatal error.**

                            # Scoring Rules (MANDATORY)
                            ## Automatic 0
                            - Three or more dimensions have major errors
                            - Wrong chart type
                            - Data trend or scale is fundamentally incorrect

                            ## Hard Score Caps
                            Any error in any dimension → score ≤ 40
                            Multiple errors → score ≤ 20
                            Only completely indistinguishable charts → 100

                            ## Score Meaning
                            Score	Interpretation
                            90-100	completely identical in all visual aspects (no perceptible differences)
                            70-89	Slight deviation with minor visual differences(no major errors)
                            50-69	Minor but obvious deviation in any dimension
                            20-49	Noticeable but not critical deviation (One major error OR multiple minor errors)
                            10-39	Clear error in ≥1 dimension 
                            1-9	Severe mismatch
                            0	Fundamentally incorrect

                            # Evaluation Procedure
                            - Start from 0
                            - Identify all visible differences
                            - Classify each as minor / major / fatal
                            - Assign maximum penalty per difference
                            - Do not compensate across dimensions
                            - When uncertain, lower the score

                            # Forbidden Behaviors
                            - No “approximately correct” without justification
                            - No compensating data errors with visual similarity
                            - No tolerance for “looks similar”
                            - No score inflation

                            # Output Format
                            You MUST return a valid JSON object. Do not use markdown code blocks.
                            Format example:
                            {
                                "Final Score": 85,
                                "Summary": "Brief summary of the main issue.",
                                "Errors by Dimension": {
                                    "Data": {"score": <0-100>, "reason": "<brief explanation>"},,
                                    "Layout": {"score": <0-100>, "reason": "<brief explanation>"},
                                    "Color_Style": {"score": <0-100>, "reason": "<brief explanation>"},
                                    "Chart Type": {"score": <0-100>, "reason": "<brief explanation>"},
                                }
                            }
                        """ 

                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{gt_base64}", "detail": "high"}
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{gen_base64}", "detail": "high"}
                    }
                ]
            }
        ]

        # 调用带重试装饰器的函数
        return call_openai_with_retry(client, model, messages)

    except Exception as e:
        # 如果重试 6 次后依然失败，或者遇到非网络错误（如文件损坏），则捕获
        logger.error(f"FATAL Error processing {Path(gen_image_path).name}: {e}")
        return {"error": True, "reason": str(e), "raw_content": ""}


# --- Worker Function ---
def evaluate_single_image_pair(
    gen_file_path: Path,
    gt_file_path: Path,
    results_dir: Path,
    model_name: str,
    api_key: str,
    base_url: str
) -> Optional[Dict[str, Any]]:
    file_name = gen_file_path.name

    if not gt_file_path.exists():
        logger.warning(f"GT missing: {file_name}")
        return None 

    # 1. Check if report already exists (Skip processed)
    output_path = results_dir / f"{gen_file_path.stem}_report.json"
    if output_path.exists() and output_path.stat().st_size > 0:
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if existing_data.get("status") == ExecutionStatus.SUCCESS:
                    # logger.info(f"Skipping existing: {file_name}")
                    return {
                        "file_name": file_name,
                        "similarity_score": existing_data.get("similarity_score", 0),
                        "status": ExecutionStatus.SUCCESS,
                        "reason": existing_data.get("reason", "Skipped")
                    }
        except:
            pass 

    logger.info(f"Evaluating: {file_name}")

    api_result = _call_vision_api_for_evaluation(
        api_key, base_url, model_name, str(gt_file_path), str(gen_file_path)
    )

    # 2. Process Result
    status = ExecutionStatus.FAILED
    similarity_score = 0.0
    reason = "Unknown Error"

    if not api_result.get("error"):
        # Robust Score Extraction
        keys_to_check = ["Final Score", "score", "final_score", "final score"]
        for key in keys_to_check:
            if key in api_result:
                try:
                    similarity_score = float(api_result[key])
                    status = ExecutionStatus.SUCCESS
                    break
                except: continue
        
        reason = api_result.get("Summary", api_result.get("reason", str(api_result)))
    else:
        reason = api_result.get("reason", "API Error")

    # 3. Save Report
    pair_report = {
        "file_name": file_name,
        "status": status,
        "similarity_score": similarity_score,
        "reason": reason,
        "gt_path": str(gt_file_path),
        "gen_path": str(gen_file_path),
        "evaluation_details": api_result
    }

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pair_report, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save JSON for {file_name}: {e}")

    return {
        "file_name": file_name,
        "similarity_score": similarity_score,
        "status": status,
        "reason": reason
    }

class APIBasedImageEvaluator:
    def _generate_summary_report(self, summary_data_list, gen_dir, gt_source, output_path, model_name):
        if not summary_data_list:
            return

        df = pd.DataFrame(summary_data_list)
        successful_evals = df[df['status'] == ExecutionStatus.SUCCESS]
        
        avg_score = 0.0
        if not successful_evals.empty and 'similarity_score' in successful_evals:
             avg_score = successful_evals['similarity_score'].astype(float).mean()

        summary_stats = {
            "total_pairs": len(df),
            "successful": len(successful_evals),
            "failed": len(df) - len(successful_evals),
            "average_score": avg_score
        }

        final_report = {
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "model": model_name,
                "gen_dir": str(gen_dir)
            },
            "stats": summary_stats,
            "results": summary_data_list
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        logger.info(f"Summary Saved. Avg Score: {avg_score:.2f}")

    def evaluate_and_report(self, gen_dir, gt_json, summary_path, details_dir, model_name, workers, api_key):
        gen_path = Path(gen_dir)
        results_dir = Path(details_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Load GT
        try:
            with open(gt_json, 'r', encoding='utf-8') as f:
                gt_list = json.load(f)
            gt_base = Path(gt_json).parent
            gt_map = {}
            for i in gt_list:
                rel = i.get('GT image') or i.get('gt_image')
                if rel: gt_map[Path(rel).name] = gt_base / rel
        except Exception as e:
            logger.error(f"GT Load Error: {e}")
            sys.exit(1)

        # Build Tasks
        tasks = []
        for ext in ["*.png", "*.jpg", "*.jpeg"]:
            for f in gen_path.glob(ext):
                if f.name in gt_map:
                    tasks.append((f, gt_map[f.name]))
        
        logger.info(f"Task Queue: {len(tasks)} items. Workers: {workers}")

        # Get Base URL securely
        base_url = os.getenv('OPENAI_API_URL', "https://api.openai.com/v1")

        summary_data_list = []
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    evaluate_single_image_pair, 
                    gen, gt, results_dir, model_name, api_key, base_url
                ): gen.name for gen, gt in tasks
            }
            
            for future in as_completed(futures):
                res = future.result()
                if res: summary_data_list.append(res)

        self._generate_summary_report(summary_data_list, gen_dir, gt_json, summary_path, model_name)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gen-dir', required=True)
    parser.add_argument('--gt-json', required=True)
    parser.add_argument('--summary-json-path', required=True)
    parser.add_argument('--details-dir', required=True)
    parser.add_argument('--model-name', required=True)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--api-key', type=str, required=True) 
    
    args = parser.parse_args()

    if not args.api_key or args.api_key.strip() == "":
        logger.error("API Key is empty!")
        sys.exit(1)
    
    evaluator = APIBasedImageEvaluator()
    evaluator.evaluate_and_report(
        args.gen_dir, args.gt_json, args.summary_json_path, 
        args.details_dir, args.model_name, args.workers, args.api_key
    )

if __name__ == "__main__":
    main()

