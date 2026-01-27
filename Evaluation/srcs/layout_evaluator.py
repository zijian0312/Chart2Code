# layout_evaluator.py
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
import multiprocessing
import queue
import gc
import io
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

try:
    from matplotlib.contour import QuadContourSet, TriContourSet
except ImportError:
    try:
        from matplotlib.contour import QuadContourSet
        from matplotlib.tri import TriContourSet
    except ImportError:
        class TriContourSet: pass
        class QuadContourSet: pass

from matplotlib.collections import (
    PathCollection, PolyCollection, QuadMesh, LineCollection
)
from matplotlib.container import BarContainer, ErrorbarContainer, StemContainer
from matplotlib.quiver import Quiver
from matplotlib.patches import Wedge

class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class LayoutMetrics:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    error_message: str = ""

def _identify_ax_type(ax: plt.Axes) -> str:
    """Robustly identifies the primary chart type within a single Axes."""
    try:
        if ax.name == '3d':
            if any(isinstance(c, (QuadContourSet, TriContourSet)) for c in ax.collections): return '3d_contour'
            if any(isinstance(c, PathCollection) for c in ax.collections): return '3d_scatter'
            if len(ax.lines) > 0: return '3d_line'
            return '3d_plot'
        if ax.name == 'polar': return 'radar'
        if ax.containers:
            for c in ax.containers:
                if isinstance(c, BarContainer):
                    try:
                        if len(ax.get_yticks()) > len(ax.get_xticks()) and not ax.get_xaxis().get_label().get_text():
                             return 'bar'
                    except: pass
                    return 'bar'
                if isinstance(c, ErrorbarContainer): return 'errorbar'
                if isinstance(c, StemContainer): return 'stem'
        for c in ax.collections:
            if isinstance(c, Quiver): return 'quiver'
            if isinstance(c, (QuadContourSet, TriContourSet)): return 'contour'
            if isinstance(c, QuadMesh): return 'heatmap'
            if isinstance(c, PolyCollection):
                 try:
                     if len(c.get_paths()) > 0 and len(c.get_paths()[0].vertices) > 20: return 'violin' 
                 except: pass
                 return 'area'
            if isinstance(c, PathCollection): return 'scatter'
        if ax.images:
            if not ax.axis('on') or (len(ax.get_xticks()) == 0): return 'wordcloud'
            return 'heatmap'
        for p in ax.patches:
            if isinstance(p, Wedge): return 'pie'
        if ax.lines:
             if not ax.axis('on'): return 'graph'
             return 'line'
    except Exception as e:
        return 'error'
    return 'empty'

def _get_fuzzy_data_stats(ax: plt.Axes) -> Dict[str, float]:
    raw_data_blobs = []
    
    try:
        for line in ax.lines:
            x, y = line.get_data()
            if y is not None: raw_data_blobs.append(np.array(y))

        for c in ax.containers:
            if hasattr(c, 'datavalues') and c.datavalues is not None:
                raw_data_blobs.append(np.array(c.datavalues))

        for c in ax.collections:
            offsets = c.get_offsets()
            if offsets is not None and len(offsets) > 0:
                raw_data_blobs.append(offsets.flatten())
            elif isinstance(c, PolyCollection):
                 for path in c.get_paths():
                    if path.vertices is not None:
                        raw_data_blobs.append(path.vertices.flatten())
            if isinstance(c, Quiver):
                 if c.U is not None: raw_data_blobs.append(c.U.flatten())

        for img in ax.images:
            arr = img.get_array()
            if arr is not None:
                 if np.ma.is_masked(arr): raw_data_blobs.append(arr.compressed())
                 else: raw_data_blobs.append(np.array(arr).flatten())

        if not ax.containers: 
            for p in ax.patches:
                if isinstance(p, Wedge):
                    raw_data_blobs.append(np.array([p.theta2 - p.theta1]))
                elif hasattr(p, 'get_height'):
                    h = p.get_height()
                    if h is not None: raw_data_blobs.append(np.array([h]))

        full_data = []
        for blob in raw_data_blobs:
            if blob is None or blob.size == 0: continue
            try:
                valid = blob[np.isfinite(np.asanyarray(blob, dtype=float))]
                if valid.size > 0:
                    full_data.extend(valid.tolist())
            except: continue
            
        if not full_data:
            return None 

        arr = np.array(full_data)
        return {
            "count": float(len(arr)),
            "sum": float(np.sum(arr)),
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "max": float(np.max(arr))
        }

    except Exception:
        return None

def _extract_layout_data(fig: Figure, file_path: str = "") -> List[Dict[str, Any]]:
    if "/graph" in str(file_path).replace("\\", "/"):

        return [dict(nrows=1, ncols=1, row_start=0, row_end=0, col_start=0, col_end=0, type='graph', stats=None)]
    
    layout_info = []
    try:
        fig.canvas.draw()
    except Exception: pass

    for ax in fig.axes:
        try:
            spec = ax.get_subplotspec()
            if spec is None: continue
            gs = spec.get_gridspec()
            nrows, ncols = gs.get_geometry()
            row_start, row_end = spec.rowspan.start, spec.rowspan.stop - 1
            col_start, col_end = spec.colspan.start, spec.colspan.stop - 1
            
            chart_type = _identify_ax_type(ax)
            stats = _get_fuzzy_data_stats(ax) 
            
            layout_info.append(dict(
                nrows=nrows, ncols=ncols, 
                row_start=row_start, row_end=row_end, 
                col_start=col_start, col_end=col_end,
                type=chart_type,
                stats=stats 
            ))
        except Exception: continue
    return layout_info

class LayoutEvaluator:
    def __init__(self) -> None:
        self.metrics = LayoutMetrics()

    def __call__(self, gen_input: Any, gt_input: Any, gen_file_path: str = "", gt_file_path: str = "") -> LayoutMetrics:
        if gen_input is None or gt_input is None:
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = "Invalid input (None)"
            return self.metrics

        try:
            if hasattr(gen_input, 'canvas'): gen_layouts = _extract_layout_data(gen_input, gen_file_path)
            else: gen_layouts = gen_input

            if hasattr(gt_input, 'canvas'): gt_layouts = _extract_layout_data(gt_input, gt_file_path)
            else: gt_layouts = gt_input

            self._calculate_metrics(gen_layouts, gt_layouts)
        except Exception as e:
            logger.error(f"Error during layout evaluation: {e}", exc_info=True)
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = str(e)
        return self.metrics

    def _is_fuzzy_match(self, layout1: Dict, layout2: Dict, is_single_plot: bool) -> bool:

        if (layout1['nrows'] != layout2['nrows'] or 
            layout1['ncols'] != layout2['ncols'] or 
            layout1['row_start'] != layout2['row_start'] or 
            layout1['col_start'] != layout2['col_start']):
            return False

        if is_single_plot:
            return True

        if layout1['type'] != layout2['type']:
            return False

        s1 = layout1.get('stats')
        s2 = layout2.get('stats')

        if s1 is None and s2 is None: return True

        if s1 is None or s2 is None: return False
        
        if abs(s1['count'] - s2['count']) > max(2, s1['count'] * 0.05): return False

        def is_close(a, b, rel_tol=0.05, abs_tol=1e-3):
            return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

        if not is_close(s1['mean'], s2['mean']): return False
        if not is_close(s1['std'], s2['std']): return False
        
        return True

    def _calculate_metrics(self, gen_layouts: List[Dict], gt_layouts: List[Dict]) -> None:
        if not gen_layouts and not gt_layouts:
            self.metrics.precision = 1.0; self.metrics.recall = 1.0; self.metrics.f1 = 1.0; return
        if not gt_layouts or not gen_layouts:
            self.metrics.precision = 0.0; self.metrics.recall = 0.0; self.metrics.f1 = 0.0; return

        is_single_plot = (len(gen_layouts) == 1 and len(gt_layouts) == 1)

        n_correct = 0
        gt_layouts_copy = gt_layouts.copy()
        
        for g_item in gen_layouts:
            match_found = False
            for gt_item in gt_layouts_copy:
                if self._is_fuzzy_match(g_item, gt_item, is_single_plot):
                    match_found = True
                    gt_layouts_copy.remove(gt_item)
                    break
            if match_found:
                n_correct += 1
        
        self.metrics.precision = n_correct / len(gen_layouts) if gen_layouts else 1.0
        self.metrics.recall = n_correct / len(gt_layouts) if gt_layouts else 1.0
        
        if self.metrics.precision + self.metrics.recall > 0:
            self.metrics.f1 = 2 * self.metrics.precision * self.metrics.recall / (self.metrics.precision + self.metrics.recall)

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
            layout_data = _extract_layout_data(fig, code_path)
            result_queue.put({"status": "success", "data": layout_data})
    except Exception as e:
        result_queue.put({"status": "error", "msg": str(e)})
    finally:
        plt.close('all')
        gc.collect()

def execute_code_and_get_layout(code_file_path: str, timeout: int = 60):
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
    evaluator = LayoutEvaluator()
    gen_data, gen_err = execute_code_and_get_layout(str(generation_dir / file_name))
    gt_data, gt_err = execute_code_and_get_layout(str(gt_dir / file_name))
    
    if gen_data is None or gt_data is None:
        metrics = LayoutMetrics(status=ExecutionStatus.FAILED)
        metrics.error_message = f"GenErr: {gen_err}; GtErr: {gt_err}"
        return file_name, metrics
    
    return file_name, evaluator(gen_data, gt_data)

def batch_evaluate_directory(generation_dir: str, gt_dir: str, output_file: str):
    print(f"Running LayoutEvaluator (Fuzzy & Robust)...")
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

    with open(output_file, 'w') as f:
        json.dump({k: v.f1 for k, v in all_results.items()}, f, indent=2)
    print(f"Finished. Saved to {output_file}")

if __name__ == "__main__":
    if sys.platform != 'linux':
        multiprocessing.set_start_method('spawn', force=True)
    
    gen_dir = PROJECT_PATH / "generation_code"
    gt_dir = PROJECT_PATH / "gt_code"
    if gen_dir.exists():
        batch_evaluate_directory(str(gen_dir), str(gt_dir), "layout_standalone.json")

