import os
import sys
import json
import logging
import argparse
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

# --- Configure logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger("API_CodeEvaluator_8Dim_Strict")

# --- Load environment variables ---
load_dotenv()

class ExecutionStatus:
    SUCCESS = "success"
    FAILED = "failed"

STRICT_SYSTEM_PROMPT = """
You are a VERY STRICT Code-to-Visualization Auditor.

Your task is to evaluate the SIMILARITY of the FINAL RENDERED IMAGE
between Ground Truth (GT) and Generated (Gen) Python visualization code,
using ONLY STATIC CODE ANALYSIS.
You MUST reason strictly from what the code will deterministically render.

Your judgment target is:
> The FINAL VISUAL OUTPUT AS SEEN BY A HUMAN VIEWER,
not code structure, not style, not intent.

--------------------------------------------------
CORE PRINCIPLES (MANDATORY)
--------------------------------------------------

1. Judge ONLY by final rendered visual appearance.
   - If two codes differ but render visually identical output → no deduction.
   - If two codes look similar in intent but render differently → deduct.

2. If the final rendered result CANNOT be determined with certainty
   from static analysis (e.g., randomness, external state, implicit defaults),
   you MUST deduct points.

3. All scores use a DEDUCTIVE METHOD:
   - Start at 100 points per dimension.
   - Deduct strictly based on visual discrepancies.

4. Be conservative:
   - When in doubt → DEDUCT.
   - Do NOT give benefit of the doubt.

--------------------------------------------------
DEDUCTION SEVERITY GUIDE
--------------------------------------------------

- -0 pts:
  * Purely functional identity (e.g., `c='k'` vs `color='black'`)
  * Parameter changes that provably do NOT affect final pixels

- -20 to -40 pts:
  * Minor but visible deviations
    (linewidth, marker size, font size, minor text wording)

- -50 to -80 pts:
  * Clearly visible visual mismatches
    (wrong color, missing legend, different axis limits, missing grid)

- -100 pts:
  * Fundamentally different visualization
    (wrong chart type, wrong data, missing primary plot)

--------------------------------------------------
EVALUATION DIMENSIONS
--------------------------------------------------

1. DATA LOGIC (CRITICAL)
   Evaluate whether the SAME DATA is visually presented.

   - Consider:
     * Raw values
     * Ordering / sorting
     * Filtering / slicing
     * Aggregation (sum, mean, cumulative, stacked)
     * Normalization / scaling
     * Axis transforms (log, symlog)

   - Question:
     > Would a viewer perceive the same quantitative information?

2. CHART TYPE & GEOMETRY(CRITICAL)
   - Exact plotting primitive (`plot`, `scatter`, `bar`, `imshow`, `contour`, etc.)
   - Same dimensionality (1D / 2D / heatmap / 3D)
   - Same stacking / grouping / overlay logic

3. COLOR & COLOR MAPPING (CRITICAL)
   Judge FINAL COLORS, NOT parameter names.

   - For single-color plots:
     * Are the rendered colors visually identical?

   - For colormaps:
     * Same colormap family?
     * Same direction (normal vs reversed)?
     * Same normalization range (`vmin`, `vmax`)?
     * Same discrete vs continuous mapping?

   - If colors differ in the final image → deduct heavily.

4. VISUAL PARAMETERS(CRITICAL)
   - Line width
   - Marker type & size
   - Alpha / transparency
   - Linestyle
   - Edgecolor / facecolor

5. LAYOUT & STRUCTURE(CRITICAL)
   - Figure size & aspect ratio
   - Subplot grid (`nrows`, `ncols`)
   - Shared axes
   - Spacing (`tight_layout`, margins)

6. LEGEND(CRITICAL)
   - Presence or absence
   - Content text
   - Order of entries
   - Location (`loc`)
   - Frame visibility

7. GRID & AXES(CRITICAL)
   - Grid on/off
   - Which axis (x, y, both)
   - Grid style (major/minor, linestyle)
   - Axis limits and ticks

8. TEXT CONTENT(CRITICAL)
   - Title text (exact wording)
   - Axis labels
   - Annotations
   - Font size & weight if visually impactful

--------------------------------------------------
OUTPUT FORMAT (JSON ONLY, NO EXTRA TEXT)
--------------------------------------------------

{
  "dim_chart_type": {"score": 0-100, "reason": "brief, concrete"},
  "dim_data_similarity": {"score": 0-100, "reason": "brief, concrete"},
  "dim_visual_params": {"score": 0-100, "reason": "brief, concrete"},
  "dim_color_matching": {"score": 0-100, "reason": "brief, concrete"},
  "dim_layout_structure": {"score": 0-100, "reason": "brief, concrete"},
  "dim_legend_config": {"score": 0-100, "reason": "brief, concrete"},
  "dim_grid_config": {"score": 0-100, "reason": "brief, concrete"},
  "dim_text_content": {"score": 0-100, "reason": "brief, concrete"}
}
"""

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Robustly extract JSON from text, handling Markdown code blocks.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
        raise ValueError("Could not parse JSON from response")
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
def call_openai_with_retry(client: openai.OpenAI, model: str, gt_code: str, gen_code: str) -> Dict[str, Any]:
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": STRICT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"### GT CODE:\n{gt_code}\n\n### GEN CODE:\n{gen_code}"
            }
        ],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    content = completion.choices[0].message.content
    return extract_json_from_text(content)

def evaluate_single_file_8dim(
    gen_file_path: Path,
    gt_file_path: Path,
    weights: Dict[str, float],
    results_dir: Path,
    model_name: str,
    api_key: str,
    base_url: str
) -> Optional[Dict[str, Any]]:
    file_name = gen_file_path.name
    
    output_path = results_dir / f"{gen_file_path.stem}_api_report.json"
    if output_path.exists() and output_path.stat().st_size > 0:
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if 'overall_score' in existing_data:
                    return {
                        "file_name": file_name,
                        "overall_score": existing_data['overall_score'],
                        "status": ExecutionStatus.SUCCESS,
                        "skipped": True
                    }
        except:
            pass 
    try:
        gt_content = gt_file_path.read_text(encoding='utf-8')
    except:
        gt_content = gt_file_path.read_text(encoding='gbk', errors='ignore')
        
    try:
        gen_content = gen_file_path.read_text(encoding='utf-8')
    except:
        gen_content = gen_file_path.read_text(encoding='gbk', errors='ignore')

    logger.info(f"Evaluating: {file_name}")
    
    try:
        client = openai.OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=60.0,
            max_retries=0 
        )
    except Exception as e:
        logger.error(f"Client Init Error: {e}")
        return None

    try:
        api_result = call_openai_with_retry(client, model_name, gt_content, gen_content)
        api_status = ExecutionStatus.SUCCESS
    except Exception as e:
        logger.error(f"FATAL API Error for {file_name}: {e}")
        api_result = {}
        api_status = ExecutionStatus.FAILED

    file_results = {}
    overall_score = 0.0
    
    expected_dims = [
        'dim_chart_type', 'dim_data_similarity', 
        'dim_visual_params', 'dim_color_matching',
        'dim_layout_structure', 'dim_legend_config', 
        'dim_grid_config', 'dim_text_content'
    ]

    if api_status == ExecutionStatus.SUCCESS and api_result:
        for dim in expected_dims:
            dim_data = api_result.get(dim, {})
            score = float(dim_data.get('score', 0))
            reason = dim_data.get('reason', "No reason provided")
            
            file_results[dim] = {
                "status": ExecutionStatus.SUCCESS,
                "score": score,
                "reason": reason
            }
            overall_score += score * weights.get(dim, 0.0)
    else:
        for dim in expected_dims:
            file_results[dim] = {
                "status": ExecutionStatus.FAILED,
                "score": 0.0,
                "reason": "API execution failed"
            }
            
    file_results['overall_score'] = overall_score
    file_results['status'] = api_status

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(file_results, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save details {output_path}: {e}")

    summary_data = {"file_name": file_name, "overall_score": overall_score, "status": api_status}
    for k, v in file_results.items():
        if isinstance(v, dict):
            summary_data[f"{k}_score"] = v.get('score', 0.0)
            summary_data[f"{k}_status"] = v.get('status')
            
    return summary_data

class APIBasedCodeEvaluator:
    def __init__(self):
        self.weights = {
            'dim_chart_type': 0.1,
            'dim_data_similarity': 0.2,
            'dim_visual_params': 0.1,
            'dim_color_matching': 0.2,
            'dim_layout_structure': 0.1,
            'dim_legend_config': 0.1,
            'dim_grid_config': 0.1,
            'dim_text_content': 0.1
        }
        
        # Verify normalization
        total = sum(self.weights.values())
        if not (0.99 < total < 1.01):
            self.weights = {k: v/total for k, v in self.weights.items()}

    def _generate_summary_report(self, summary_data_list, gen_dir, gt_json, output_path, model_name):
        if not summary_data_list: return
        
        df = pd.DataFrame(summary_data_list)
        
        avg_scores = {}
        for dim in self.weights.keys():
            col = f'{dim}_score'
            if col in df.columns:
                # Only count successful runs
                vals = df[df.get(f'{dim}_status', ExecutionStatus.FAILED) == ExecutionStatus.SUCCESS][col]
                avg_scores[dim] = vals.mean() if not vals.empty else 0.0

        final_report = {
            "report_info": {
                "timestamp": datetime.now().isoformat(),
                "evaluator": "Strict_8Dim_Robust",
                "model": model_name
            },
            "summary_statistics": {
                "total_files": len(df),
                "successful": len(df[df['status'] == ExecutionStatus.SUCCESS]) if 'status' in df else 0,
                "avg_overall_score": df['overall_score'].mean() if not df.empty else 0.0,
                "avg_dim_scores": avg_scores
            },
            "individual_file_results": df.to_dict('records')
        }

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_report, f, indent=2, ensure_ascii=False)
            logger.info(f"Summary Report Saved: {output_path}")
        except Exception as e:
            logger.error(f"Summary Save Error: {e}")

    def evaluate_and_report(self, gen_dir, gt_json, summary_path, details_dir, model_name, workers, api_key):
        gen_path = Path(gen_dir)
        results_dir = Path(details_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Load GT Map
        try:
            with open(gt_json, 'r') as f:
                gt_list = json.load(f)
            gt_base = Path(gt_json).parent
            gt_map = {Path(i['GT code']).name: gt_base / i['GT code'] for i in gt_list if 'GT code' in i}
        except Exception as e:
            logger.error(f"GT Load Error: {e}")
            sys.exit(1)

        # Find Tasks
        tasks = []
        for f in gen_path.glob("*.py"):
            if f.name in gt_map:
                tasks.append((f, gt_map[f.name]))
        
        if not tasks:
            logger.warning("No tasks found.")
            return

        logger.info(f"Starting {len(tasks)} evaluations with {workers} workers.")
        
        # Get Base URL
        base_url = os.getenv('OPENAI_API_URL', "https://api.openai.com/v1")

        summary_data_list = []
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    evaluate_single_file_8dim, 
                    gen, gt, self.weights, results_dir, model_name, api_key, base_url
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
    parser.add_argument('--api-key', type=str, required=True, help="API Key from Bash script")
    
    args = parser.parse_args()
    
    if not args.api_key:
        logger.error("API Key missing.")
        sys.exit(1)

    evaluator = APIBasedCodeEvaluator()
    evaluator.evaluate_and_report(
        args.gen_dir, args.gt_json, args.summary_json_path, 
        args.details_dir, args.model_name, args.workers, args.api_key
    )

if __name__ == "__main__":
    main()
