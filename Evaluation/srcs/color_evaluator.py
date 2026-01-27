# color_evaluator.py
# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
from collections import defaultdict, Counter
import logging
import os
import sys
import json
import io
import runpy
import hashlib
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from datetime import datetime
from contextlib import redirect_stdout
from dotenv import load_dotenv
from concurrent.futures import ProcessPoolExecutor, TimeoutError, as_completed
from dataclasses import dataclass
from enum import Enum

try:
    import color_utils
except ImportError:
    logging.warning("Could not import 'color_utils'. Defining fallback functions.")
    class color_utils:
        @staticmethod
        def convert_color_to_hex(c): return None
        @staticmethod
        def calculate_color_similarity(a, b): return 0.0

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()
PROJECT_PATH = Path(os.environ.get("PROJECT_PATH", Path(__file__).parent.resolve()))
sys.path.insert(0, str(PROJECT_PATH))

TYPE_WEIGHTS = {
    'patch_face': 1.0,         
    'line_color': 1.0,         
    'scatter_color': 1.0,     
    'text_color': 1.0,        
    'colormap_sampling': 1.2, 
    'edge_color': 0.5,         
    'axes_bg': 0.1,            
    'figure_bg': 0.1,          
    'title': 0.1,              
    'label': 0.1             
}
DEFAULT_WEIGHT = 0.1

TYPE_MAPPING = {
    'line': 'line_color',
    'patch': 'patch_face',
    'collection': 'scatter_color', 
    'image': 'colormap_sampling',  
    'text': 'text_color'
}
# ==========================================

class GeoSignature:

    @staticmethod
    def _safe_numpy_array(data: Any) -> np.ndarray:
        try:
            return np.array(data)
        except (ValueError, Warning):
            try:
                return np.array(data, dtype=object)
            except:
                return np.array([])

    @staticmethod
    def _hash_array(arr: np.ndarray) -> str:
        try:
            if np.issubdtype(arr.dtype, np.number):
                rounded = np.round(arr, decimals=4)
                return hashlib.md5(rounded.tobytes()).hexdigest()
            else:
                return hashlib.md5(str(arr).encode('utf-8')).hexdigest()
        except:
            return "invalid_data"

    @staticmethod
    def _get_feature_vector(arr: np.ndarray) -> np.ndarray:

        try:
            if arr.size == 0: return np.zeros(5)
            
            if arr.dtype == object:
                 return np.array([0, 0, 0, 0, arr.size])

            if arr.ndim == 1: arr = arr.reshape(-1, 1)
            
            mean = np.mean(arr, axis=0)
            std = np.std(arr, axis=0)
            
            feat = np.zeros(5)
            feat[0] = mean[0] if mean.size > 0 else 0
            feat[1] = mean[1] if mean.size > 1 else 0
            feat[2] = std[0] if std.size > 0 else 0
            feat[3] = std[1] if std.size > 1 else 0
            feat[4] = arr.shape[0]
            return feat
        except:
            return np.zeros(5)

    @staticmethod
    def get_signature(artist: Any) -> Tuple[str, str, np.ndarray]:
        """
        返回: (Type, Hash, FeatureVector)
        """
        artist_type = "unknown"
        sig_hash = ""
        feature_vec = np.zeros(5)

        try:
            if isinstance(artist, matplotlib.lines.Line2D):
                artist_type = "line"
                if hasattr(artist, 'get_data_3d'):
                    x, y, z = artist.get_data_3d()
                    data_matrix = np.column_stack((x, y, z))
                else:
                    x, y = artist.get_data()
                    data_matrix = np.column_stack((x, y))
                
                if len(data_matrix) > 100:
                    idx = np.linspace(0, len(data_matrix)-1, 100).astype(int)
                    data_summary = data_matrix[idx]
                else:
                    data_summary = data_matrix
                
                sig_hash = GeoSignature._hash_array(data_summary)
                feature_vec = GeoSignature._get_feature_vector(data_summary)

            elif isinstance(artist, matplotlib.patches.Patch):
                artist_type = "patch"
                path = artist.get_path()
                transform = artist.get_patch_transform()
                verts = transform.transform(path.vertices)
                sig_hash = GeoSignature._hash_array(verts)
                feature_vec = GeoSignature._get_feature_vector(verts)

            elif isinstance(artist, matplotlib.collections.Collection):
                artist_type = "collection"
                offsets = artist.get_offsets()
                
                if hasattr(artist, 'U') and hasattr(artist, 'V'):
                    U, V = artist.U, artist.V
                    if U is not None and V is not None:
                        U_arr = np.ma.filled(U, 0)
                        V_arr = np.ma.filled(V, 0)
                        combined = np.concatenate([np.mean(offsets, axis=0), [np.mean(U_arr), np.mean(V_arr)]])
                        sig_hash = GeoSignature._hash_array(combined)
                        feature_vec = GeoSignature._get_feature_vector(offsets)
                    else:
                        sig_hash = GeoSignature._hash_array(offsets)
                        feature_vec = GeoSignature._get_feature_vector(offsets)
                
                elif hasattr(artist, 'get_verts'):
                    verts = artist.get_verts()
                    if len(verts) > 0:
                        try:
                            centroids = []
                            for v in verts:
                                v_arr = np.array(v)
                                if v_arr.size > 0:
                                    centroids.append(np.mean(v_arr, axis=0))
                            
                            flat_verts = GeoSignature._safe_numpy_array(centroids)
                            
                            if len(flat_verts) > 200: 
                                flat_verts = flat_verts[::len(flat_verts)//200]
                            
                            sig_hash = GeoSignature._hash_array(flat_verts)
                            feature_vec = GeoSignature._get_feature_vector(flat_verts)
                        except:
                             sig_hash = "complex_3d_collection"
                elif len(offsets) > 0:
                    sig_hash = GeoSignature._hash_array(offsets)
                    feature_vec = GeoSignature._get_feature_vector(offsets)
            elif isinstance(artist, matplotlib.image.AxesImage):
                artist_type = "image"
                data = artist.get_array()
                extent = artist.get_extent()
                
                if data is not None:
                    if np.ma.is_masked(data):
                        data = data.filled(0)
                    if data.size > 1000:
                        flat = data.flatten()
                        sample = flat[::max(1, len(flat)//100)]
                        sig_hash = GeoSignature._hash_array(sample)
                    else:
                        sig_hash = GeoSignature._hash_array(data)
                
                data_mean = np.mean(data) if data is not None else 0
                feature_vec = np.array([extent[0], extent[2], extent[1]-extent[0], extent[3]-extent[2], data_mean])
            elif isinstance(artist, matplotlib.text.Text):
                artist_type = "text"
                txt = artist.get_text().strip()
                pos = artist.get_position()
                if txt:
                    raw_str = f"{txt}_{pos[0]:.2f}_{pos[1]:.2f}"
                    sig_hash = hashlib.md5(raw_str.encode('utf-8')).hexdigest()
                    feature_vec = np.array([pos[0], pos[1], 0, 0, len(txt)])

        except Exception:
            pass

        return artist_type, sig_hash, feature_vec

def extract_elements_with_signature(fig: Figure) -> Dict[str, List[Dict]]:
    elements = defaultdict(list)
    for ax in fig.axes:
        all_artists = ax.lines + ax.patches + ax.collections + ax.images + ax.texts
        for artist in all_artists:
            ftype, fhash, fvec = GeoSignature.get_signature(artist)
            if ftype == "unknown" or not fhash: continue

            color = None
            if hasattr(artist, 'cmap') and artist.cmap is not None:
                 try:
                     cmap = artist.cmap
                     c1 = color_utils.convert_color_to_hex(cmap(0.2))
                     c2 = color_utils.convert_color_to_hex(cmap(0.5))
                     c3 = color_utils.convert_color_to_hex(cmap(0.8))
                     if c1 and c2 and c3: color = f"{c1},{c2},{c3}"
                 except: pass
            if not color:
                if hasattr(artist, 'get_facecolors'):
                    fcs = artist.get_facecolors()
                    if len(fcs) > 0: color = color_utils.convert_color_to_hex(fcs[0])
                elif hasattr(artist, 'get_facecolor'):
                    color = color_utils.convert_color_to_hex(artist.get_facecolor())
                elif hasattr(artist, 'get_color'):
                    color = color_utils.convert_color_to_hex(artist.get_color())

            if color: 
                elements[ftype].append({'hash': fhash, 'vec': fvec, 'color': color})
    return elements


class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class ColorMetrics:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    total_similarity: float = 0.0
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    error_message: str = ""

class ColorEvaluator:
    def __call__(self, gen_fig: Any, gt_fig: Any) -> ColorMetrics:
        metrics = ColorMetrics()
        if gen_fig is None or gt_fig is None:
            metrics.status = ExecutionStatus.FAILED
            metrics.error_message = "Figure object is None"
            return metrics

        try:
            gen_data = extract_elements_with_signature(gen_fig)
            gt_data = extract_elements_with_signature(gt_fig)
        except Exception as e:
            metrics.status = ExecutionStatus.FAILED
            metrics.error_message = f"Extraction failed: {str(e)}"
            return metrics

        return self._calculate_score_geo(gen_data, gt_data)

    def _calculate_score_geo(self, gen_data: Dict[str, List], gt_data: Dict[str, List]) -> ColorMetrics:
        metrics = ColorMetrics()
        total_weighted_sim = 0.0
        total_gt_weight = 0.0
        total_gen_weight = 0.0
        
        matched_gen_indices = defaultdict(set) 
        for elem_type, items in gen_data.items():
            weight_key = TYPE_MAPPING.get(elem_type, '')
            weight = TYPE_WEIGHTS.get(weight_key, DEFAULT_WEIGHT)
            total_gen_weight += len(items) * weight
        for elem_type, gt_items in gt_data.items():
            weight_key = TYPE_MAPPING.get(elem_type, '')
            weight = TYPE_WEIGHTS.get(weight_key, DEFAULT_WEIGHT)
            gen_items = gen_data.get(elem_type, [])
            total_gt_weight += len(gt_items) * weight

            if not gen_items:
                continue

            for gt_item in gt_items:
                best_match_idx = -1
                best_match_score = 0.0
                for idx, gen_item in enumerate(gen_items):
                    if idx in matched_gen_indices[elem_type]: continue
                    if gt_item['hash'] == gen_item['hash']:
                        best_match_idx = idx
                        best_match_score = self._compare_color(gt_item['color'], gen_item['color'])
                        break 
                if best_match_idx == -1:
                    min_relative_dist = float('inf')
                    candidate_idx = -1
                    gt_vec = gt_item['vec']
                    gt_norm = np.linalg.norm(gt_vec) + 1e-6
                    
                    for idx, gen_item in enumerate(gen_items):
                        if idx in matched_gen_indices[elem_type]: continue
                        
                        gen_vec = gen_item['vec']
                        abs_dist = np.linalg.norm(gt_vec - gen_vec)
                        relative_dist = abs_dist / gt_norm
                        
                        is_match = False
                        if abs_dist < 0.2: is_match = True
                        elif relative_dist < 0.05: is_match = True
                            
                        if is_match:
                            score_metric = relative_dist
                            if score_metric < min_relative_dist:
                                min_relative_dist = score_metric
                                candidate_idx = idx

                    if candidate_idx != -1:
                        best_match_idx = candidate_idx
                        best_match_score = self._compare_color(gt_item['color'], gen_items[candidate_idx]['color'])
                if best_match_idx != -1:
                    total_weighted_sim += best_match_score * weight
                    matched_gen_indices[elem_type].add(best_match_idx)

        metrics.total_similarity = total_weighted_sim
        metrics.recall = total_weighted_sim / total_gt_weight if total_gt_weight > 0 else 1.0
        metrics.precision = total_weighted_sim / total_gen_weight if total_gen_weight > 0 else 1.0
        
        if total_gt_weight == 0 and total_gen_weight == 0:
            metrics.precision = metrics.recall = metrics.f1 = 1.0
        else:
            if metrics.precision + metrics.recall > 0:
                metrics.f1 = 2 * metrics.precision * metrics.recall / (metrics.precision + metrics.recall)
            else:
                metrics.f1 = 0.0
        return metrics

    def _compare_color(self, c1: str, c2: str) -> float:
        if "," in c1 and "," in c2:
            l1, l2 = c1.split(','), c2.split(',')
            if len(l1) == 3 and len(l2) == 3:
                return sum(color_utils.calculate_color_similarity(a, b) for a, b in zip(l1, l2)) / 3.0
        return color_utils.calculate_color_similarity(c1, c2)
def _execute_code_runner(code_file_path: str) -> Tuple[bool, Optional[str]]:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.show = lambda *args, **kwargs: None
    plt.savefig = lambda *args, **kwargs: None
    plt.close('all')
    output_buffer = io.StringIO()
    try:
        with redirect_stdout(output_buffer):
            runpy.run_path(str(code_file_path), run_name='__main__')
        return True, None
    except Exception as e:
        return False, f"Code execution failed: {e}"
    finally:
        plt.close('all')

def execute_code_and_get_figure(code_file_path: str, timeout: int = 60) -> Tuple[Optional[Figure], Optional[str]]:
    with ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_execute_code_runner, code_file_path)
        try:
            success, error_msg = future.result(timeout=timeout)
            if not success: return None, error_msg
        except TimeoutError:
            return None, f"Execution timed out after {timeout} seconds"
        except Exception as e:
            return None, f"Executor encountered an unknown error: {e}"
    plt.close('all')
    try:
        runpy.run_path(str(code_file_path), run_name='__main__')
        fig_nums = plt.get_fignums()
        if not fig_nums: return None, "Script executed successfully but produced no figure"
        return plt.figure(fig_nums[-1]), None
    except Exception as e:
        return None, f"Error while retrieving figure object: {e}"
    finally:
        plt.close('all')
def process_single_file(file_name: str, generation_dir: Path, gt_dir: Path) -> Tuple[str, ColorMetrics]:
    logger.info(f"Processing: {file_name}...")
    evaluator = ColorEvaluator()
    gen_fig, gen_err = execute_code_and_get_figure(str(generation_dir / file_name))
    gt_fig, gt_err = execute_code_and_get_figure(str(gt_dir / file_name))
    metrics = evaluator(gen_fig, gt_fig)
    if gen_err or gt_err:
        if metrics.status == ExecutionStatus.SUCCESS: metrics.status = ExecutionStatus.FAILED
        if "timeout" in str(gen_err).lower() or "timeout" in str(gt_err).lower(): metrics.status = ExecutionStatus.TIMEOUT
        metrics.error_message = f"GenError: {gen_err}; GtError: {gt_err}"
        logger.warning(f"Failed to process {file_name}: {metrics.error_message}")
    else:
        logger.info(f"Finished {file_name} (P:{metrics.precision:.2f} R:{metrics.recall:.2f} F1:{metrics.f1:.2f})")
    return file_name, metrics

def batch_evaluate_directory(generation_dir: str, gt_dir: str, output_file: Optional[str] = None, num_workers: Optional[int] = None) -> Dict[str, ColorMetrics]:
    generation_path = Path(generation_dir)
    gt_path = Path(gt_dir)
    common_files = sorted(list(set(f.name for f in generation_path.glob("*.py")) & set(f.name for f in gt_path.glob("*.py"))))
    if not common_files:
        logger.warning("No matching file pairs found in the specified directories."); return {}
    if num_workers is None: num_workers = os.cpu_count()
    logger.info(f"Found {len(common_files)} files to process using {num_workers} workers.")
    all_results = {}
    with ProcessPoolExecutor(max_workers=num_workers, max_tasks_per_child=20) as executor:
        future_to_file = {executor.submit(process_single_file, fname, generation_path, gt_path): fname for fname in common_files}
        for future in as_completed(future_to_file):
            file_name = future_to_file[future]
            try:
                _, metrics = future.result()
                all_results[file_name] = metrics
            except Exception as e:
                logger.error(f"A critical error occurred while processing future for {file_name}: {e}")
                all_results[file_name] = ColorMetrics(status=ExecutionStatus.FAILED, error_message=str(e))
    if output_file: save_results_to_json(all_results, output_file, str(generation_dir), str(gt_dir))
    return all_results

def save_results_to_json(results: Dict[str, ColorMetrics], output_file: str, generation_dir: str, gt_dir: str) -> None:
    json_data = {
        "evaluation_info": {"timestamp": datetime.now().isoformat(), "evaluator": "GeoMatchingColorEvaluator"},
        "individual_results": []
    }
    for file_name, metrics in sorted(results.items()):
        json_data["individual_results"].append({
            "file": file_name,
            "status": metrics.status.value,
            "precision": round(metrics.precision, 4),
            "recall": round(metrics.recall, 4),
            "f1": round(metrics.f1, 4),
            "total_similarity": round(metrics.total_similarity, 4),
            "error_message": metrics.error_message
        })
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Evaluation results saved to: {output_file}")

def main():
    print("=" * 60)
    print("Color Evaluator (Geometric Matching + Perceptual Color Diff + Weighted)")
    generation_dir = PROJECT_PATH / "generation_code"
    gt_dir = PROJECT_PATH / "gt_code"
    if not generation_dir.exists() or not gt_dir.exists():
        logger.error(f"Error: Please ensure 'generation_code' and 'gt_code' directories exist in: {PROJECT_PATH}")
        return
    try:
        results = batch_evaluate_directory(
            generation_dir=str(generation_dir),
            gt_dir=str(gt_dir),
            output_file=str(PROJECT_PATH / "color_evaluation_results_geo.json"),
            num_workers=os.cpu_count()
        )
        if results:
            print("\n" + "=" * 25 + " Evaluation Summary " + "=" * 25)
            status_counts = Counter(m.status.value for m in results.values())
            total = len(results)
            print(f"Total files evaluated: {total}")
            for status, count in status_counts.items():
                print(f"  - {status.capitalize():<10}: {count:4d} files ({count/total:.1%})")
            print("=" * 60)
        else:
            print("\nNo files were evaluated.")
    except Exception as e:
        logger.error(f"Batch evaluation failed: {e}", exc_info=True)

if __name__ == "__main__":
    import multiprocessing
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass
    main()

