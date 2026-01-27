#!/bin/bash
# ==============================================================================
#                               LMM Evaluation
# ==============================================================================
set -euo pipefail

# --- 1. API Key Configuration ---
API_KEY_POOL=(
    "sk-ufdY8FFZfcjbYQDaaEFiRASDklsadcjn21H5MXP8Rdrb4NYA"
    "sk-icxuQRwrff8RP84c8e1nZnPpdasdadsd3w221KdJgLRfN9xu"
)

API_MODEL_NAME="gpt-5-mini"

MAX_PARALLEL_TASKS=${#API_KEY_POOL[@]} 
NUM_WORKERS_PER_EVAL_TASK=1

# --- 2. Path Setup ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

find_project_root() {
    local current_dir="$1"
    while [[ "$current_dir" != "/" && -n "$current_dir" ]]; do
        if [[ -d "$current_dir/Evaluation" && -d "$current_dir/data" ]]; then
            realpath "$current_dir"
            return 0
        fi
        current_dir=$(dirname "$current_dir")
    done
    return 1
}

PROJECT_ROOT_DIR=$(find_project_root "$SCRIPT_DIR")
if [ -z "$PROJECT_ROOT_DIR" ]; then echo "Error: Root not found." >&2; exit 1; fi

DEFAULT_EXECUTE_RESULTS_DIR="${PROJECT_ROOT_DIR}/Evaluation/execute_results"
GT_JSONS_DIR="${PROJECT_ROOT_DIR}/data"
EVALUATION_RESULTS_DIR="${PROJECT_ROOT_DIR}/Evaluation/evaluation_results"
PYTHON_EVALUATOR_SCRIPT_FULLPATH="${PROJECT_ROOT_DIR}/Evaluation/srcs/LMM_evaluator.py"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$EVALUATION_RESULTS_DIR/_logs"
MAIN_LOG_FILE="${EVALUATION_RESULTS_DIR}/_logs/batch_run_${TIMESTAMP}.log"
JOB_LIST_FILE="${EVALUATION_RESULTS_DIR}/_logs/job_list_${TIMESTAMP}.tsv"
JOB_LOG_FILE="${EVALUATION_RESULTS_DIR}/_logs/gnu_parallel_joblog_${TIMESTAMP}.txt"

exec > >(tee -a "$MAIN_LOG_FILE") 2>&1

export API_KEY_POOL_STR="${API_KEY_POOL[*]}"
export PYTHON_EVALUATOR_SCRIPT_FULLPATH
export NUM_WORKERS_PER_EVAL_TASK
export API_MODEL_NAME

generate_task_list() {
    local input_base="$1"
    local output_file="$2"
    
    echo "Scanning directory: $input_base" >&2
    

    find "$input_base" -mindepth 1 -maxdepth 1 -type d | sort | while read -r gen_dir_path; do
        local dir_name=$(basename "$gen_dir_path")
        local gt_json_file=""

        # Filter Logic
        # if [[ "$dir_name" != *"customize"* ]]; then continue; fi

        # GT Mapping Logic
        if [[ "$dir_name" == *customize* ]]; then gt_json_file="level1_customize.json"
        elif [[ "$dir_name" == *direct* ]]; then gt_json_file="level1_direct.json"
        elif [[ "$dir_name" == *figure* ]]; then gt_json_file="level1_figure.json"
        elif [[ "$dir_name" == *level2* ]]; then gt_json_file="level2.json"
        elif [[ "$dir_name" == *level3* ]]; then gt_json_file="level3.json"
        fi

        if [ -n "$gt_json_file" ]; then
            local full_gt_path="${GT_JSONS_DIR}/${gt_json_file}"
            if [ -f "$full_gt_path" ]; then
                local output_dir="${EVALUATION_RESULTS_DIR}/${dir_name}"
                printf "%s\t%s\t%s\n" "$gen_dir_path" "$full_gt_path" "$output_dir" >> "$output_file"
            fi
        fi
    done
}

echo "Discovering tasks and building job queue..."
: > "$JOB_LIST_FILE" 

for INPUT_PATH in "${DEFAULT_EXECUTE_RESULTS_DIR}"; do
    if [ -d "$INPUT_PATH" ]; then
        generate_task_list "$INPUT_PATH" "$JOB_LIST_FILE"
    fi
done

TOTAL_TASKS=$(wc -l < "$JOB_LIST_FILE")
if [ "$TOTAL_TASKS" -eq 0 ]; then
    echo "No valid tasks found. Exiting."
    exit 0
fi

echo "Found $TOTAL_TASKS tasks. Saved to: $JOB_LIST_FILE"

# --- 4. Execution Wrapper ---
run_evaluation_wrapper() {
    local gen_dir="$1"
    local gt_json="$2"
    local output_dir="$3"
    local job_slot="$4" 
    local job_id="$5"   

    local task_name=$(basename "$gen_dir")
    
    # --- A. Resilience: Resume Check ---

    local existing_summary=$(find "$output_dir" -name "LMM_results_*.json" | head -n 1)
    if [[ -n "$existing_summary" && -s "$existing_summary" ]]; then
        echo "  [SKIP] Task already completed: $task_name"
        return 0
    fi

    # --- B. Key Rotation ---
    local keys_array=($API_KEY_POOL_STR)
    local num_keys=${#keys_array[@]}
    local key_index=$(( (job_slot - 1) % num_keys ))
    local selected_api_key="${keys_array[$key_index]}"
    
    # --- C. Execution ---
    mkdir -p "${output_dir}"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local base_name="LMM_results_${timestamp}"
    local log_file="${output_dir}/${base_name}.log"
    local summary_json_file="${output_dir}/${base_name}.json"
    local details_dir="${output_dir}/${base_name}"

    python3 "$PYTHON_EVALUATOR_SCRIPT_FULLPATH" \
        --gen-dir "${gen_dir}" \
        --gt-json "${gt_json}" \
        --summary-json-path "${summary_json_file}" \
        --details-dir "${details_dir}" \
        --model-name "${API_MODEL_NAME}" \
        --workers "${NUM_WORKERS_PER_EVAL_TASK}" \
        --api-key "${selected_api_key}" > "${log_file}" 2>&1

    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo "  [OK] Task $job_id Finished: $task_name"
    else
        echo "  [ERR] Task $job_id Failed: $task_name (Check $log_file)"
        return $exit_code
    fi
}
export -f run_evaluation_wrapper

# --- 5. Batch Execution using GNU Parallel ---
echo "Starting Parallel Execution (Max Jobs: ${MAX_PARALLEL_TASKS})..."


parallel \
    --jobs "${MAX_PARALLEL_TASKS}" \
    --colsep '\t' \
    --joblog "$JOB_LOG_FILE" \
    --resume-failed \
    --halt never \
    --bar \
    run_evaluation_wrapper {1} {2} {3} {%} {#} \
    :::: "$JOB_LIST_FILE"

# --- 6. Summary ---
FAIL_COUNT=$(awk 'NR>1 && $7!=0 {count++} END {print count+0}' "$JOB_LOG_FILE")
SUCCESS_COUNT=$(awk 'NR>1 && $7==0 {count++} END {print count+0}' "$JOB_LOG_FILE")

echo "=============================================================================="
echo "Batch Processing Completed."
echo "Total Tasks: ${TOTAL_TASKS}"
echo "Success    : ${SUCCESS_COUNT}"
echo "Failed     : ${FAIL_COUNT}"
echo "Detailed Job Log: ${JOB_LOG_FILE}"

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "⚠️  There were failures. You can re-run this script to retry failed tasks."
    exit 1
fi
exit 0



