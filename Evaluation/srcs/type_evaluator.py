# type_evaluator.py 
from typing import List, Tuple, Any, Dict, Optional, Union
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
from dataclasses import dataclass
import logging
import json
from datetime import datetime
import runpy
from enum import Enum
import io
import multiprocessing
import queue
import gc
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

try:
    from matplotlib.contour import QuadContourSet, TriContourSet
except ImportError:
    try:
        from matplotlib.contour import QuadContourSet
        from matplotlib.tri import TriContourSet
    except ImportError:
        class TriContourSet: pass
        class QuadContourSet: pass

from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Wedge, Polygon, PathPatch
from matplotlib.collections import (
    PathCollection, PolyCollection, QuadMesh, LineCollection, EllipseCollection
)
from matplotlib.container import BarContainer, ErrorbarContainer, StemContainer
from matplotlib.quiver import Quiver
from matplotlib.image import AxesImage

class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class ChartTypeMetrics:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    error_message: str = ""


def _extract_chart_types_from_figure(fig: Figure) -> Dict[str, int]:

    detected_types = set()

    try:
        fig.canvas.draw()
    except Exception as e:
        logger.debug(f"Canvas draw warning: {e}")

    try:
        for ax in fig.axes:
            if ax.name == '3d':
                has_3d_scatter = any(isinstance(c, PathCollection) for c in ax.collections)
                has_3d_poly = any('Poly3DCollection' in str(type(c)) for c in ax.collections)
                has_3d_line = len(ax.lines) > 0
                has_3d_contour = any(isinstance(c, (QuadContourSet, TriContourSet)) for c in ax.collections)

                if has_3d_contour: detected_types.add('3d_contour')
                if has_3d_scatter: detected_types.add('3d_scatter')

                if has_3d_poly:
                    detected_types.add('3d_surface_or_bar') 
                
                if has_3d_line and not has_3d_scatter:
                    detected_types.add('3d_line')
                continue
            if ax.name == 'polar':
                if len(ax.lines) > 0 or len(ax.collections) > 0:
                    detected_types.add('radar')
                if ax.containers:
                    detected_types.add('polar_bar')
                continue

            if ax.containers:
                for container in ax.containers:
                    if isinstance(container, BarContainer):
                        x_labels = [l.get_text() for l in ax.get_xticklabels() if l.get_text()]
                        y_labels = [l.get_text() for l in ax.get_yticklabels() if l.get_text()]
                        
                        def is_numeric(labels):
                            if not labels: return True
                            return all(l.replace('.', '', 1).replace('-', '', 1).isdigit() for l in labels)
                        if y_labels and not is_numeric(y_labels) and (not x_labels or is_numeric(x_labels)):
                            detected_types.add('barh')
                        else:
                            detected_types.add('bar')
                            
                    elif isinstance(container, ErrorbarContainer):
                        detected_types.add('errorbar')
                    elif isinstance(container, StemContainer):
                        detected_types.add('stem')
            for collection in ax.collections:
                if isinstance(collection, Quiver):
                    detected_types.add('quiver')
                
                elif isinstance(collection, (QuadContourSet, TriContourSet)):
                    detected_types.add('contourf' if collection.filled else 'contour')

                elif isinstance(collection, QuadMesh):
                    detected_types.add('heatmap')

                elif isinstance(collection, PolyCollection):
                    is_violin = False
                    try:
                        if len(collection.get_paths()) > 0:

                            if len(collection.get_paths()[0].vertices) > 20: 
                                detected_types.add('violin')
                                is_violin = True
                    except: pass
                    
                    if not is_violin:
                        detected_types.add('area') 

                elif isinstance(collection, PathCollection):
                    if 'errorbar' not in detected_types:
                        detected_types.add('scatter')
            if ax.images:
                spines_visible = any(spine.get_visible() for spine in ax.spines.values())
                has_ticks = len(ax.get_xticks()) > 0 or len(ax.get_yticks()) > 0
                
                if not spines_visible and not has_ticks:
                     detected_types.add('wordcloud')
                elif 'heatmap' not in detected_types:
                     detected_types.add('heatmap') 
            for patch in ax.patches:
                if isinstance(patch, Wedge):
                    detected_types.add('pie')
                elif isinstance(patch, PathPatch):

                    if len(ax.lines) > 0 and 'bar' not in detected_types:
                        detected_types.add('boxplot')
            if ax.lines:
            
                complex_types = {'violin', 'errorbar', 'boxplot', 'stem', 'radar', 'quiver'}
                if not detected_types.intersection(complex_types):
                    detected_types.add('line')

            has_scatter = 'scatter' in detected_types
            has_lines_col = any(isinstance(c, LineCollection) for c in ax.collections)
            axis_off = not ax.axis('on')
            
            if has_scatter and has_lines_col and axis_off:
                detected_types.add('graph')
                if 'scatter' in detected_types: detected_types.remove('scatter')

    except Exception as e:
        logger.error(f"Error extracting chart types: {e}")
    return {chart_type: 1 for chart_type in detected_types}


class ChartTypeEvaluator:
    def __init__(self) -> None:
        self.metrics = ChartTypeMetrics()

    def __call__(self, gen_input: Any, gt_input: Any) -> ChartTypeMetrics:

        if gen_input is None or gt_input is None:
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = "Invalid input (None)"
            return self.metrics
        
        try:
            if hasattr(gen_input, 'canvas'): 
                gen_types = _extract_chart_types_from_figure(gen_input)
            else: # Dict
                gen_types = gen_input
            if hasattr(gt_input, 'canvas'):
                gt_types = _extract_chart_types_from_figure(gt_input)
            else:
                gt_types = gt_input

            self._calculate_metrics(gen_types, gt_types)
        except Exception as e:
            logger.error(f"Error during chart type evaluation: {e}", exc_info=True)
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = str(e)
        return self.metrics

    def _calculate_metrics(self, generation_chart_types: Dict[str, int], gt_chart_types: Dict[str, int]) -> None:
        if not generation_chart_types and not gt_chart_types:
            self.metrics.precision = 1.0; self.metrics.recall = 1.0; self.metrics.f1 = 1.0
            return
            
        gen_types_set = set(generation_chart_types.keys())
        gt_types_set = set(gt_chart_types.keys())

        n_correct = len(gen_types_set.intersection(gt_types_set))
        total_generated = len(gen_types_set)
        total_gt = len(gt_types_set)

        self.metrics.precision = n_correct / total_generated if total_generated > 0 else (1.0 if not gt_types_set else 0.0)
        self.metrics.recall = n_correct / total_gt if total_gt > 0 else (1.0 if not gen_types_set else 0.0)
        
        if self.metrics.precision + self.metrics.recall > 0:
            self.metrics.f1 = 2 * self.metrics.precision * self.metrics.recall / (self.metrics.precision + self.metrics.recall)
        else:
            self.metrics.f1 = 0.0


def _worker_process(code_path: str, result_queue: multiprocessing.Queue):
    """Standalone Worker: Runs code -> returns extracted Dict"""
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
            type_data = _extract_chart_types_from_figure(fig)
            result_queue.put({"status": "success", "data": type_data})
    except Exception as e:
        result_queue.put({"status": "error", "msg": str(e)})
    finally:
        plt.close('all')
        gc.collect()

def execute_code_and_get_types(code_file_path: str, timeout: int = 60):
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
    evaluator = ChartTypeEvaluator()
    # Standalone mode: get Dicts
    gen_data, gen_err = execute_code_and_get_types(str(generation_dir / file_name))
    gt_data, gt_err = execute_code_and_get_types(str(gt_dir / file_name))
    
    if gen_data is None or gt_data is None:
        metrics = ChartTypeMetrics(status=ExecutionStatus.FAILED)
        metrics.error_message = f"GenErr: {gen_err}; GtErr: {gt_err}"
        return file_name, metrics
    
    return file_name, evaluator(gen_data, gt_data)

def save_results_to_json(results: Dict[str, ChartTypeMetrics], output_file: str) -> None:
    json_data = {"evaluation_info": {"timestamp": datetime.now().isoformat(), "evaluator": "ChartTypeEvaluator_Advanced"}, "individual_results": []}
    for file_name, metrics in sorted(results.items()):
        json_data["individual_results"].append({
            "file": file_name, "status": metrics.status.value, "precision": round(metrics.precision, 4), "recall": round(metrics.recall, 4), "f1": round(metrics.f1, 4), "error_message": metrics.error_message
        })
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"Saved to: {output_file}")

def batch_evaluate_directory(generation_dir: str, gt_dir: str, output_file: str):
    print(f"Running ChartTypeEvaluator in STANDALONE mode...")
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
                print(f"Processed {fname}: F1={metrics.f1:.2f}")
            except Exception as e:
                print(f"Error {fname}: {e}")

    save_results_to_json(all_results, output_file)


if __name__ == "__main__":
    if sys.platform != 'linux':
        multiprocessing.set_start_method('spawn', force=True)
    
    gen_dir = PROJECT_PATH / "generation_code"
    gt_dir = PROJECT_PATH / "gt_code"
    output_path = PROJECT_PATH / "type_evaluation_results.json"
    
    if gen_dir.exists():
        batch_evaluate_directory(str(gen_dir), str(gt_dir), str(output_path))
