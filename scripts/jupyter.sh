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
Usage: jupyter.sh [lab|notebook] [options] [--remote]

Start Jupyter with %%agent / %%sql magic pre-loaded.

Options:
  --remote        bind to 0.0.0.0 (all interfaces) for remote access

Examples:
  jupyter.sh                          # start notebook on localhost:8888
  jupyter.sh lab --remote             # JupyterLab, bind to all interfaces
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

    # ensure project venv + deps
    if [[ ! -x "${VENV_PYTHON}" ]] || ! "${VENV_PYTHON}" -c "import jupyter" 2>/dev/null; then
        echo "ERROR: jupyter deps not installed. Run: install.sh init" >&2
        exit 1
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

    # ---- frontend extension (comm-based auto cell execution) ----
    local ext_dir="${PROJECT_DIR}/src/jupyter/extension"
    if command -v node &>/dev/null; then
        local node_ver=$(node -v | sed 's/^v//' | cut -d. -f1)
        if [ "$node_ver" -ge 18 ] 2>/dev/null; then
            echo "  building frontend extension (node v${node_ver})..."
            cd "$ext_dir"
            [ ! -d "node_modules" ] && npm install --silent 2>&1 | tail -1
            npx tsc 2>&1 | tail -1
            # patch: license-webpack-plugin bug with Node >=25
            local lp_file="node_modules/@jupyterlab/builder/node_modules/license-webpack-plugin/dist/WebpackModuleFileIterator.js"
            if [ -f "$lp_file" ]; then
                sed -i '' "s/return filename.split('=')\[1\].trim()/var parts = filename.split('=')\n            return parts.length > 1 ? parts[1].trim() : null/" "$lp_file"
            fi
            PATH="${PROJECT_DIR}/.venv/bin:${HOME}/.npm-global/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" \
                "${VENV_PYTHON}" -m jupyter labextension build . 2>&1 | tail -1
            cp -r lib labextension/
            PATH="${PROJECT_DIR}/.venv/bin:${HOME}/.npm-global/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" \
                "${VENV_PYTHON}" -m jupyter labextension install labextension/ 2>&1 | tail -3
            # Clean then copy to shared labextensions/ — prevents stale webpack chunks
            rm -rf "${PROJECT_DIR}/.venv/share/jupyter/labextensions/skillbot-jupyter"
            cp -r labextension/ "${PROJECT_DIR}/.venv/share/jupyter/labextensions/skillbot-jupyter"
            cd "${PROJECT_DIR}"
            echo "  [OK] frontend extension: comm-based cell execution"
        else
            echo "  [SKIP] frontend extension: need Node >=18 (current: v${node_ver})"
        fi
    else
        echo "  [SKIP] frontend extension: node not found (auto cell fallback to kernel-side)"
    fi

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
# rebuild: quick frontend-only rebuild (no server restart needed)
# -----------------------------------------------------------
_rebuild() {
    echo "=== Rebuilding frontend extension ==="
    local ext_dir="${PROJECT_DIR}/src/jupyter/extension"
    local ext_install_dir="${PROJECT_DIR}/.venv/share/jupyter/labextensions/skillbot-jupyter"

    if ! command -v node &>/dev/null || [ "$(node -v | sed 's/^v//' | cut -d. -f1)" -lt 18 ] 2>/dev/null; then
        echo "ERROR: need Node >=18" >&2
        exit 1
    fi

    cd "$ext_dir"
    echo "  [1/3] tsc..."
    npx tsc
    echo "  [2/3] webpack..."
    local lp_file="node_modules/@jupyterlab/builder/node_modules/license-webpack-plugin/dist/WebpackModuleFileIterator.js"
    if [ -f "$lp_file" ]; then
        sed -i '' "s/return filename.split('=')\[1\].trim()/var parts = filename.split('=')\n            return parts.length > 1 ? parts[1].trim() : null/" "$lp_file"
    fi
    PATH="${PROJECT_DIR}/.venv/bin:${HOME}/.npm-global/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" \
        "${VENV_PYTHON}" -m jupyter labextension build .
    cp -r lib labextension/
    echo "  [3/3] sync to labextensions..."
    rm -rf "${ext_install_dir}"
    cp -r labextension/ "${ext_install_dir}"
    echo "  [OK] frontend rebuilt — hard refresh browser (Cmd+Shift+R) to pick up changes"
    cd "${PROJECT_DIR}"
}

# -----------------------------------------------------------
# start
# -----------------------------------------------------------
_start() {
    local mode="${1:-notebook}"
    local remote="${2:-0}"
    shift 2 || shift || true

    _setup

    echo "=== Starting Jupyter ${mode} ==="
    echo "  PYTHONPATH: ${SRC}"
    echo ""

    export PYTHONPATH="${SRC}${PYTHONPATH:+:${PYTHONPATH}}"
    export IPYTHONDIR="${IPYTHON_PROFILE}"
    # ensure venv takes priority over system anaconda
    export PATH="${PROJECT_DIR}/.venv/bin:${PATH}"
    cd "${IPYTHON_PROFILE}/run"

    # --remote: bind to all interfaces
    if [[ "$remote" == "1" ]]; then
        # don't override explicit --ip passed by user
        local has_ip=0
        for _a in "$@"; do
            [[ "$_a" == "--ip" || "$_a" == --ip=* ]] && has_ip=1
        done
        if [[ $has_ip -eq 0 ]]; then
            set -- --ip 0.0.0.0 "$@"
        fi
    fi

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

    if [[ $# -gt 0 && "$1" == "--rebuild" ]]; then
        _rebuild
        exit 0
    fi

    local mode="notebook"
    local remote=0
    if [[ $# -gt 0 ]]; then
        case "$1" in
            lab|notebook) mode="$1"; shift ;;
        esac
    fi

    # extract --remote flag (don't pass it to Jupyter)
    local passthru=()
    for _a in "$@"; do
        if [[ "$_a" == "--remote" ]]; then
            remote=1
        else
            passthru+=("$_a")
        fi
    done

    _start "$mode" "$remote" "${passthru[@]}"
}

main "$@"
