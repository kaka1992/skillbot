#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# skillbot agent framework install script
# ============================================================

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_NAME="$(basename "$0")"
AGENT_NAMES="deer-flow nanobot hermes-agent claude-code"

# Load project-level env config
_load_env() {
    local env_file="${PROJECT_DIR}/conf/.env"
    if [[ -f "$env_file" ]]; then
        set -a
        # shellcheck disable=SC1090
        source "$env_file"
        set +a
    fi
}

# ============================================================
# Agent metadata (compatible with bash 3.2+)
# ============================================================

_git_url() {
    case "$1" in
        deer-flow)    echo "https://github.com/bytedance/deer-flow" ;;
        nanobot)      echo "https://github.com/HKUDS/nanobot" ;;
        hermes-agent) echo "https://github.com/nousresearch/hermes-agent" ;;
        claude-code)  echo "" ;;  # npm-based, no git clone
    esac
}

# Config type: "agent" -> config in agent_path, "home" -> config in ~/.xxx/
_conf_type() {
    case "$1" in
        deer-flow)    echo "agent" ;;
        nanobot)      echo "home" ;;
        hermes-agent) echo "home" ;;
    esac
}

_conf_home_dir() {
    case "$1" in
        nanobot)      echo ".nanobot" ;;
        hermes-agent) echo ".hermes" ;;
        claude-code)  echo ".claude" ;;
    esac
}

_conf_files() {
    case "$1" in
        deer-flow)    echo "config.yaml .env" ;;
        nanobot)      echo "config.json" ;;
        hermes-agent) echo "config.yaml .env" ;;
        claude-code)  echo "settings.json .env" ;;
    esac
}

_is_known_agent() {
    for a in $AGENT_NAMES; do
        [[ "$a" == "$1" ]] && return 0
    done
    return 1
}

# ============================================================
# Helpers
# ============================================================

usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} <command> [agent]

Commands:
  init                Initialize project — uv venv + install pyproject.toml deps
  install   [agent]   Install agent(s) — clone repo + create uv venv
  update    [agent]   Update agent(s) — git pull + reinstall dependencies
  uninstall [agent]   Uninstall agent(s) — remove agent dir and config
  check     [agent]   Check whether agent is installed correctly

Agents: ${AGENT_NAMES}
If no agent is specified, the command applies to all agents.
EOF
    exit 0
}

get_agent_path() {
    local name="$1"
    if [[ -n "${SKILL_BOT_AGENT_INSTALL_DIR:-}" ]]; then
        echo "${SKILL_BOT_AGENT_INSTALL_DIR}/${name}"
    else
        echo "${PROJECT_DIR}/agents/${name}"
    fi
}

get_agent_conf_dest() {
    local name="$1"
    local ctype
    ctype="$(_conf_type "$name")"
    case "$ctype" in
        agent) get_agent_path "$name" ;;
        home)  echo "${HOME}/$(_conf_home_dir "$name")" ;;
    esac
}

get_agent_conf_src() {
    echo "${PROJECT_DIR}/conf/agent_conf/${1}"
}

check_prereqs() {
    if ! command -v git &>/dev/null; then
        echo "ERROR: git is not installed" >&2
        exit 1
    fi
    if ! command -v uv &>/dev/null; then
        echo "ERROR: uv is not installed (https://docs.astral.sh/uv/)" >&2
        exit 1
    fi
}

require_agent() {
    local name="$1"
    if ! _is_known_agent "$name"; then
        echo "ERROR: unknown agent '${name}'. Known: ${AGENT_NAMES}" >&2
        exit 1
    fi
}

resolve_agents() {
    local target="${1:-}"
    if [[ -z "$target" ]]; then
        echo "$AGENT_NAMES"
    else
        require_agent "$target"
        echo "$target"
    fi
}

# ============================================================
# Commands
# ============================================================

cmd_install() {
    for agent in $(resolve_agents "${1:-}"); do
        echo "=== Installing ${agent} ==="

        if [[ "$agent" == "claude-code" ]]; then
            _install_claude
            continue
        fi

        check_prereqs
        local agent_path
        agent_path="$(get_agent_path "$agent")"
        local git_url
        git_url="$(_git_url "$agent")"

        if [[ -d "$agent_path" ]]; then
            echo "  [SKIP] ${agent_path} already exists"
            continue
        fi

        mkdir -p "$(dirname "$agent_path")"
        git clone "$git_url" "$agent_path"
        echo "  [OK] cloned to ${agent_path}"

        (cd "$agent_path" && uv venv .venv)
        echo "  [OK] venv created at ${agent_path}/.venv"

        if [[ -f "${agent_path}/pyproject.toml" ]]; then
            (cd "$agent_path" && VIRTUAL_ENV="$agent_path/.venv" uv pip install -e .)
            echo "  [OK] dependencies installed via pyproject.toml"
        elif [[ -f "${agent_path}/requirements.txt" ]]; then
            (cd "$agent_path" && VIRTUAL_ENV="$agent_path/.venv" uv pip install -r requirements.txt)
            echo "  [OK] dependencies installed via requirements.txt"
        fi

        # WebUI install
        _install_webui "$agent" "$agent_path"

        echo "=== ${agent} installed ==="
    done
}

_install_claude() {
    local agent_path
    agent_path="$(get_agent_path "claude-code")"
    local dest="${agent_path}/server"
    local src="${PROJECT_DIR}/src/server"

    if [[ -f "${dest}/app.py" && -d "${dest}/webui/node_modules" ]]; then
        echo "  [SKIP] claude-code server already installed"
        return 0
    fi

    _copy_claude_files "$src" "$dest"

    if [[ -f "${dest}/webui/package.json" ]]; then
        if command -v npm &>/dev/null; then
            echo "  [RUN] npm install (webui)"
            (cd "${dest}/webui" && npm install)
            echo "  [OK] webui dependencies installed"
        else
            echo "  [WARN] npm not found — webui dependencies skipped"
        fi
    fi

    echo "  [OK] claude-code server installed"
}

_copy_claude_files() {
    local src="$1" dest="$2"
    mkdir -p "${dest}/webui/src"
    cp "${src}/app.py" "${dest}/"
    cp "${src}/session.py" "${dest}/"
    touch "${dest}/__init__.py"
    cp "${src}/webui/index.html" "${dest}/webui/"
    cp "${src}/webui/package.json" "${dest}/webui/"
    cp "${src}/webui/tsconfig.json" "${dest}/webui/"
    cp "${src}/webui/server.js" "${dest}/webui/"
    [[ -d "${src}/webui/src" ]] && cp -r "${src}/webui/src/"* "${dest}/webui/src/"
    echo "  [CP] server files copied"
}

_install_webui() {
    local agent="$1"
    local agent_path="$2"
    local webui_dir=""

    case "$agent" in
        nanobot)      webui_dir="webui" ;;
        hermes-agent) webui_dir="web" ;;
        *)            return 0 ;;
    esac

    # hermes-agent: install dashboard Python deps via "web" extra
    if [[ "$agent" == "hermes-agent" && -f "${agent_path}/pyproject.toml" ]]; then
        (cd "$agent_path" && VIRTUAL_ENV="${agent_path}/.venv" uv pip install -e ".[web]")
        echo "  [OK] dashboard deps installed (fastapi + uvicorn)"
    fi

    if [[ -f "${agent_path}/${webui_dir}/package.json" ]]; then
        if command -v npm &>/dev/null; then
            (cd "${agent_path}/${webui_dir}" && npm install)
            echo "  [OK] webui dependencies installed"
        else
            echo "  [WARN] npm not found — webui dependencies skipped"
        fi
    fi
}

cmd_update() {
    for agent in $(resolve_agents "${1:-}"); do
        echo "=== Updating ${agent} ==="

        if [[ "$agent" == "claude-code" ]]; then
            local agent_path
            agent_path="$(get_agent_path "claude-code")"
            if [[ ! -d "${agent_path}/server" ]]; then
                echo "  [SKIP] claude-code server not found — run install first"
                continue
            fi
            _copy_claude_files "${PROJECT_DIR}/src/server" "${agent_path}/server"
            if [[ -f "${agent_path}/server/webui/package.json" ]]; then
                if command -v npm &>/dev/null; then
                    echo "  [RUN] npm install (webui)"
                    (cd "${agent_path}/server/webui" && npm install)
                    echo "  [OK] webui dependencies updated"
                fi
            fi
            echo "  [OK] claude-code updated"
            echo "=== ${agent} updated ==="
            continue
        fi

        check_prereqs
        local agent_path
        agent_path="$(get_agent_path "$agent")"

        if [[ ! -d "$agent_path" ]]; then
            echo "  [SKIP] ${agent_path} not found — run install first"
            continue
        fi

        (cd "$agent_path" && git pull)
        echo "  [OK] pulled latest changes"

        if [[ -f "${agent_path}/pyproject.toml" ]]; then
            (cd "$agent_path" && VIRTUAL_ENV="$agent_path/.venv" uv pip install -e .)
            echo "  [OK] dependencies updated via pyproject.toml"
        elif [[ -f "${agent_path}/requirements.txt" ]]; then
            (cd "$agent_path" && VIRTUAL_ENV="$agent_path/.venv" uv pip install -r requirements.txt)
            echo "  [OK] dependencies updated via requirements.txt"
        fi

        # WebUI update
        _install_webui "$agent" "$agent_path"

        echo "=== ${agent} updated ==="
    done
}

cmd_uninstall() {
    for agent in $(resolve_agents "${1:-}"); do
        if [[ "$agent" == "claude-code" ]]; then
            echo "=== Uninstalling ${agent} ==="
            local agent_path
            agent_path="$(get_agent_path "claude-code")"
            if [[ -d "${agent_path}/server" ]]; then
                rm -rf "${agent_path}/server"
                echo "  [OK] removed server dir"
            fi
            # also clean .claude config
            if [[ -d "${agent_path}/.claude" ]]; then
                rm -rf "${agent_path}/.claude"
                echo "  [OK] removed .claude dir"
            fi
            echo "=== ${agent} uninstalled ==="
            continue
        fi

        local agent_path
        agent_path="$(get_agent_path "$agent")"

        echo "=== Uninstalling ${agent} ==="

        # Remove agent install directory (includes .venv)
        if [[ -d "$agent_path" ]]; then
            rm -rf "$agent_path"
            echo "  [OK] removed agent dir: ${agent_path}"
        else
            echo "  [SKIP] agent dir not found: ${agent_path}"
        fi

        # Remove config directory
        local conf_dest
        conf_dest="$(get_agent_conf_dest "$agent")"
        if [[ -n "$conf_dest" && -d "$conf_dest" ]]; then
            rm -rf "$conf_dest"
            echo "  [OK] removed config dir: ${conf_dest}"
        else
            [[ -n "$conf_dest" ]] && echo "  [SKIP] config dir not found: ${conf_dest}"
        fi

        echo "=== ${agent} uninstalled ==="
    done
}

cmd_check() {
    local agent="${1:?usage: ${SCRIPT_NAME} check <agent>}"
    require_agent "$agent"

    # claude-code: check server directory + webui
    if [[ "$agent" == "claude-code" ]]; then
        echo "=== Checking ${agent} ==="
        local agent_path
        agent_path="$(get_agent_path "claude-code")"
        local dest="${agent_path}/server"
        local errors=0

        if [[ -f "${dest}/app.py" ]]; then
            echo "  [OK] server: app.py exists"
        else
            echo "  [FAIL] server: app.py missing"
            errors=$((errors + 1))
        fi

        if [[ -f "${dest}/session.py" ]]; then
            echo "  [OK] server: session.py exists"
        else
            echo "  [FAIL] server: session.py missing"
            errors=$((errors + 1))
        fi

        if [[ -d "${dest}/webui/dist" ]]; then
            echo "  [OK] webui: dist/ exists"
        else
            echo "  [WARN] webui: dist/ not built (run: cd ${dest}/webui && npm run build)"
        fi

        if [[ -d "${dest}/webui/node_modules" ]]; then
            echo "  [OK] webui: node_modules exists"
        else
            echo "  [WARN] webui: node_modules missing (run: cd ${dest}/webui && npm install)"
        fi

        if [[ $errors -gt 0 ]]; then
            echo "=== ${agent}: FAIL (${errors} errors) ==="
            exit 1
        fi
        echo "=== ${agent}: OK ==="
        return 0
    fi

    local agent_path
    agent_path="$(get_agent_path "$agent")"
    local errors=0

    echo "=== Checking ${agent} ==="

    # 1. Agent path
    if [[ -d "$agent_path" ]]; then
        echo "  [OK] agent path exists: ${agent_path}"
    else
        echo "  [FAIL] agent path missing: ${agent_path}"
        errors=$((errors + 1))
    fi

    # 2. Virtual environment
    if [[ -d "${agent_path}/.venv" ]]; then
        echo "  [OK] venv exists: ${agent_path}/.venv"
    else
        echo "  [FAIL] venv missing: ${agent_path}/.venv"
        errors=$((errors + 1))
    fi

    # 3. Python binary
    if [[ -x "${agent_path}/.venv/bin/python" ]]; then
        echo "  [OK] python binary: ${agent_path}/.venv/bin/python"
    else
        echo "  [FAIL] python binary missing or not executable"
        errors=$((errors + 1))
    fi

    # 4. Installed packages
    local site_pkgs
    site_pkgs=$(echo "${agent_path}"/.venv/lib/python*/site-packages 2>/dev/null)
    if ls "$site_pkgs"/*.dist-info &>/dev/null 2>&1; then
        local pkg_count
        pkg_count=$(echo "$site_pkgs"/*.dist-info | wc -w | tr -d ' ')
        echo "  [OK] dependencies installed (${pkg_count} packages)"
    else
        echo "  [WARN] no installed packages found in venv"
    fi

    # 5. Config files
    local conf_dest
    conf_dest="$(get_agent_conf_dest "$agent")"
    for f in $(_conf_files "$agent"); do
        if [[ -f "${conf_dest}/${f}" ]]; then
            echo "  [OK] config file exists: ${conf_dest}/${f}"
        else
            echo "  [WARN] config file missing: ${conf_dest}/${f}"
        fi
    done

    if [[ $errors -eq 0 ]]; then
        echo "=== ${agent}: OK ==="
    else
        echo "=== ${agent}: ${errors} check(s) failed ==="
        exit 1
    fi
}

cmd_init() {
    echo "=== Initializing skillbot project ==="
    check_prereqs

    local venv_dir="${PROJECT_DIR}/.venv"
    if [[ -d "$venv_dir" ]]; then
        echo "  [SKIP] .venv already exists"
    else
        (cd "$PROJECT_DIR" && uv venv)
        echo "  [OK] uv venv created at ${venv_dir}"
    fi

    echo "  [RUN] uv pip install -e .[dev,jupyter,eval]"
    uv pip install --python "${venv_dir}/bin/python" -e "${PROJECT_DIR}[dev,jupyter,eval]"
    echo "  [OK] project dependencies installed"
    echo "=== Init complete ==="
}

# ============================================================
# Main
# ============================================================

main() {
    _load_env
    local cmd="${1:-}"

    case "$cmd" in
        init)       cmd_init ;;
        install)    cmd_install   "${2:-}" ;;
        update)     cmd_update    "${2:-}" ;;
        uninstall)  cmd_uninstall "${2:-}" ;;
        check)      cmd_check     "${2:?usage: ${SCRIPT_NAME} check <agent>}" ;;
        -h|--help|help) usage ;;
        *) usage ;;
    esac
}

main "$@"
