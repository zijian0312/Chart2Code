#!/bin/bash
# ==============================================================================
#                 Chart2Code Base Evaluation Script 
# ==============================================================================

set -euo pipefail

MAX_PARALLEL_TASKS=2
NUM_WORKERS_PER_EVAL_TASK=8


SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

find_project_root() {
    local current_dir="$1"
    while [[ "$current_dir" != "/" && -n "$current_dir" ]]; do
        if [[ -d "$current_dir/Evaluation" && -d "$current_dir/Inference" ]]; then
            realpath "$current_dir"
            return 0
        fi
        current_dir=$(dirname "$current_dir")
    done
    return 1
}

PROJECT_ROOT_DIR=$(find_project_root "$SCRIPT_DIR")

SOURCE_DIRS_INPUT=(

    # "/path/to/project/Evaluation/execute_results/qwen_level1_direct"
    # "${PROJECT_ROOT_DIR}/Evaluation/execute_results/claude_direct"
    "${PROJECT_ROOT_DIR}/Evaluation/execute_results"
)

if [ -z "$PROJECT_ROOT_DIR" ]; then
    echo "Error: Could not dynamically locate the project root directory." >&2
    exit 1
fi

DEFAULT_EXECUTE_RESULTS_DIR="${PROJECT_ROOT_DIR}/Evaluation/execute_results"
GT_DATA_DIR="${PROJECT_ROOT_DIR}/data"
EVALUATION_RESULTS_DIR="${PROJECT_ROOT_DIR}/Evaluation/evaluation_results"
PYTHON_EVALUATOR_SCRIPT_FULLPATH="${PROJECT_ROOT_DIR}/Evaluation/srcs/base_evaluator.py"

if [ ${#SOURCE_DIRS_INPUT[@]} -eq 0 ]; then
    SOURCE_DIRS_INPUT=("${DEFAULT_EXECUTE_RESULTS_DIR}")
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAIN_LOG_DIR="${EVALUATION_RESULTS_DIR}/_base_main_log"
MAIN_LOG_FILE="${MAIN_LOG_DIR}/base_main_${TIMESTAMP}.log"
mkdir -p "$MAIN_LOG_DIR"
mkdir -p "$EVALUATION_RESULTS_DIR"

exec &> >(tee -a "$MAIN_LOG_FILE")

echo "=============================================================================="
echo "                   Base Evaluation "
echo "=============================================================================="
echo "Project Root: ${PROJECT_ROOT_DIR}"
echo "Results Dest: ${EVALUATION_RESULTS_DIR}"
echo "------------------------------------------------------------------------------"

declare -a TASKS_GEN_DIRS=()
declare -a TASKS_GT_PATHS=()
declare -a TASKS_OUTPUT_DIRS=()

add_task() {
    local gen_dir_path="$1"
    local dir_name=$(basename "$gen_dir_path")
    local gt_json_file=""

    if [[ "$dir_name" == *customize* ]]; then gt_json_file="level1_customize.json"
    elif [[ "$dir_name" == *direct* ]]; then gt_json_file="level1_direct.json"
    elif [[ "$dir_name" == *figure* ]]; then gt_json_file="level1_figure.json"
    elif [[ "$dir_name" == *level2* ]]; then gt_json_file="level2.json"
    elif [[ "$dir_name" == *level3* ]]; then gt_json_file="level3.json"
    fi

    if [ -n "$gt_json_file" ]; then
        full_gt_path="${GT_DATA_DIR}/${gt_json_file}"
        if [ -f "$full_gt_path" ]; then
            output_dir="${EVALUATION_RESULTS_DIR}/${dir_name}"
            TASKS_GEN_DIRS+=("${gen_dir_path}")
            TASKS_GT_PATHS+=("${full_gt_path}")
            TASKS_OUTPUT_DIRS+=("${output_dir}")
            echo "  [MATCH] Task Added: '${dir_name}' -> '${gt_json_file}'"
        else
            echo "  [WARNING] GT file missing for '${dir_name}': ${full_gt_path}"
        fi
    else
        echo "  [SKIP] No matching GT rule for directory: '${dir_name}'"
    fi
}

echo "Discovering evaluation tasks..."

for INPUT_PATH in "${SOURCE_DIRS_INPUT[@]}"; do
    if [ ! -d "$INPUT_PATH" ]; then
        echo "Warning: Path not found: $INPUT_PATH"
        continue
    fi

    echo " Scanning: $INPUT_PATH"
    subdirs_count=$(find "$INPUT_PATH" -mindepth 1 -maxdepth 1 -type d | wc -l)

    if [ "$subdirs_count" -gt 0 ]; then
        echo "  -> Identified as container directory (contains $subdirs_count sub-folders)."
        

        while read -r sub_dir; do
            add_task "$sub_dir"
        # done < <(find "$INPUT_PATH" -mindepth 1 -maxdepth 1 -type d -name "*direct*") # choose mode
        done < <(find "$INPUT_PATH" -mindepth 1 -maxdepth 1 -type d) # all eval

        
    else
        echo "  -> Identified as specific task directory."
        add_task "$INPUT_PATH"
    fi
done

total_tasks=${#TASKS_GEN_DIRS[@]}
if [ "$total_tasks" -eq 0 ]; then
    echo "------------------------------------------------------------------------------"
    echo "No valid tasks found. Exiting."
    exit 0
fi

echo "------------------------------------------------------------------------------"
echo "Found ${total_tasks} valid tasks. Starting execution..."
start_time=$(date +%s)

run_evaluation_task() {
    local gen_dir="$1"
    local gt_json="$2"
    local output_dir="$3"
    local task_id="$4"
    local task_name=$(basename "$gen_dir")

    echo "$(date) [Task ${task_id}] START: ${task_name}"
    mkdir -p "${output_dir}"

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local output_basename="base_results_${timestamp}"

    python "$PYTHON_EVALUATOR_SCRIPT_FULLPATH" \
        --gen-dir "${gen_dir}" \
        --gt-json "${gt_json}" \
        --output-dir "${output_dir}" \
        --output-basename "${output_basename}" \
        --workers "${NUM_WORKERS_PER_EVAL_TASK}"

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "$(date) [Task ${task_id}] SUCCESS: ${task_name}"
    else
        echo "$(date) [Task ${task_id}] FAILED (Exit Code: ${exit_code}): ${task_name}"
    fi
    return ${exit_code}
}

export -f run_evaluation_task
export PYTHON_EVALUATOR_SCRIPT_FULLPATH
export NUM_WORKERS_PER_EVAL_TASK

if command -v parallel &> /dev/null; then
    echo "Using GNU Parallel (Max Jobs: ${MAX_PARALLEL_TASKS})."
    
    parallel -j "${MAX_PARALLEL_TASKS}" --halt now,fail=1 \
        run_evaluation_task {1} {2} {3} {#} \
        ::: "${TASKS_GEN_DIRS[@]}" \
        :::+ "${TASKS_GT_PATHS[@]}" \
        :::+ "${TASKS_OUTPUT_DIRS[@]}"
        
    ALL_TASKS_SUCCESS=$?
else
    echo "GNU Parallel not found. Running sequentially..."
    ALL_TASKS_SUCCESS=0
    for i in "${!TASKS_GEN_DIRS[@]}"; do
        run_evaluation_task "${TASKS_GEN_DIRS[$i]}" "${TASKS_GT_PATHS[$i]}" "${TASKS_OUTPUT_DIRS[$i]}" "$((i+1))" || ALL_TASKS_SUCCESS=1
    done
fi

# --- 7. Summary Report ---
end_time=$(date +%s)
duration=$((end_time - start_time))
echo -e "\n=============================================================================="
if [ "$ALL_TASKS_SUCCESS" -eq 0 ]; then
    echo "              All tasks completed successfully!"
else
    echo "              Some tasks failed."
fi
echo "              Time: $((duration / 60)) min $((duration % 60)) sec"
echo "=============================================================================="

exit $ALL_TASKS_SUCCESS


