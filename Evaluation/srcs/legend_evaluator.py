# legend_evaluator.py 
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
from matplotlib.colors import to_hex
from color_utils import calculate_color_similarity, convert_color_to_hex


class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class LegendMetrics:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    error_message: str = ""

def _get_color_safe(artist):

    try:
        if hasattr(artist, 'get_facecolor'):
            c = artist.get_facecolor()
            if isinstance(c, np.ndarray):
                if c.ndim > 1: c = c[0]
                if len(c) == 4 and c[3] == 0: return None 
            return convert_color_to_hex(c)
        
        if hasattr(artist, 'get_color'):
            return convert_color_to_hex(artist.get_color())
            
        if hasattr(artist, 'get_edgecolor'): 
             return convert_color_to_hex(artist.get_edgecolor())
             
    except Exception:
        return None
    return None

def _extract_legends_data(fig: Figure) -> List[Dict]:

    items = []
    try:
        fig.canvas.draw()
    except Exception as e:
        logger.debug(f"Canvas draw warning: {e}")

    try:
        renderer = fig.canvas.get_renderer()
        width, height = fig.get_size_inches() * fig.dpi
        if width == 0 or height == 0: width, height = 1, 1 
        
        for i, ax in enumerate(fig.axes):

            legend = ax.get_legend()
            if legend and legend.get_visible():
                try:
                    bbox = legend.get_window_extent(renderer)
                    center_x = (bbox.x0 + bbox.x1) / 2 / width
                    center_y = (bbox.y0 + bbox.y1) / 2 / height

                    content = []

                    handles = getattr(legend, 'legendHandles', getattr(legend, 'legend_handles', []))
                    texts = legend.get_texts()
                    
                    for h, t in zip(handles, texts):
                        txt = t.get_text().strip()
                        if txt:
                            content.append({
                                'text': txt, 
                                'color': _get_color_safe(h)
                            })
                    
                    if content:
                        items.append({
                            'type': 'legend',
                            'ax_index': i,
                            'center': (center_x, center_y),
                            'content': content
                        })
                except Exception as e:
                    logger.warning(f"Error processing legend: {e}")
            try:
                is_colorbar = False
                if ax.get_label() == '<colorbar>': is_colorbar = True
                
                if is_colorbar:
                    bbox = ax.get_window_extent(renderer)
                    center_x = (bbox.x0 + bbox.x1) / 2 / width
                    center_y = (bbox.y0 + bbox.y1) / 2 / height
                    
                    label = ax.get_ylabel() or ax.get_xlabel() or "colorbar"
                    
                    items.append({
                        'type': 'colorbar',
                        'ax_index': i,
                        'center': (center_x, center_y),
                        'content': [{'text': label, 'color': None}] 
                    })
            except Exception: pass
            
    except Exception as e:
        logger.error(f"Critical error in legend extraction: {e}")
        
    return items


class LegendEvaluator:
    def __init__(self, use_position: bool = True) -> None:
        self.metrics = LegendMetrics()
        self.use_position = use_position

    def __call__(self, gen_input: Any, gt_input: Any) -> LegendMetrics:
        if gen_input is None or gt_input is None:
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = "Invalid input (None)"
            return self.metrics
        
        try:

            if hasattr(gen_input, 'canvas'):
                gen_legends = _extract_legends_data(gen_input)
            else: 
                gen_legends = gen_input

            if hasattr(gt_input, 'canvas'):
                gt_legends = _extract_legends_data(gt_input)
            else:
                gt_legends = gt_input

            self._calculate_soft_metrics(gen_legends, gt_legends)
        except Exception as e:
            logger.error(f"Error during legend evaluation: {e}", exc_info=True)
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = str(e)
        return self.metrics

    def _calculate_content_score(self, gen_content: List[Dict], gt_content: List[Dict]) -> float:
        if not gen_content and not gt_content: return 1.0
        if not gen_content or not gt_content: return 0.0
        
        total_score = 0.0
        gt_pool = gt_content[:]
        
        for gen_item in gen_content:
            best_item_score = 0.0
            best_idx = -1
            
            for i, gt_item in enumerate(gt_pool):
                text_match = 1.0 if gen_item['text'] == gt_item['text'] else 0.0
                color_sim = calculate_color_similarity(gen_item['color'], gt_item['color'])
                
                if text_match:
                    item_score = 0.7 + 0.3 * color_sim
                else:
                    item_score = 0.0
                
                if item_score > best_item_score:
                    best_item_score = item_score
                    best_idx = i
            
            if best_idx != -1:
                total_score += best_item_score
                gt_pool.pop(best_idx)
        
        max_items = max(len(gen_content), len(gt_content))
        return total_score / max_items if max_items > 0 else 0.0

    def _calculate_position_score(self, gen_item: Dict, gt_item: Dict) -> float:
        if abs(gen_item['ax_index'] - gt_item['ax_index']) > 1: 
            return 0.0
        dist = np.linalg.norm(np.array(gen_item['center']) - np.array(gt_item['center']))
        return 1.0 / (1.0 + 10 * dist)

    def _calculate_soft_metrics(self, gen_items: List[Dict], gt_items: List[Dict]) -> None:
        if not gen_items and not gt_items:
            self.metrics.precision = self.metrics.recall = self.metrics.f1 = 1.0
            return
        
        total_score = 0.0
        gt_pool = gt_items[:]
        
        for gen_obj in gen_items:
            best_obj_score = 0.0
            best_idx = -1
            
            for i, gt_obj in enumerate(gt_pool):
                if gen_obj['type'] != gt_obj['type']: continue
                
                content_sim = self._calculate_content_score(gen_obj['content'], gt_obj['content'])
                
                pos_sim = 1.0
                if self.use_position:
                    pos_sim = self._calculate_position_score(gen_obj, gt_obj)
                
                if content_sim > 0:
                    obj_score = 0.8 * content_sim + 0.2 * pos_sim
                else:
                    obj_score = 0.0
                
                if obj_score > best_obj_score:
                    best_obj_score = obj_score
                    best_idx = i
            
            if best_idx != -1:
                total_score += best_obj_score
                gt_pool.pop(best_idx)
        
        precision = total_score / len(gen_items) if gen_items else 0.0
        recall = total_score / len(gt_items) if gt_items else 0.0
        
        self.metrics.precision = precision
        self.metrics.recall = recall
        if precision + recall > 0:
            self.metrics.f1 = 2 * precision * recall / (precision + recall)


def _worker_process(code_path: str, result_queue: multiprocessing.Queue):
    """Standalone worker: Runs code -> returns List[Dict]"""
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
            data = _extract_legends_data(fig)
            result_queue.put({"status": "success", "data": data})
    except Exception as e:
        result_queue.put({"status": "error", "msg": str(e)})
    finally:
        plt.close('all')
        gc.collect()

def execute_code_and_get_legends(code_file_path: str, timeout: int = 60):
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

def process_single_file_standalone(file_name: str, generation_dir: Path, gt_dir: Path, use_position: bool):
    evaluator = LegendEvaluator(use_position=use_position)
    gen_data, gen_err = execute_code_and_get_legends(str(generation_dir / file_name))
    gt_data, gt_err = execute_code_and_get_legends(str(gt_dir / file_name))
    
    if gen_data is None or gt_data is None:
        metrics = LegendMetrics(status=ExecutionStatus.FAILED)
        metrics.error_message = f"GenErr: {gen_err}; GtErr: {gt_err}"
        return file_name, metrics
    
    return file_name, evaluator(gen_data, gt_data)

def save_results_to_json(results: Dict[str, LegendMetrics], output_file: str) -> None:
    json_data = {"evaluation_info": {"timestamp": datetime.now().isoformat(), "evaluator": "LegendEvaluator_Robust"}, "individual_results": []}
    for file_name, metrics in sorted(results.items()):
        json_data["individual_results"].append({
            "file": file_name, "status": metrics.status.value, "precision": round(metrics.precision, 4), "recall": round(metrics.recall, 4), "f1": round(metrics.f1, 4), "error_message": metrics.error_message
        })
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"Saved to: {output_file}")

def batch_evaluate_directory(generation_dir: str, gt_dir: str, output_file: str, use_position: bool = True):
    print(f"Running LegendEvaluator in STANDALONE mode...")
    gen_path = Path(generation_dir)
    gt_path = Path(gt_dir)
    common_files = sorted(list(set(f.name for f in gen_path.glob("*.py")) & set(f.name for f in gt_path.glob("*.py"))))
    
    all_results = {}
    with ProcessPoolExecutor() as executor:
        future_to_file = {executor.submit(process_single_file_standalone, f, gen_path, gt_path, use_position): f for f in common_files}
        for future in as_completed(future_to_file):
            fname = future_to_file[future]
            try:
                _, metrics = future.result()
                all_results[fname] = metrics
                print(f"Processed {fname}: F1={metrics.f1:.2f}")
            except Exception as e:
                print(f"Error {fname}: {e}")

    save_results_to_json(all_results, output_file)

if __name__ == "__main__":
    if sys.platform != 'linux':
        multiprocessing.set_start_method('spawn', force=True)
    
    gen_dir = PROJECT_PATH / "generation_code"
    gt_dir = PROJECT_PATH / "gt_code"
    output_path = PROJECT_PATH / "legend_evaluation_results.json"
    
    if gen_dir.exists():
        batch_evaluate_directory(str(gen_dir), str(gt_dir), str(output_path))
