#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# skillbot eval CLI — batch evaluation task runner
# ============================================================

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python"

usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} <command> [options]

Commands:
  run  <config>            Run all tasks from YAML config
  run  <config> -t <name>  Run a specific task only
  list <config>            List task names in config
  -h|--help                Show this help

Options:
  -o, --output-dir <dir>   Output directory (default: from config or "results")
  -t, --task <name>        Run a specific task by name

Examples:
  ${SCRIPT_NAME} run tasks.yaml
  ${SCRIPT_NAME} run tasks.yaml -o results/
  ${SCRIPT_NAME} run tasks.yaml -t math-smoke
  ${SCRIPT_NAME} list tasks.yaml
EOF
    exit 0
}

# -----------------------------------------------------------
# cmd_list — print task names from config
# -----------------------------------------------------------
cmd_list() {
    local config="${1:?usage: ${SCRIPT_NAME} list <config>}"
    PYTHONPATH="${PROJECT_DIR}/src" "${VENV_PYTHON}" -c "
import sys
from eval.task import load_tasks
tasks, out_dir = load_tasks('${config}')
print(f'output_dir: {out_dir}')
print(f'tasks ({len(tasks)}):')
for t in tasks:
    print(f'  - {t.name}  ({t.agent}, {t.dataset})')
"
}

# -----------------------------------------------------------
# cmd_run — execute eval tasks
# -----------------------------------------------------------
cmd_run() {
    local config=""
    local output_dir=""
    local task_filter=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -o|--output-dir)
                output_dir="${2:?missing output dir}"
                shift 2
                ;;
            -t|--task)
                task_filter="${2:?missing task name}"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            -*)
                echo "ERROR: unknown option: $1" >&2
                usage
                ;;
            *)
                if [[ -z "$config" ]]; then
                    config="$1"
                fi
                shift
                ;;
        esac
    done

    if [[ -z "$config" ]]; then
        echo "ERROR: config file required" >&2
        usage
    fi

    if [[ ! -f "$config" ]]; then
        echo "ERROR: config not found: $config" >&2
        exit 1
    fi

    local output_arg=""
    if [[ -n "$output_dir" ]]; then
        output_arg=", output_dir='${output_dir}'"
    fi

    local task_filter_arg=""
    if [[ -n "$task_filter" ]]; then
        task_filter_arg=", task_filter='${task_filter}'"
    fi

    PYTHONPATH="${PROJECT_DIR}/src" "${VENV_PYTHON}" -c "
from eval.task import load_tasks, run_tasks
import asyncio

tasks, cfg_out = load_tasks('${config}')
out = '${output_dir}' or cfg_out

if '${task_filter}':
    tasks = [t for t in tasks if t.name == '${task_filter}']
    if not tasks:
        raise SystemExit(f'Task not found: ${task_filter}')

asyncio.run(run_tasks(tasks, out))
"
}

# -----------------------------------------------------------
# main
# -----------------------------------------------------------
main() {
    if [[ $# -eq 0 ]]; then
        usage
    fi

    case "${1:-}" in
        run)
            shift
            cmd_run "$@"
            ;;
        list)
            shift
            cmd_list "$@"
            ;;
        -h|--help|help)
            usage
            ;;
        *)
            echo "ERROR: unknown command: ${1:-}" >&2
            usage
            ;;
    esac
}

main "$@"
