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

Start Jupyter with %%agent magic pre-loaded.

Examples:
  jupyter.sh                          # start notebook on 8888
  jupyter.sh lab                      # start JupyterLab
  jupyter.sh notebook --port 9999     # custom port
  jupyter.sh lab --no-browser         # headless
EOF
    exit 0
}

# -----------------------------------------------------------
# setup: ensure deps + init profile with auto-load
# -----------------------------------------------------------
_setup() {
    echo "=== Setting up Jupyter ==="

    # ensure deps
    if ! "${VENV_PYTHON}" -c "import jupyter" 2>/dev/null; then
        echo "  [RUN] installing jupyter deps"
        "${VENV_PYTHON}" -m pip install ipython jupyter notebook jupyterlab pandas ipykernel -q
    fi

    # register skillbot kernel with bootstrap that patches in %%agent
    local kernel_dir="${IPYTHON_PROFILE}/kernels/skillbot"
    mkdir -p "$kernel_dir"
    cat > "${kernel_dir}/bootstrap.py" <<BOOTSTRAP_EOF
import os, sys
sys.path.insert(0, '${SRC}')
from ipykernel.kernelapp import IPKernelApp
_orig = IPKernelApp.init_shell
def _patched(self):
    _orig(self)
    # store notebook path for session-key binding
    self.shell._notebook_path = os.path.realpath(os.getcwd())
    from jupyter import load_ipython_extension
    load_ipython_extension(self.shell)
IPKernelApp.init_shell = _patched
IPKernelApp.launch_instance()
BOOTSTRAP_EOF
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
    echo "  [OK] kernel: skillbot (Python 3.12)"

    # create working directory
    mkdir -p "${IPYTHON_PROFILE}/run"

    # create startup script in BOTH locations:
    # .jupyter/startup  — Jupyter server
    # ~/.ipython/profile_default/startup — ipykernel
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

    # IPython config: auto-load jupyter extension (works for both terminal and kernel)
    local ipython_config_dir="${ipython_dir}/profile_default"
    mkdir -p "$ipython_config_dir"
    cat > "${ipython_config_dir}/ipython_kernel_config.py" <<'PYEOF'
c = get_config()
c.InteractiveShellApp.extensions = ['jupyter']
PYEOF
    echo "  [OK] config: auto-load %%agent via InteractiveShellApp.extensions"
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
    echo "  Use: %load_ext jupyter"
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
