# parameter_evaluator.py 
from typing import List, Tuple, Any, Dict, Optional, Union
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
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
import matplotlib.colors as mcolors 
try:
    from scipy.optimize import linear_sum_assignment 
    HAS_SCIPY_OPT = True
except ImportError:
    HAS_SCIPY_OPT = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()
PROJECT_PATH = Path(os.environ.get("PROJECT_PATH", Path(__file__).parent.resolve()))
sys.path.insert(0, str(PROJECT_PATH))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Polygon, Wedge, PathPatch
from matplotlib.collections import PathCollection, PolyCollection, QuadMesh, LineCollection
try:
    from scipy.stats import wasserstein_distance
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class ScoreBlock:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0

@dataclass
class ParameterMetrics:
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    error_message: str = ""
    data_metrics: ScoreBlock = field(default_factory=ScoreBlock)
    visual_metrics: ScoreBlock = field(default_factory=ScoreBlock)

class NumpyJSONEncoder(json.JSONEncoder):
    """Robust JSON Encoder for NumPy types."""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int_, np.int32, np.int64)): return int(obj)
        elif isinstance(obj, (np.floating, np.float_, np.float32, np.float64)): return float(obj)
        elif isinstance(obj, np.ndarray): return obj.tolist()
        try:
            return super(NumpyJSONEncoder, self).default(obj)
        except TypeError:
            return str(obj) 

def _safe_get_scalar(value):
    try:
        if value is None: return None
        if isinstance(value, (list, np.ndarray)):
            if len(value) > 0: return value[0]
            return None
        return value
    except: return None

def _compute_dtw_distance(s1, s2):
    n, m = len(s1), len(s2)
    if n == 0 or m == 0: return float('inf')
    if n > 300: 
        idx = np.linspace(0, n-1, 300).astype(int)
        s1 = s1[idx]; n = len(s1)
    if m > 300:
        idx = np.linspace(0, m-1, 300).astype(int)
        s2 = s2[idx]; m = len(s2)

    dtw_matrix = np.full((n + 1, m + 1), float('inf'))
    dtw_matrix[0, 0] = 0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = np.linalg.norm(s1[i-1] - s2[j-1])
            dtw_matrix[i, j] = cost + min(dtw_matrix[i-1, j],   
                                          dtw_matrix[i, j-1],   
                                          dtw_matrix[i-1, j-1])  

    return dtw_matrix[n, m]

def _extract_params_from_figure(fig: Figure) -> List[Dict]:
    extracted = []

    try:
        fig.canvas.draw()
    except Exception as e:
        logger.debug(f"Canvas draw warning: {e}")

    try:
        for ax in fig.axes:
            try:
                extracted.append({
                    'type': 'axis_limits',
                    'xlim': ax.get_xlim(),
                    'ylim': ax.get_ylim()
                })
            except: pass

            try:
                xtick_objs = ax.get_xticklabels()
                if len(xtick_objs) > 0:
                    extracted.append({
                        'type': 'xticks',
                        'ticks_loc': ax.get_xticks().tolist(),
                        'fontsize': _safe_get_scalar(xtick_objs[0].get_fontsize()),
                        'rotation': _safe_get_scalar(xtick_objs[0].get_rotation()),
                    })
            except: pass

            try:
                ytick_objs = ax.get_yticklabels()
                if len(ytick_objs) > 0:
                    extracted.append({
                        'type': 'yticks',
                        'ticks_loc': ax.get_yticks().tolist(),
                        'fontsize': _safe_get_scalar(ytick_objs[0].get_fontsize()),
                        'rotation': _safe_get_scalar(ytick_objs[0].get_rotation())
                    })
            except: pass
            
            for line in ax.lines:
                try:
                    params = {
                        'type': 'line',
                        'xdata': np.array(line.get_xdata()),
                        'ydata': np.array(line.get_ydata()),
                        'linestyle': line.get_linestyle(),
                        'linewidth': float(line.get_linewidth()),
                        'marker': line.get_marker(),
                        'markersize': float(line.get_markersize()),
                        'alpha': line.get_alpha(),
                        'zorder': line.get_zorder()
                    }
                    if hasattr(line, 'get_color'): params['color'] = line.get_color()
                    if hasattr(line, 'get_zdata'):
                        z = line.get_zdata()
                        if z is not None: params['zdata'] = np.array(z)
                    
                    extracted.append(params)
                except Exception: continue
            for patch in ax.patches:
                try:
                    params = {
                        'alpha': patch.get_alpha(),
                        'zorder': patch.get_zorder(),
                        'hatch': patch.get_hatch(),
                        'fill': patch.get_fill(),
                        'facecolor': patch.get_facecolor(),
                        'edgecolor': patch.get_edgecolor()
                    }
                    
                    if isinstance(patch, Rectangle):
                        params.update({
                            'type': 'rectangle', 
                            'xy': np.array(patch.get_xy()).tolist(), 
                            'width': patch.get_width(), 
                            'height': patch.get_height()
                        })
                        extracted.append(params)
                    elif isinstance(patch, Wedge):
                        params.update({
                            'type': 'wedge', 
                            'theta1': patch.theta1, 
                            'theta2': patch.theta2, 
                            'r': patch.r,
                            'width': patch.get_width()
                        })
                        extracted.append(params)
                    elif isinstance(patch, (Polygon, PathPatch)):
                        path = patch.get_path()
                        if path:
                            verts = path.vertices
                            if len(verts) > 100: verts = verts[::int(len(verts)/100)] # Downsample
                            params.update({'type': 'polygon', 'verts': np.array(verts).tolist()})
                            extracted.append(params)
                except Exception: continue

            for col in ax.collections:
                try:
                    params = {
                        'type': 'collection', 
                        'alpha': col.get_alpha(),
                        'zorder': col.get_zorder()
                    }
                    
                    found_data = False

                    if hasattr(col, '_offsets3d') and col._offsets3d is not None: 
                         params['offsets'] = np.column_stack(col._offsets3d).tolist()
                         params['type'] = 'scatter'
                         found_data = True
                    elif hasattr(col, 'get_offsets'): 
                         offs = col.get_offsets()
                         if isinstance(offs, np.ma.MaskedArray): offs = offs.data
                         if len(offs) > 0 and np.any(offs):
                            params['offsets'] = np.array(offs).tolist()
                            params['type'] = 'scatter'
                            found_data = True

                    if not found_data and isinstance(col, PolyCollection):
                        paths = col.get_paths()
                        if paths:
                            all_verts = []
                            for p in paths[:10]: 
                                v = p.vertices
                                if len(v) > 50: v = v[::5] 
                                all_verts.append(v.tolist())
                            if all_verts:
                                params['verts'] = all_verts
                                params['type'] = 'poly_collection' 
                                found_data = True

                    if isinstance(col, QuadMesh):
                        if hasattr(col, 'get_array'):
                             arr = col.get_array()
                             if isinstance(arr, np.ma.MaskedArray): arr = arr.data
                             flat_arr = np.array(arr).flatten()
                             if len(flat_arr) > 400: flat_arr = flat_arr[::int(len(flat_arr)/400)]
                             params['array_data'] = flat_arr.tolist()
                             params['type'] = 'heatmap'
                             found_data = True

                    if not found_data and isinstance(col, LineCollection):
                        segs = col.get_segments()
                        if segs:
                            sample_segs = segs[:20] if len(segs) > 20 else segs
                            flat_segs = np.array(sample_segs).reshape(-1, 2)
                            params['segments'] = flat_segs.tolist()
                            params['type'] = 'line_collection'
                            found_data = True

                    if hasattr(col, 'get_sizes'):
                        sizes = np.array(col.get_sizes()).flatten()
                        if sizes.size > 0: params['sizes'] = sizes.tolist()
                    
                    if hasattr(col, 'get_linewidth'):
                        lw = _safe_get_scalar(col.get_linewidth())
                        if lw is not None: params['linewidth'] = float(lw)
                    
                    if hasattr(col, 'get_facecolor'):
                        fc = col.get_facecolor()
                        if len(fc) > 0: params['facecolor'] = fc[0] 

                    if found_data:
                        extracted.append(params)
                except Exception: continue

            for img in ax.images:
                try:
                    data = img.get_array()
                    if data is not None and isinstance(data, np.ndarray):
                        if data.size > 2500: 
                            step = int(np.sqrt(data.size) / 50)
                            if data.ndim == 2: data = data[::step, ::step]
                            else: data = data[::step, ::step, :]
                        params = {'type': 'image', 'image_data': np.array(data).tolist()}
                        extracted.append(params)
                except: pass

    except Exception as e:
        logger.error(f"Error traversing figure: {e}")

    return extracted


class ParameterEvaluator:
    def __init__(self) -> None:
        self.metrics = ParameterMetrics()
        
        self.DATA_KEYS = {
            'xdata', 'ydata', 'zdata', 'offsets', 'image_data', 
            'xy', 'verts', 'width', 'height', 'sizes', 'array_data', 'segments',
            'ticks_loc', 'theta1', 'theta2', 'r'
        }
        self.VISUAL_KEYS = {
            'linestyle', 'linewidth', 'marker', 'markersize', 'alpha',
            'fontsize', 'rotation', 'fontweight', 'color', 'facecolor', 'edgecolor',
            'drawstyle', 'zorder', 'hatch', 'fill',
            'xlim', 'ylim'
        }

    def __call__(self, gen_input: Any, gt_input: Any) -> ParameterMetrics:
        """Universal Entry Point."""
        if gen_input is None or gt_input is None:
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = "Invalid input (None)"
            return self.metrics
        
        try:
            gen_params = _extract_params_from_figure(gen_input) if hasattr(gen_input, 'canvas') else gen_input
            gt_params = _extract_params_from_figure(gt_input) if hasattr(gt_input, 'canvas') else gt_input
            gen_params = [self._standardize_params(p) for p in gen_params]
            gt_params = [self._standardize_params(p) for p in gt_params]
            self._calculate_metrics(gen_params, gt_params)
        except Exception as e:
            logger.error(f"Eval Error: {e}", exc_info=True)
            self.metrics.status = ExecutionStatus.FAILED
            self.metrics.error_message = str(e)
        return self.metrics

    def _standardize_params(self, params: Dict) -> Dict:
        """Standardizes colors and defaults for more accurate comparison."""
        new_params = params.copy()

        for k in ['color', 'facecolor', 'edgecolor']:
            if k in new_params and new_params[k] is not None:
                try:
                    new_params[k] = mcolors.to_rgba(new_params[k])
                except: pass 

        if 'alpha' in new_params:
            if new_params['alpha'] is None: new_params['alpha'] = 1.0

        if new_params.get('type') == 'scatter' and 'offsets' in new_params:
            try:
                offs = np.array(new_params['offsets'])
                if len(offs) > 0 and offs.ndim == 2:
                    sorted_indices = np.lexsort((offs[:, 1], offs[:, 0]))
                    new_params['offsets'] = offs[sorted_indices].tolist()
            except: pass
        return new_params

    def _calc_similarity_function(self, key: str, v1: Any, v2: Any) -> float:
        if v1 is None and v2 is None: return 1.0
        if v1 is None or v2 is None: return 0.0
        if key in ['title', 'xlabel', 'ylabel', 'xscale', 'yscale']:
            return 1.0 if str(v1).strip().lower() == str(v2).strip().lower() else 0.0
        if key in ['color', 'facecolor', 'edgecolor']:
            try:
                c1 = np.array(v1)
                c2 = np.array(v2)
                dist = np.linalg.norm(c1 - c2)
                return max(0.0, 1.0 - dist) 
            except: 
                return 1.0 if str(v1) == str(v2) else 0.0

        if key == 'rotation':
            try:
                diff = abs(float(v1) - float(v2)) % 360
                diff = min(diff, 360 - diff)
                return max(0.0, 1.0 - (diff / 45.0))
            except: return 0.0

        if isinstance(v1, (list, tuple, np.ndarray)) and isinstance(v2, (list, tuple, np.ndarray)):

            if len(v1) == 0 and len(v2) == 0: return 1.0

            if len(v1) != len(v2): return 0.0
            try:
                arr1 = np.array(v1, dtype=float).flatten()
                arr2 = np.array(v2, dtype=float).flatten()
                diff = np.linalg.norm(arr1 - arr2)
                denom = np.linalg.norm(arr1) + np.linalg.norm(arr2) + 1e-6
                if denom < 1e-9: return 1.0 if diff < 1e-9 else 0.0
                return max(0.0, 1.0 - (2 * diff / denom))
            except (ValueError, TypeError):
                return 1.0 if str(v1) == str(v2) else 0.0
        if isinstance(v1, (int, float, np.number)) and isinstance(v2, (int, float, np.number)):
            f1, f2 = float(v1), float(v2)
            if key == 'alpha': return 1.0 - min(1.0, abs(f1 - f2))
            diff = abs(f1 - f2)
            denom = max(abs(f1), abs(f2), 1.0) 
            return max(0.0, 1.0 - (diff / denom))

        return 1.0 if str(v1) == str(v2) else 0.0

    def _compare_continuous_data(self, gt, gen) -> float:
        try:
            gt, gen = np.array(gt).flatten(), np.array(gen).flatten()
            if len(gt) == 0 or len(gen) == 0: return 0.0
            if HAS_SCIPY:
                dist = wasserstein_distance(gt, gen)
                data_range = np.ptp(gt)
                if data_range == 0: data_range = 1.0
                return max(0.0, 1.0 - (dist / data_range))
            mean_sim = 1.0 - min(1.0, abs(np.mean(gt) - np.mean(gen)) / (np.mean(gt) or 1.0))
            std_sim = 1.0 - min(1.0, abs(np.std(gt) - np.std(gen)) / (np.std(gt) or 1.0))
            return (mean_sim + std_sim) / 2.0
        except: return 0.0

    def _compare_xy_curves(self, gt_x, gt_y, gen_x, gen_y) -> float:
        try:
            gt_x, gt_y = np.array(gt_x), np.array(gt_y)
            gen_x, gen_y = np.array(gen_x), np.array(gen_y)
            if len(gt_x) < 2 or len(gen_x) < 2: return 0.0
            if not (np.isclose(gt_x.min(), gen_x.min(), atol=1e-1) and np.isclose(gt_x.max(), gen_x.max(), atol=1e-1)):
                return 0.0 
            gt_mono = np.all(gt_x[1:] >= gt_x[:-1])
            gen_mono = np.all(gen_x[1:] >= gen_x[:-1])

            if gt_mono and gen_mono:
                gen_y_interp = np.interp(gt_x, np.sort(gen_x), gen_y[np.argsort(gen_x)])
                rmse = np.sqrt(np.mean((gt_y - gen_y_interp)**2))
                yrange = np.ptp(gt_y)
                if yrange == 0: yrange = 1.0
                return max(0.0, 1.0 - (rmse / yrange))
            else:
                gt_points = np.column_stack((gt_x, gt_y))
                gen_points = np.column_stack((gen_x, gen_y))
                x_scale = np.ptp(gt_x) if np.ptp(gt_x) > 0 else 1.0
                y_scale = np.ptp(gt_y) if np.ptp(gt_y) > 0 else 1.0
                gt_norm = gt_points / [x_scale, y_scale]
                gen_norm = gen_points / [x_scale, y_scale]
                dtw_dist = _compute_dtw_distance(gt_norm, gen_norm)
                avg_error = dtw_dist / (len(gt_x) + len(gen_x))
                return max(0.0, 1.0 - (avg_error / 0.1)) 
        except: return 0.0

    def _calculate_metrics(self, gen_elements: List[Dict], gt_elements: List[Dict]):
        if not gen_elements and not gt_elements:
            self.metrics.data_metrics = ScoreBlock(1.0, 1.0, 1.0)
            self.metrics.visual_metrics = ScoreBlock(1.0, 1.0, 1.0)
            return

        n_gt, n_gen = len(gt_elements), len(gen_elements)
        cost_matrix = np.zeros((n_gt, n_gen))
        d_sims = np.zeros((n_gt, n_gen))
        v_sims = np.zeros((n_gt, n_gen))

        for i, gt_elem in enumerate(gt_elements):
            for j, gen_elem in enumerate(gen_elements):
                if gt_elem.get('type') != gen_elem.get('type'):
                    cost_matrix[i, j] = 1000.0 
                    continue
                d_sim = 0.0
                try:
                    if gt_elem['type'] == 'line':
                        d_sim = self._compare_xy_curves(
                            gt_elem.get('xdata'), gt_elem.get('ydata'),
                            gen_elem.get('xdata'), gen_elem.get('ydata'))
                    elif gt_elem['type'] == 'scatter' and 'offsets' in gt_elem:
                        gt_off = np.array(gt_elem['offsets']).flatten()
                        gen_off = np.array(gen_elem.get('offsets', [])).flatten()
                        if len(gt_off) == len(gen_off):
                             d_sim = self._calc_similarity_function('offsets', gt_elem['offsets'], gen_elem.get('offsets'))
                        else:
                             d_sim = self._compare_continuous_data(gt_off, gen_off)
                    elif gt_elem['type'] in ['heatmap', 'image']:
                        gt_d = np.array(gt_elem.get('array_data', gt_elem.get('image_data', []))).flatten()
                        gen_d = np.array(gen_elem.get('array_data', gen_elem.get('image_data', []))).flatten()
                        if len(gt_d) == len(gen_d) and len(gt_d) > 0:
                            d_sim = 1.0 if np.allclose(gt_d, gen_d, atol=0.1) else max(0.0, 1.0 - np.mean(np.abs(gt_d - gen_d))/(np.ptp(gt_d)+1e-6))
                    elif gt_elem['type'] == 'axis_limits':
                        sim_x = self._calc_similarity_function('xlim', gt_elem.get('xlim'), gen_elem.get('xlim'))
                        sim_y = self._calc_similarity_function('ylim', gt_elem.get('ylim'), gen_elem.get('ylim'))
                        d_sim = (sim_x + sim_y) / 2.0
                    else:
                        keys = [k for k in self.DATA_KEYS if k in gt_elem]
                        if keys:
                            matches = sum(self._calc_similarity_function(k, gt_elem[k], gen_elem.get(k)) for k in keys)
                            d_sim = matches / len(keys)
                        else: d_sim = 1.0 
                except: d_sim = 0.0
                
                d_sims[i, j] = d_sim

                v_sim = 0.0
                vis_keys = [k for k in self.VISUAL_KEYS if k in gt_elem]
                if vis_keys:
                    v_sim = sum(self._calc_similarity_function(k, gt_elem[k], gen_elem.get(k)) for k in vis_keys) / len(vis_keys)
                else: v_sim = 1.0
                
                v_sims[i, j] = v_sim
                

                if d_sim > 0.9:
                    cost_matrix[i, j] = 1.0 - d_sim - (v_sim * 0.01) 
                else:
                    cost_matrix[i, j] = 1.0 - d_sim

        if HAS_SCIPY_OPT and n_gt > 0 and n_gen > 0:
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
        else:
            row_ind = list(range(n_gt))
            col_ind = [-1] * n_gt
            used = set()
            for i in row_ind:
                best_j, best_val = -1, -1.0
                for j in range(n_gen):
                    sim = 1.0 - cost_matrix[i, j]
                    if j not in used and sim > best_val and cost_matrix[i,j] < 100.0:
                        best_val = sim; best_j = j
                if best_j != -1:
                    col_ind[i] = best_j
                    used.add(best_j)

        final_data_scores = []
        final_vis_scores = []

        for r, c in zip(row_ind, col_ind):
            if c != -1 and cost_matrix[r, c] < 500.0:
                final_data_scores.append(d_sims[r, c])
                final_vis_scores.append(v_sims[r, c])
            else:
                final_data_scores.append(0.0)
                final_vis_scores.append(0.0)

        def get_f1(scores, total_gen, total_gt):
            tp = sum(scores)
            p = tp / total_gen if total_gen > 0 else 0.0
            r = tp / total_gt if total_gt > 0 else 0.0
            f1 = 2*p*r/(p+r) if (p+r) > 0 else 0.0
            return ScoreBlock(p, r, f1)

        self.metrics.data_metrics = get_f1(final_data_scores, n_gen, n_gt)
        self.metrics.visual_metrics = get_f1(final_vis_scores, n_gen, n_gt)


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
            params = _extract_params_from_figure(fig)
            result_queue.put({"status": "success", "data": params})
    except Exception as e:
        result_queue.put({"status": "error", "msg": str(e)})
    finally:
        plt.close('all')
        gc.collect()

def execute_code_and_get_params(code_file_path: str, timeout: int = 60):
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
    evaluator = ParameterEvaluator()
    gen_data, gen_err = execute_code_and_get_params(str(generation_dir / file_name))
    gt_data, gt_err = execute_code_and_get_params(str(gt_dir / file_name))
    
    if gen_data is None or gt_data is None:
        metrics = ParameterMetrics(status=ExecutionStatus.FAILED)
        metrics.error_message = f"GenErr: {gen_err}; GtErr: {gt_err}"
        return file_name, metrics
    
    return file_name, evaluator(gen_data, gt_data)

def save_results_to_json(results: Dict[str, ParameterMetrics], output_file: str) -> None:
    json_data = {"evaluation_info": {"timestamp": datetime.now().isoformat(), "evaluator": "ParameterEvaluator_Pro"}, "individual_results": []}
    for file_name, metrics in sorted(results.items()):
        json_data["individual_results"].append({
            "file": file_name, "status": metrics.status.value, "error_message": metrics.error_message,
            "data_metrics": {k:round(v,4) for k,v in metrics.data_metrics.__dict__.items()},
            "visual_metrics": {k:round(v,4) for k,v in metrics.visual_metrics.__dict__.items()}
        })
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
    print(f"Saved to: {output_file}")

def batch_evaluate_directory(generation_dir: str, gt_dir: str, output_file: str):
    print(f"Running ParameterEvaluator in STANDALONE mode...")
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
                print(f"Processed {fname}: DataF1={metrics.data_metrics.f1:.2f}, VisF1={metrics.visual_metrics.f1:.2f}")
            except Exception as e:
                print(f"Error {fname}: {e}")

    save_results_to_json(all_results, output_file)


if __name__ == "__main__":
    if sys.platform != 'linux':
        multiprocessing.set_start_method('spawn', force=True)
    
    gen_dir = PROJECT_PATH / "generation_code"
    gt_dir = PROJECT_PATH / "gt_code"
    output_path = PROJECT_PATH / "parameter_evaluation_results.json"
    
    if gen_dir.exists():
        batch_evaluate_directory(str(gen_dir), str(gt_dir), str(output_path))
