import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from concurrent.futures import ProcessPoolExecutor, TimeoutError, as_completed
from datetime import datetime
from collections import Counter
import io
from contextlib import redirect_stdout
import runpy
import multiprocessing
from enum import Enum
import time

from dotenv import load_dotenv

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- Global Weights Configuration ---
SCORE_WEIGHTS = {
    'type_f1': 1.0,             
    'parameter_data_f1': 2.0,   
    'parameter_visual_f1': 1.0, 
    'text_f1': 1.0,             
    'color_f1': 2.0,            
    'layout_f1': 1.0,           
    'grid_f1': 1.0,             
    'legend_f1': 1.0            
}

# --- Sub-Evaluator Imports ---
try:
    from color_evaluator import ColorEvaluator, ColorMetrics, ExecutionStatus
    from grid_evaluator import GridEvaluator, GridMetrics
    from layout_evaluator import LayoutEvaluator, LayoutMetrics
    from legend_evaluator import LegendEvaluator, LegendMetrics
    from parameter_evaluator import ParameterEvaluator, ParameterMetrics
    from text_evaluator import TextEvaluator, TextMetrics
    from type_evaluator import ChartTypeEvaluator, ChartTypeMetrics
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import a sub-evaluator: {e}")
    print("Please ensure all evaluator .py files are present.")
    sys.exit(1)

# --- Global Configuration ---
logger = logging.getLogger("BaseEvaluator")
load_dotenv()
PROJECT_PATH = Path(__file__).resolve().parents[4]
def neutralize_matplotlib_gui(plt_module):

    dummy_func = lambda *args, **kwargs: None
    plt_module.show = dummy_func
    plt_module.savefig = dummy_func

    plt_module.tight_layout = dummy_func
    plt_module.pause = dummy_func
    plt_module.draw = dummy_func
    plt_module.close = dummy_func
    plt_module.ioff()


# --- Code Execution Utilities ---
def _execute_code_runner(code_file_path: str) -> Tuple[bool, Optional[str]]:
    """A sandboxed function to run a Python script."""
    import runpy, matplotlib, io, os
    from contextlib import redirect_stdout
    import random
    import numpy as np

    random.seed(42)
    np.random.seed(42)
    matplotlib.use('Agg')

    import matplotlib.pyplot as plt
    plt.close('all') # Close existing real figures
    matplotlib.rc_file_defaults()
    neutralize_matplotlib_gui(plt)

    output_buffer = io.StringIO()
    script_path = Path(code_file_path)
    original_directory = os.getcwd()

    try:
        os.chdir(script_path.parent)
        with redirect_stdout(output_buffer):
            runpy.run_path(script_path.name, run_name='__main__')
        return True, None
    except Exception as e:
        return False, f"Error during code execution: {e}"
    finally:
        os.chdir(original_directory)
        plt.close('all')

def execute_code_and_get_figure(code_file_path: str, timeout: int = 60) -> Tuple[Optional[plt.Figure], Optional[str]]:
    with ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_execute_code_runner, code_file_path)
        try:
            success, error_msg = future.result(timeout=timeout)
            if not success:
                return None, error_msg
        except TimeoutError:
            return None, f"Code execution timed out (> {timeout} seconds)"
        except Exception as e:
            return None, f"Executor encountered an unknown error: {e}"

    plt.close('all')
    matplotlib.rc_file_defaults()
    
    import random
    import numpy as np
    random.seed(42)
    np.random.seed(42)
    original_show = plt.show
    original_savefig = plt.savefig
    original_tight_layout = plt.tight_layout
    original_close = plt.close
    neutralize_matplotlib_gui(plt)
    
    output_buffer = io.StringIO()
    script_path = Path(code_file_path)
    original_directory = os.getcwd()
    
    try:
        os.chdir(script_path.parent)
        with redirect_stdout(output_buffer):
            runpy.run_path(script_path.name, run_name='__main__')
        
        fig_nums = plt.get_fignums()
        if not fig_nums:
            return None, "Code executed successfully but did not generate any Figure"
        fig = plt.figure(fig_nums[-1])
        return fig, None

    except Exception as e:
        return None, f"Error while capturing Figure object: {e}"
    finally:
        plt.show = original_show
        plt.savefig = original_savefig
        plt.tight_layout = original_tight_layout
        plt.close = original_close
        
        os.chdir(original_directory)
def convert_metrics_to_dict(metrics: Any) -> Dict[str, Any]:
    if not isinstance(metrics, object) or not hasattr(metrics, '__dict__'):
        return metrics
    result_dict = {}
    for key, value in metrics.__dict__.items():
        if isinstance(value, Enum):
            result_dict[key] = value.value
        elif hasattr(value, '__dict__'):
            result_dict[key] = convert_metrics_to_dict(value)
        else:
            result_dict[key] = value
    return result_dict

def init_worker():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def evaluate_and_save_single_file(
    file_name: str, 
    generation_dir: str, 
    gt_file_path: str,
    results_dir: str
) -> Tuple[str, Dict[str, Any]]:
    
    print(f"[Worker] Processing: {file_name}...")
    
    generation_file_path = str(Path(generation_dir) / file_name)

    gen_fig, gen_err = execute_code_and_get_figure(generation_file_path)
    gt_fig, gt_err = execute_code_and_get_figure(gt_file_path)
    
    EXECUTION_SUCCESS = not (gen_err or gt_err)
    execution_error_msg = f"GenErr: {gen_err}; GtErr: {gt_err}" if not EXECUTION_SUCCESS else ""
    
    full_report = {}
    failed_dimensions = [] 
    
    def run_evaluation(dim_name, evaluator_class, *args):
        try:
            if EXECUTION_SUCCESS and gen_fig and gt_fig:
                evaluator_instance = evaluator_class()
                metrics = evaluator_instance(*args)
                result_dict = convert_metrics_to_dict(metrics)
                if result_dict.get('status') != 'success':
                    failed_dimensions.append(f"{dim_name}: {result_dict.get('error_message', 'Unknown')}")
                
                return result_dict
            else:
                metrics_class = globals()[evaluator_class.__name__.replace("Evaluator", "Metrics")]
                return convert_metrics_to_dict(metrics_class(status=ExecutionStatus.FAILED, error_message=execution_error_msg))
        except Exception as e:
             err = f"Eval Logic Crash: {e}"
             failed_dimensions.append(f"{dim_name} (CRASH): {err}")
             metrics_class = globals()[evaluator_class.__name__.replace("Evaluator", "Metrics")]
             return convert_metrics_to_dict(metrics_class(status=ExecutionStatus.FAILED, error_message=err))

    full_report['color'] = run_evaluation('color', ColorEvaluator, gen_fig, gt_fig)
    full_report['layout'] = run_evaluation('layout', LayoutEvaluator, gen_fig, gt_fig, generation_file_path, gt_file_path)
    full_report['grid'] = run_evaluation('grid', GridEvaluator, gen_fig, gt_fig)
    full_report['legend'] = run_evaluation('legend', LegendEvaluator, gen_fig, gt_fig)
    full_report['parameter'] = run_evaluation('parameter', ParameterEvaluator, gen_fig, gt_fig)
    full_report['text'] = run_evaluation('text', TextEvaluator, gen_fig, gt_fig)
    full_report['type'] = run_evaluation('type', ChartTypeEvaluator, gen_fig, gt_fig)
    
    plt.close('all') 
    
    summary_data = {'file_name': file_name, 'is_success': EXECUTION_SUCCESS}
    log_details = ""
    if not EXECUTION_SUCCESS:
        summary_data['error_message'] = execution_error_msg
        log_details = f"Code Exec Failed -> {execution_error_msg}"
    elif failed_dimensions:
        summary_data['error_message'] = "; ".join(failed_dimensions)
        log_details = f"Partial Eval Failure -> {'; '.join(failed_dimensions)}"
    
    for dim, result in full_report.items():
        if result.get('status') == 'success':
            if dim == 'parameter': 
                summary_data[f'{dim}_data_f1'] = result.get('data_metrics', {}).get('f1', 0)
                summary_data[f'{dim}_visual_f1'] = result.get('visual_metrics', {}).get('f1', 0)
            else:
                summary_data[f'{dim}_f1'] = result.get('f1', 0)
    total_score = 0.0
    total_weight = 0.0
    
    if EXECUTION_SUCCESS:
        for key, weight in SCORE_WEIGHTS.items():
            score = summary_data.get(key, 0.0)
            total_score += score * weight
            total_weight += weight
        
        weighted_score = total_score / total_weight if total_weight > 0 else 0.0
    else:
        weighted_score = 0.0

    summary_data['weighted_score'] = weighted_score
    full_report['overall_weighted_score'] = weighted_score
    full_report['weights_used'] = SCORE_WEIGHTS
    output_path = Path(results_dir) / f"{Path(file_name).stem}_report.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(full_report, f, indent=2, ensure_ascii=False)
    if EXECUTION_SUCCESS:
        if not failed_dimensions:
            logger.info(f"Finished: {file_name} (Success)")
        else:
            logger.warning(f"Finished: {file_name} (Partial Success) | Issues: {log_details}")
    else:
        logger.error(f"Finished: {file_name} (Failed) | Reason: {log_details}")
        
    return file_name, summary_data

class CodeEvaluator:
    
    def evaluate_and_report(self, generation_dir: str, gt_json_path: str, output_dir: str, output_basename: str, log_file_path: str, num_workers: Optional[int] = None):
        gen_path = Path(generation_dir)
        gt_json = Path(gt_json_path)
        output_path = Path(output_dir)

        if not gt_json.is_file():
            logger.error(f"Ground truth JSON file not found: {gt_json}")
            return
            
        with open(gt_json, 'r', encoding='utf-8') as f:
            gt_data = json.load(f)

        gt_json_dir = gt_json.parent
        gt_files_map = {
            Path(item['GT code']).name: gt_json_dir / item['GT code']
            for item in gt_data if 'GT code' in item
        }
        
        gen_files = {f.name for f in gen_path.glob("*.py")}
        gt_basenames = set(gt_files_map.keys())
        common_files = sorted(list(gen_files & gt_basenames))
        
        if not common_files:
            logger.warning("No matching Python (.py) file pairs found.")
            return
        if num_workers is None:
            num_workers = max(1, int(os.cpu_count() * 0.75))
        
        individual_results_dir = output_path / output_basename
        summary_report_path = output_path / f"{output_basename}.json"
        individual_results_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Found {len(common_files)} file pairs.")
        logger.info(f"Using {num_workers} workers.")

        all_summaries = []
        with ProcessPoolExecutor(
            max_workers=num_workers,
            initializer=init_worker
        ) as executor:
            future_to_file = {
                executor.submit(
                    evaluate_and_save_single_file, 
                    fname, 
                    generation_dir, 
                    str(gt_files_map[fname]), 
                    str(individual_results_dir)
                ): fname 
                for fname in common_files
            }
            
            for i, future in enumerate(as_completed(future_to_file)):
                file_name = future_to_file[future]
                try:
                    _, summary_data = future.result()
                    all_summaries.append(summary_data)
                    
                    
                    progress_tag = f"[{i+1}/{len(common_files)}]"
                    
                    if summary_data.get('is_success'):
                        score = summary_data.get('weighted_score', 0.0)
                        logger.info(f"{progress_tag} SUCCESS {file_name}: Score={score:.2f}")
                    else:
                        err_msg = summary_data.get('error_message', 'Unknown Error')
                        logger.warning(f"{progress_tag} FAILED  {file_name}: {err_msg}")
                        
                except Exception as e:
                    logger.error(f"CRITICAL SYSTEM ERROR processing {file_name}: {e}", exc_info=True)
                    all_summaries.append({'file_name': file_name, 'is_success': False, 'error_message': str(e)})

        self._generate_summary_report(all_summaries, str(summary_report_path), generation_dir, gt_json_path)

    def _generate_summary_report(self, all_summaries: List[Dict], output_path: str, gen_dir: str, gt_source: str):
        if not all_summaries:
            return

        successful = [s for s in all_summaries if s.get('is_success')]
        
        avg_scores = Counter()
        counts = Counter()
        keys_to_avg = set(SCORE_WEIGHTS.keys()) | {'weighted_score'}

        for s in successful:
            for k, v in s.items():
                if k in keys_to_avg and isinstance(v, (int, float)):
                    avg_scores[k] += v
                    counts[k] += 1
        
        for k in avg_scores:
            if counts[k] > 0: avg_scores[k] /= counts[k]
        
        total_files = len(all_summaries)
        success_count = len(successful)
        success_rate = success_count / total_files if total_files > 0 else 0.0

        report = {
            "evaluation_info": { 
                "timestamp": datetime.now().isoformat(), 
                "generation_directory": str(gen_dir), 
                "gt_source_file": str(gt_source), 
                "total_files_evaluated": total_files,
                "weights_config": SCORE_WEIGHTS 
            },
            "success_rate": { 
                "count": success_count, 
                "total": total_files, 
                "rate_percent": round(success_rate * 100, 2) 
            },
            "average_scores_100_scale": {k: round(v * 100, 2) for k, v in sorted(avg_scores.items())}
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        summary_msg = [
            f"\n{'='*60}",
            f"  EVALUATION COMPLETE: {Path(gen_dir).name}",
            f"  Report: {output_path}",
            f"  Success Rate: {success_count}/{total_files} ({success_rate:.2%})",
            f"{'-'*60}",
            "  Average Scores (0-100):"
        ]
        for k, v in sorted(avg_scores.items()):
            if k != 'weighted_score':
                summary_msg.append(f"    - {k:<25}: {v*100:.2f}")
        
        final_score = avg_scores.get('weighted_score', 0.0) * 100
        summary_msg.append(f"{'-'*60}")
        summary_msg.append(f"  FINAL WEIGHTED SCORE: {final_score:.2f}")
        summary_msg.append(f"{'='*60}\n")
        
        logger.warning("\n".join(summary_msg))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gen-dir', required=True)
    parser.add_argument('--gt-json', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--output-basename', required=True)
    parser.add_argument('--workers', type=int, default=None)
    args = parser.parse_args()

    output_dir_path = Path(args.output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    log_file_path = output_dir_path / f"{args.output_basename}.log"

    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.WARNING) 
    
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    print(f"[{datetime.now()}] Task Started. Logs: {log_file_path}")
    
    evaluator = CodeEvaluator()
    evaluator.evaluate_and_report(
        args.gen_dir, args.gt_json, args.output_dir, args.output_basename, str(log_file_path), args.workers
    )

    print(f"[{datetime.now()}] Task Finished.")

if __name__ == "__main__":
    if sys.platform != 'linux':
        multiprocessing.set_start_method('spawn', force=True)
    main()




