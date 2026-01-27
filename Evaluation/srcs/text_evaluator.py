# text_evaluator.py
from typing import List, Tuple, Any, Dict, Optional, Union
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
from dataclasses import dataclass
import logging
import json
from datetime import datetime
from enum import Enum
import io
import multiprocessing
import queue
import gc
import runpy
import numpy as np
from scipy.optimize import linear_sum_assignment
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stdout, redirect_stderr

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()
PROJECT_PATH = Path(os.environ.get("PROJECT_PATH", Path(__file__).parent.resolve()))
sys.path.insert(0, str(PROJECT_PATH))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from Levenshtein import ratio as levenshtein_ratio


class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class TextMetrics:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    error_message: str = ""

def _extract_texts_from_figure(fig: Figure) -> Dict[str, List[Dict[str, Any]]]:

    texts = {
        "title": [], "xlabel": [], "ylabel": [], "tick_label": [],
        "suptitle": [], "legend_text": [], "annotation": [], "offset_text": []
    }

    try:
        fig.canvas.draw()
    except Exception as e:
        logger.debug(f"Canvas draw warning: {e}")

    inv_fig_trans = fig.transFigure.inverted()

    def _get_item(txt_obj) -> Optional[Dict[str, Any]]:
        try:
            content = txt_obj.get_text()
            if content and content.strip():
                try:
                    transform = txt_obj.get_transform()
                    pos_pixels = transform.transform(txt_obj.get_position())
                    pos_norm = inv_fig_trans.transform(pos_pixels)
                except Exception:

                    pos_norm = np.array([0.0, 0.0])

                return {'text': content.strip(), 'pos': pos_norm}
        except Exception:
            pass
        return None

    try:
        if hasattr(fig, '_suptitle') and fig._suptitle:
            if item := _get_item(fig._suptitle): texts["suptitle"].append(item)

        for ax in fig.axes:
            if item := _get_item(ax.title): texts["title"].append(item)
            if item := _get_item(ax.xaxis.label): texts["xlabel"].append(item)
            if item := _get_item(ax.yaxis.label): texts["ylabel"].append(item)
            if hasattr(ax, 'zaxis'): 
                if item := _get_item(ax.zaxis.label): texts["ylabel"].append(item) 
            try:
                if item := _get_item(ax.xaxis.get_offset_text()): texts["offset_text"].append(item)
                if item := _get_item(ax.yaxis.get_offset_text()): texts["offset_text"].append(item)
            except: pass
            try:
                for label in ax.get_xticklabels() + ax.get_yticklabels():
                    if item := _get_item(label): texts["tick_label"].append(item)
                if hasattr(ax, 'get_zticklabels'): 
                    for label in ax.get_zticklabels():
                        if item := _get_item(label): texts["tick_label"].append(item)
            except: pass
            if legend := ax.get_legend():
                for text_obj in legend.get_texts():
                    if item := _get_item(text_obj): texts["legend_text"].append(item)

            for text_obj in ax.texts:
                if item := _get_item(text_obj): texts["annotation"].append(item)
    
    except Exception as e:
        logger.error(f"Error traversing figure texts: {e}")

    return {k: v for k, v in texts.items() if v}


class TextEvaluator:
    def __init__(self) -> None:
        self.metrics = TextMetrics()

    def __call__(self, gen_input: Any, gt_input: Any) -> TextMetrics:

        if gen_input is None or gt_input is None:
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = "Invalid input (None)"
            return self.metrics
        
        try:
            if hasattr(gen_input, 'canvas'): 
                gen_texts = _extract_texts_from_figure(gen_input)
            else:
                gen_texts = gen_input 
            if hasattr(gt_input, 'canvas'):
                gt_texts = _extract_texts_from_figure(gt_input)
            else:
                gt_texts = gt_input

            self._calculate_metrics(gen_texts, gt_texts)
        except Exception as e:
            logger.error(f"Error during text evaluation: {e}", exc_info=True)
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = str(e)
        return self.metrics

    def _calculate_metrics(self, generation_texts: Dict[str, List[Dict]], gt_texts: Dict[str, List[Dict]]) -> None:

        if not generation_texts and not gt_texts:
            self.metrics.precision = 1.0; self.metrics.recall = 1.0; self.metrics.f1 = 1.0
            return

        total_similarity_score = 0.0
        total_gt_text_count = sum(len(texts) for texts in gt_texts.values())
        total_gen_text_count = sum(len(texts) for texts in generation_texts.values())

        all_categories = set(gt_texts.keys()) | set(generation_texts.keys())

        for category in all_categories:
            gt_list = gt_texts.get(category, [])
            gen_list = generation_texts.get(category, [])
            
            if not gt_list or not gen_list:
                continue
            
            n_gt = len(gt_list)
            n_gen = len(gen_list)
            cost_matrix = np.ones((n_gt, n_gen)) 

            for i, gt_item in enumerate(gt_list):
                for j, gen_item in enumerate(gen_list):
                    gt_txt = gt_item['text']
                    gen_txt = gen_item['text']

                    text_sim = levenshtein_ratio(gen_txt, gt_txt)
                    final_score = text_sim
                    if category == 'annotation' and text_sim > 0.8:
                        gt_pos = np.array(gt_item['pos'])
                        gen_pos = np.array(gen_item['pos'])

                        dist = np.linalg.norm(gen_pos - gt_pos)
                        
                        pos_sim = np.exp(- (dist**2) / (2 * (0.2**2)))
                        
                        final_score = 0.7 * text_sim + 0.3 * pos_sim
                    cost_matrix[i, j] = 1.0 - final_score
            row_ind, col_ind = linear_sum_assignment(cost_matrix)

            current_category_score = 0.0
            for r, c in zip(row_ind, col_ind):

                score = 1.0 - cost_matrix[r, c]
                current_category_score += score
            
            total_similarity_score += current_category_score

        self.metrics.precision = total_similarity_score / total_gen_text_count if total_gen_text_count > 0 else 1.0 if not gt_texts else 0.0
        self.metrics.recall = total_similarity_score / total_gt_text_count if total_gt_text_count > 0 else 1.0 if not generation_texts else 0.0
        
        if self.metrics.precision + self.metrics.recall > 0:
            self.metrics.f1 = 2 * self.metrics.precision * self.metrics.recall / (self.metrics.precision + self.metrics.recall)
        else:
            self.metrics.f1 = 0.0


def _worker_process(code_path: str, result_queue: multiprocessing.Queue):
    try:
        f = io.StringIO()
        with redirect_stdout(f), redirect_stderr(f):
            plt.close('all')
            matplotlib.rc_file_defaults()
            runpy.run_path(str(code_path), run_name='__main__')
            
            fig_nums = plt.get_fignums()
            if not fig_nums:
                result_queue.put({"status": "error", "msg": "No figure produced"})
                return
            
            fig = plt.figure(fig_nums[-1])
            text_data = _extract_texts_from_figure(fig)
            result_queue.put({"status": "success", "data": text_data})
    except Exception as e:
        result_queue.put({"status": "error", "msg": str(e)})
    finally:
        plt.close('all')
        gc.collect()

def execute_code_and_get_texts(code_file_path: str, timeout: int = 60):
    if not os.path.exists(code_file_path): return None, "File not found"
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=_worker_process, args=(code_file_path, q))
    try:
        p.start()
        res = q.get(timeout=timeout)
        p.join(timeout=1)
        if res["status"] == "success": return res["data"], None
        else: return None, res["msg"]
    except queue.Empty:
        p.terminate(); p.join()
        return None, f"Execution timed out (> {timeout} seconds)"
    except Exception as e:
        if p.is_alive(): p.terminate()
        return None, f"Executor error: {e}"

def process_single_file_standalone(file_name: str, generation_dir: Path, gt_dir: Path):
    evaluator = TextEvaluator()
    gen_data, gen_err = execute_code_and_get_texts(str(generation_dir / file_name))
    gt_data, gt_err = execute_code_and_get_texts(str(gt_dir / file_name))
    
    if gen_data is None or gt_data is None:
        metrics = TextMetrics(status=ExecutionStatus.FAILED)
        metrics.error_message = f"GenErr: {gen_err}; GtErr: {gt_err}"
        return file_name, metrics
    
    return file_name, evaluator(gen_data, gt_data)

def batch_evaluate_directory(generation_dir: str, gt_dir: str, output_file: str):
    print(f"Running TextEvaluator in STANDALONE mode...")
    gen_path = Path(generation_dir)
    gt_path = Path(gt_dir)
    common_files = sorted(list(set(f.name for f in gen_path.glob("*.py")) & set(f.name for f in gt_path.glob("*.py"))))
    
    all_results = {}
    with ProcessPoolExecutor() as executor:
        future_to_file = {executor.submit(process_single_file_standalone, f, gen_path, gt_path): f for f in common_files}
        for future in as_completed(future_to_file):
            fname = future_to_file[future]
            try:
                _, metrics = future.result()
                all_results[fname] = metrics
                # Simple progress log
                if len(all_results) % 10 == 0:
                    print(f"Processed {len(all_results)}/{len(common_files)} files...")
            except Exception as e:
                print(f"Error {fname}: {e}")

    save_results_to_json(all_results, output_file)


def save_results_to_json(results: Dict[str, TextMetrics], output_file: str) -> None:
    json_data = {"evaluation_info": {"timestamp": datetime.now().isoformat(), "evaluator": "TextEvaluator_Robust"}, "individual_results": []}
    for file_name, metrics in sorted(results.items()):
        json_data["individual_results"].append({
            "file": file_name, "status": metrics.status.value,
            "precision": round(metrics.precision, 4), "recall": round(metrics.recall, 4), "f1": round(metrics.f1, 4),
            "error_message": metrics.error_message
        })
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    if sys.platform != 'linux':
        multiprocessing.set_start_method('spawn', force=True)
    
    gen_dir = PROJECT_PATH / "generation_code"
    gt_dir = PROJECT_PATH / "gt_code"
    output_path = PROJECT_PATH / "text_evaluation_results.json"
    
    if gen_dir.exists():
        batch_evaluate_directory(str(gen_dir), str(gt_dir), str(output_path))
