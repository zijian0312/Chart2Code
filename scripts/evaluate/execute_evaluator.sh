#!/bin/bash
# ==============================================================================
#                 Chart2Code Execute Execution Script
# ==============================================================================
set -e


export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

MAX_WORKERS=30 

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
PYTHON_SCRIPT_PATH="$PROJECT_ROOT/Evaluation/srcs/execute_evaluator.py"
BASE_OUTPUT_DIR="$PROJECT_ROOT/Evaluation/execute_results"



SOURCE_DIRS=(
    "$PROJECT_ROOT/Inference/level1_direct/results"
    "$PROJECT_ROOT/Inference/level1_customize/results"
    # "$PROJECT_ROOT/Inference/level1_customize/results/InternVL_3_customize_8B"
    "$PROJECT_ROOT/Inference/level1_figure/results"
    "$PROJECT_ROOT/Inference/level2/results"
    # "$PROJECT_ROOT/Inference/level2/results/deepseek_level2"
    # "$PROJECT_ROOT/Inference/level2/results/InternVL_3_level2_8B"
    "$PROJECT_ROOT/Inference/level3/results"
)

# ==================== 2. Core Function Definition ====================
process_target_folder() {
    local target_dir="$1"
    local base_output="$2"
    local dir_basename=$(basename "$target_dir")
    local specific_output_dir="$base_output/$dir_basename"

    local script_files=()
    while IFS= read -r -d '' file; do
        script_files+=("$file")
    done < <(find "$target_dir" -maxdepth 1 -type f -name "*.py" -print0)

    if [ ${#script_files[@]} -eq 0 ]; then
        return 0
    fi

    echo "---------------------------------------------"
    echo "Processing: $dir_basename"
    echo "  -> Source: $target_dir"
    echo "  -> Output: $specific_output_dir"
    echo "  -> Files:  ${#script_files[@]}"
    
    mkdir -p "$specific_output_dir"

    python "$PYTHON_SCRIPT_PATH" \
        --output-dir "$specific_output_dir" \
        --workers "$MAX_WORKERS" \
        "${script_files[@]}"

    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "## WARNING: Task '$dir_basename' finished with errors (Code: $exit_code)."
    fi
}

# ==================== 3. Main Logic (Auto-Detection) ====================

echo "============================================="
echo "   Starting Smart Automated Evaluation"
echo "============================================="
echo "Python Processor: $PYTHON_SCRIPT_PATH"
echo "Output Directory: $BASE_OUTPUT_DIR"
echo

if [ ! -f "$PYTHON_SCRIPT_PATH" ]; then
    echo "Error: Python script not found!"
    exit 1
fi

mkdir -p "$BASE_OUTPUT_DIR"

for INPUT_PATH in "${SOURCE_DIRS[@]}"; do
    echo -e "\n=== Scanning Input Path: $INPUT_PATH ==="

    if [ ! -d "$INPUT_PATH" ]; then
        echo "Warning: Path not found, skipping: $INPUT_PATH"
        continue
    fi

    subdirs_count=$(find "$INPUT_PATH" -mindepth 1 -maxdepth 1 -type d | grep -v '_failed$' | wc -l)

    if [ "$subdirs_count" -gt 0 ]; then
        echo "  [Mode: Container Directory] Found $subdirs_count sub-directories."
        
        find "$INPUT_PATH" -mindepth 1 -maxdepth 1 -type d | grep -v '_failed$' | while IFS= read -r sub_dir; do
            process_target_folder "$sub_dir" "$BASE_OUTPUT_DIR"
        done

    else
        py_files_count=$(find "$INPUT_PATH" -maxdepth 1 -type f -name "*.py" | wc -l)
        
        if [ "$py_files_count" -gt 0 ]; then
             echo "  [Mode: Direct Directory] Found $py_files_count Python files directly."
             process_target_folder "$INPUT_PATH" "$BASE_OUTPUT_DIR"
        else
             echo "  [Skipping] Path contains neither sub-directories nor Python files."
        fi
    fi
done

echo
echo "============================================="
echo "          All Processing Finished."
echo "============================================="


