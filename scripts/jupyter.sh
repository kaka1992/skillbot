#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# skillbot jupyter launcher
# ============================================================

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python"
SRC="${PROJECT_DIR}/src"
IPYTHON_PROFILE="${PROJECT_DIR}/.jupyter"

usage() {
    cat <<EOF
Usage: jupyter.sh [lab|notebook] [options]

Start Jupyter with %%agent / %%sql magic pre-loaded.

Examples:
  jupyter.sh                          # start notebook on 8888
  jupyter.sh lab                      # start JupyterLab
  jupyter.sh notebook --port 9999     # custom port
  jupyter.sh lab --no-browser         # headless
EOF
    exit 0
}

# -----------------------------------------------------------
# setup: ensure deps + register kernel + init profile
# -----------------------------------------------------------
_setup() {
    echo "=== Setting up Jupyter ==="

    # clean stale labextension artifacts (deprecated approach)
    rm -rf "${IPYTHON_PROFILE}/labextensions" "${IPYTHON_PROFILE}/jupyter_lab_config.py" 2>/dev/null || true

    # ensure Python deps
    if ! "${VENV_PYTHON}" -c "import jupyter" 2>/dev/null; then
        echo "  [RUN] installing jupyter deps"
        "${VENV_PYTHON}" -m pip install -e "${PROJECT_DIR}[jupyter]" -q
    fi

    # ---- skillbot kernel ----
    local kernel_dir="${IPYTHON_PROFILE}/kernels/skillbot"
    mkdir -p "$kernel_dir"
    cat > "${kernel_dir}/kernel.json" <<KERNEL_EOF
{
 "argv": [
  "${VENV_PYTHON}",
  "${kernel_dir}/bootstrap.py",
  "-f", "{connection_file}"
 ],
 "display_name": "skillbot (Python 3.12)",
 "language": "python"
}
KERNEL_EOF
    cat > "${kernel_dir}/bootstrap.py" <<BOOTSTRAP_EOF
import os, sys
sys.path.insert(0, '${SRC}')
from ipykernel.kernelapp import IPKernelApp
_orig = IPKernelApp.init_shell
def _patched(self):
    _orig(self)
    self.shell._notebook_path = os.path.realpath(os.getcwd())
    from jupyter import load_ipython_extension
    load_ipython_extension(self.shell)
IPKernelApp.init_shell = _patched
IPKernelApp.launch_instance()
BOOTSTRAP_EOF
    echo "  [OK] kernel: skillbot (Python 3.12)"

    # ---- working dir ----
    mkdir -p "${IPYTHON_PROFILE}/run"

    # ---- IPython startup: auto-load jupyter extension ----
    # Write to both .jupyter (skillbot kernel) and ~/.ipython (default kernel fallback)
    local ipython_dir="$("${VENV_PYTHON}" -c 'import IPython.paths; print(IPython.paths.get_ipython_dir())')/profile_default"
    for _dir in "${IPYTHON_PROFILE}" "${ipython_dir}"; do
        mkdir -p "${_dir}/startup"
        cat > "${_dir}/startup/00-agent-magic.py" <<'PYEOF'
import sys
_src = 'SRC_PLACEHOLDER'
if _src not in sys.path: sys.path.insert(0, _src)
try:
    _ip = get_ipython()
    from jupyter import load_ipython_extension
    load_ipython_extension(_ip)
except NameError:
    pass
PYEOF
        sed -i '' "s|SRC_PLACEHOLDER|${SRC}|" "${_dir}/startup/00-agent-magic.py"
    done
    echo "  [OK] startup: auto-load %%agent + %%sql via IPython startup"
}

# -----------------------------------------------------------
# start
# -----------------------------------------------------------
_start() {
    local mode="${1:-notebook}"
    shift || true

    _setup

    echo "=== Starting Jupyter ${mode} ==="
    echo "  PYTHONPATH: ${SRC}"
    echo ""

    export PYTHONPATH="${SRC}${PYTHONPATH:+:${PYTHONPATH}}"
    export IPYTHONDIR="${IPYTHON_PROFILE}"
    cd "${IPYTHON_PROFILE}/run"

    case "$mode" in
        lab)      exec "${VENV_PYTHON}" -m jupyterlab "$@" ;;
        notebook) exec "${VENV_PYTHON}" -m notebook "$@" ;;
    esac
}

# -----------------------------------------------------------
# main
# -----------------------------------------------------------
main() {
    if [[ $# -gt 0 && ("$1" == "-h" || "$1" == "--help" || "$1" == "help") ]]; then
        usage
    fi

    local mode="notebook"
    if [[ $# -gt 0 ]]; then
        case "$1" in
            lab|notebook) mode="$1"; shift ;;
        esac
    fi

    _start "$mode" "$@"
}

main "$@"
