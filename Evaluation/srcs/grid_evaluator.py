# grid_evaluator.py 
from typing import List, Tuple, Any, Dict, Optional, Union
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
import logging
import json
from datetime import datetime
from enum import Enum
import io
import multiprocessing
import queue
import gc
import runpy
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

def robust_to_hex(color):
    try:
        if color is None: return None
        return to_hex(color, keep_alpha=False).upper()
    except Exception:
        return None

class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class GridStyle:
    visible: bool = False
    color: Optional[str] = None
    linestyle: Optional[str] = None
    linewidth: Optional[float] = None
    alpha: Optional[float] = None

@dataclass
class GridConfig:
    x_grid: GridStyle = field(default_factory=GridStyle)
    y_grid: GridStyle = field(default_factory=GridStyle)
    z_grid: Optional[GridStyle] = None 

@dataclass
class GridMetrics:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    error_message: str = ""

def _get_grid_style(lines) -> GridStyle:
    visible_lines = [line for line in lines if line.get_visible()]
    
    if not visible_lines:
        return GridStyle(visible=False)

    sample = visible_lines[0]
    return GridStyle(
        visible=True,
        color=robust_to_hex(sample.get_color()),
        linestyle=sample.get_linestyle(),
        linewidth=float(sample.get_linewidth()),
        alpha=sample.get_alpha() if sample.get_alpha() is not None else 1.0
    )

def _extract_grids_from_figure(fig: Figure) -> List[GridConfig]:
    grids = []
    try:
        fig.canvas.draw()
    except Exception as e:
        logger.debug(f"Canvas draw warning: {e}")

    for ax in fig.axes:
        try:
            x_style = _get_grid_style(ax.get_xgridlines())
            y_style = _get_grid_style(ax.get_ygridlines())

            z_style = None
            if hasattr(ax, 'zaxis'):
                try:
                    if hasattr(ax, 'get_zgridlines'):
                        z_style = _get_grid_style(ax.get_zgridlines())
                    else:
                        z_style = GridStyle(visible=False)
                except Exception:
                    z_style = GridStyle(visible=False)
            is_visible = x_style.visible or y_style.visible or (z_style and z_style.visible)
            
            if is_visible:
                grids.append(GridConfig(x_grid=x_style, y_grid=y_style, z_grid=z_style))
        except Exception as e:
            logger.warning(f"Error extracting grid from axis: {e}")
            continue
            
    return grids

class GridEvaluator:
    def __init__(self) -> None:
        self.metrics = GridMetrics()

    def __call__(self, gen_input: Any, gt_input: Any) -> GridMetrics:
        if gen_input is None or gt_input is None:
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = "Invalid input (None)"
            return self.metrics
        
        try:
            if hasattr(gen_input, 'canvas'):
                gen_grids = _extract_grids_from_figure(gen_input)
            else:
                gen_grids = self._deserialize_input(gen_input)
            if hasattr(gt_input, 'canvas'):
                gt_grids = _extract_grids_from_figure(gt_input)
            else:
                gt_grids = self._deserialize_input(gt_input)

            self._calculate_metrics(gen_grids, gt_grids)
        except Exception as e:
            logger.error(f"Error during grid evaluation: {e}", exc_info=True)
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = str(e)
        return self.metrics

    def _deserialize_input(self, input_data: List[Any]) -> List[GridConfig]:
        if input_data and isinstance(input_data[0], GridConfig):
            return input_data
        deserialized = []
        for item in input_data:
            if isinstance(item, dict):
                x_grid = GridStyle(**item.get('x_grid', {}))
                y_grid = GridStyle(**item.get('y_grid', {}))
                z_grid = GridStyle(**item.get('z_grid', {})) if item.get('z_grid') else None
                deserialized.append(GridConfig(x_grid=x_grid, y_grid=y_grid, z_grid=z_grid))
        return deserialized

    def _style_match(self, s1: Optional[GridStyle], s2: Optional[GridStyle]) -> float:
        if s1 is None and s2 is None: return 1.0
        if s1 is None or s2 is None: return 0.0
        
        if s1.visible != s2.visible: return 0.0
        if not s1.visible: return 1.0 
        
        score = 0.0
        total_checks = 4

        score += 1.0 if s1.color == s2.color else 0.0
        score += 1.0 if s1.linestyle == s2.linestyle else 0.0
        score += 1.0 if abs(s1.linewidth - s2.linewidth) < 0.1 else 0.0
        
        a1 = s1.alpha if s1.alpha is not None else 1.0
        a2 = s2.alpha if s2.alpha is not None else 1.0
        score += 1.0 if abs(a1 - a2) < 0.05 else 0.0
        
        return score / total_checks

    def _calculate_metrics(self, gen_grids: List[GridConfig], gt_grids: List[GridConfig]) -> None:
        if not gen_grids and not gt_grids:
            self.metrics.precision = 1.0; self.metrics.recall = 1.0; self.metrics.f1 = 1.0
            return
        
        if not gt_grids or not gen_grids:
            self.metrics.precision = 0.0; self.metrics.recall = 0.0; self.metrics.f1 = 0.0
            return
        
        total_score = 0.0
        matched_gt_indices = set()
        
        for gen_cfg in gen_grids:
            best_match_score = 0.0
            best_match_idx = -1
            
            for i, gt_cfg in enumerate(gt_grids):
                if i in matched_gt_indices: continue
                x_sim = self._style_match(gen_cfg.x_grid, gt_cfg.x_grid)
                y_sim = self._style_match(gen_cfg.y_grid, gt_cfg.y_grid)
                
                if gen_cfg.z_grid or gt_cfg.z_grid:
                    z_sim = self._style_match(gen_cfg.z_grid, gt_cfg.z_grid)
                    avg_sim = (x_sim + y_sim + z_sim) / 3.0
                else:
                    avg_sim = (x_sim + y_sim) / 2.0
                
                if avg_sim > best_match_score:
                    best_match_score = avg_sim
                    best_match_idx = i
            
            if best_match_idx != -1:
                total_score += best_match_score
                matched_gt_indices.add(best_match_idx)
        
        self.metrics.precision = total_score / len(gen_grids) if gen_grids else 0.0
        self.metrics.recall = total_score / len(gt_grids) if gt_grids else 0.0
        
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
            grid_data = [asdict(g) for g in _extract_grids_from_figure(fig)]
            result_queue.put({"status": "success", "data": grid_data})
    except Exception as e:
        result_queue.put({"status": "error", "msg": str(e)})
    finally:
        plt.close('all')
        gc.collect()

def execute_code_and_get_grids(code_file_path: str, timeout: int = 60):
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
    evaluator = GridEvaluator()
    gen_data, gen_err = execute_code_and_get_grids(str(generation_dir / file_name))
    gt_data, gt_err = execute_code_and_get_grids(str(gt_dir / file_name))
    
    if gen_data is None or gt_data is None:
        metrics = GridMetrics(status=ExecutionStatus.FAILED)
        metrics.error_message = f"GenErr: {gen_err}; GtErr: {gt_err}"
        return file_name, metrics
    return file_name, evaluator(gen_data, gt_data)

def batch_evaluate_directory(generation_dir: str, gt_dir: str, output_file: str):
    print(f"Running GridEvaluator in STANDALONE mode...")
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


def save_results_to_json(results: Dict[str, GridMetrics], output_file: str) -> None:
    json_data = {"evaluation_info": {"timestamp": datetime.now().isoformat(), "evaluator": "GridEvaluator_Robust"}, "individual_results": []}
    for file_name, metrics in sorted(results.items()):
        json_data["individual_results"].append({
            "file": file_name, "status": metrics.status.value,
            "precision": round(metrics.precision, 4), "recall": round(metrics.recall, 4), "f1": round(metrics.f1, 4),
            "error_message": metrics.error_message
        })
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"Evaluation results saved to: {output_file}")


if __name__ == "__main__":
    if sys.platform != 'linux':
        multiprocessing.set_start_method('spawn', force=True)
    
    gen_dir = PROJECT_PATH / "generation_code"
    gt_dir = PROJECT_PATH / "gt_code"
    if gen_dir.exists():
        batch_evaluate_directory(str(gen_dir), str(gt_dir), "grid_standalone.json")
