#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# skillbot agent framework run script
# ============================================================

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_NAME="$(basename "$0")"
AGENT_NAMES="deer-flow nanobot hermes-agent claude-code"

# Load project-level env config (only sets vars not already in environment)
_load_env() {
    local env_file="${PROJECT_DIR}/conf/.env"
    if [[ ! -f "$env_file" ]]; then
        return
    fi
    while IFS='=' read -r key value; do
        # Skip comments, empty lines, and vars already set in environment
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        key="${key%%[[:space:]]*}"
        [[ -n "${!key:-}" ]] && continue  # skip if already set externally
        export "$key=$value"
    done < "$env_file"
}

# ============================================================
# Agent metadata (bash 3.2 compatible)
# ============================================================

_git_url() {
    case "$1" in
        deer-flow)    echo "https://github.com/bytedance/deer-flow" ;;
        nanobot)      echo "https://github.com/HKUDS/nanobot" ;;
        hermes-agent) echo "https://github.com/nousresearch/hermes-agent" ;;
        claude-code)  echo "" ;;  # npm-based
    esac
}

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

_skills_path() {
    case "$1" in
        deer-flow)    echo "skills/custom" ;;
        nanobot)      echo "nanobot/skills" ;;
        hermes-agent) echo "skills/custom" ;;
        claude-code)  echo ".claude/skills" ;;
    esac
}

_start_cmd() {
    local agent="$1"
    local no_webui="${2:-false}"

    case "$agent" in
        deer-flow)
            if $no_webui; then
                echo "make -C backend gateway"
            else
                echo "make dev-daemon"
            fi
            ;;
        nanobot)      echo ".venv/bin/nanobot gateway" ;;
        hermes-agent) echo ".venv/bin/hermes gateway run --replace" ;;
        claude-code)  echo "PYTHONPATH='${agent_path}:${PROJECT_DIR}/src' ${PROJECT_DIR}/.venv/bin/python3 -c 'from server.app import main; main()'" ;;
    esac
}

# Pre-start dependency setup (e.g. deer-flow needs make install)
_setup_deps() {
    local agent="$1"
    local agent_path="$2"
    local no_webui="${3:-false}"

    case "$agent" in
        deer-flow)
            if $no_webui; then
                echo "  [SETUP] installing backend dependencies..."
                (cd "${agent_path}/backend" && uv sync --quiet)
            else
                echo "  [SETUP] checking dependencies..."
                (cd "$agent_path" && make check 2>&1 | tail -1)
                echo "  [SETUP] installing dependencies..."
                (cd "$agent_path" && make install)
            fi
            echo "  [OK] dependencies ready"
            ;;
    esac
}

# WebUI port per agent (avoid port collision on 5173)
_webui_port() {
    case "$1" in
        nanobot)      echo "5173" ;;
        hermes-agent) echo "5174" ;;
        claude-code)  echo "5175" ;;
    esac
}

# Start webui for agents that have one (nanobot, hermes-agent, claude-code)
_start_webui() {
    local agent="$1"
    local agent_path="$2"
    local log_dir="${PROJECT_DIR}/.run"
    local webui_dir=""
    local port="$(_webui_port "$agent")"

    case "$agent" in
        nanobot)      webui_dir="webui" ;;
        hermes-agent) webui_dir="web" ;;
        claude-code)  webui_dir="server/webui" ;;
        *)            return 0 ;;
    esac

    if [[ ! -f "${agent_path}/${webui_dir}/node_modules/.package-lock.json" ]] && \
       [[ ! -d "${agent_path}/${webui_dir}/node_modules" ]]; then
        echo "  [WARN] webui dependencies not installed, skipping"
        return 0
    fi

    # claude-code: build + proxy server (API :9000 proxied through :5175)
    if [[ "$agent" == "claude-code" ]]; then
        (cd "${agent_path}/${webui_dir}" && npm run build 2>/dev/null)
    fi

    # hermes-agent: start dashboard backend first (webui proxies /api to it)
    if [[ "$agent" == "hermes-agent" ]]; then
        if ! lsof -i :9119 -sTCP:LISTEN -t &>/dev/null; then
            local dash_log="${log_dir}/${agent}-dashboard.log"
            nohup "${agent_path}/.venv/bin/hermes" dashboard --no-open > "$dash_log" 2>&1 &
            sleep 2
            if lsof -i :9119 -sTCP:LISTEN -t &>/dev/null; then
                echo "  [OK] dashboard started (port 9119)"
            fi
        else
            echo "  [INFO] dashboard already running on port 9119"
        fi
    fi

    if lsof -i ":${port}" -sTCP:LISTEN -t &>/dev/null; then
        echo "  [INFO] webui already running on port ${port}"
        return 0
    fi

    local webui_log="${log_dir}/${agent}-webui.log"
    (cd "${agent_path}/${webui_dir}" && PORT="$port" nohup npm run start > "$webui_log" 2>&1 &)
    sleep 2
    if lsof -i ":${port}" -sTCP:LISTEN -t &>/dev/null; then
        echo "  [OK] webui started (http://localhost:${port})"
    else
        echo "  [WARN] webui start pending, check: tail -f ${webui_log}"
    fi
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
Usage: ${SCRIPT_NAME} <command> [agent] [...]

Commands:
  start  <agent> [model]  Start agent (daemon mode) with optional model override
  stop   [agent]          Stop running agent(s)
  status [agent]          Show agent status (running state, model, skills)
  clean  [agent]          Clean runtime artifacts (config, cache, logs)
  sync   <agent> <skills> Sync skills to agent (skills/* or skills/a,b,c)

Agents: ${AGENT_NAMES}
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
    # claude-code: config in .claude/ under agent_path (isolated home)
    [[ "$name" == "claude-code" ]] && { echo "$(get_agent_path "$name")/.claude"; return; }
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

get_pid_file() {
    echo "${PROJECT_DIR}/.run/${1}.pid"
}

get_log_file() {
    echo "${PROJECT_DIR}/.run/${1}.log"
}

require_agent() {
    local name="$1"
    if ! _is_known_agent "$name"; then
        echo "ERROR: unknown agent '${name}'. Known: ${AGENT_NAMES}" >&2
        exit 1
    fi
}

check_installed() {
    local agent="$1"
    if [[ "$agent" == "claude-code" ]]; then
        if ! command -v claude &>/dev/null; then
            echo "ERROR: claude not found. Run: install.sh install claude-code" >&2
            exit 1
        fi
        return 0
    fi
    local agent_path
    agent_path="$(get_agent_path "$agent")"
    if [[ ! -d "$agent_path" ]]; then
        echo "ERROR: ${agent} is not installed. Run: install.sh install ${agent}" >&2
        exit 1
    fi
    if [[ ! -d "${agent_path}/.venv" ]]; then
        echo "ERROR: ${agent} venv not found. Run: install.sh install ${agent}" >&2
        exit 1
    fi
}

# ============================================================
# Config helpers
# ============================================================

# Write model name into agent config
_set_model_in_config() {
    local agent="$1"
    local model="$2"
    local conf_dest
    conf_dest="$(get_agent_conf_dest "$agent")"

    case "$agent" in
        deer-flow)
            # Update the first model entry's name/display_name/model in the existing models list.
            # Preserve use:, api_key:, supports_thinking: etc.
            # Match only lines under "models:" that start with "  - name:" / "    display_name:" / "    model:"
            local cfg="${conf_dest}/config.yaml"
            local done_name=false done_display=false done_model=false
            local in_models=false
            local tmpcfg="${cfg}.tmp"
            > "$tmpcfg"
            while IFS= read -r line; do
                if [[ "$line" =~ ^models: ]]; then
                    in_models=true
                elif $in_models && [[ "$line" =~ ^[a-z_] ]]; then
                    in_models=false
                fi
                if $in_models && [[ "$line" =~ ^[[:space:]]+-[[:space:]]+name: ]] && ! $done_name; then
                    echo "  - name: ${model}" >> "$tmpcfg"
                    done_name=true
                elif $in_models && [[ "$line" =~ ^[[:space:]]+display_name: ]] && ! $done_display; then
                    echo "    display_name: ${model}" >> "$tmpcfg"
                    done_display=true
                elif $in_models && [[ "$line" =~ ^[[:space:]]+model:[[:space:]] ]] && ! $done_model; then
                    echo "    model: ${model}" >> "$tmpcfg"
                    done_model=true
                else
                    echo "$line" >> "$tmpcfg"
                fi
            done < "$cfg"
            mv "$tmpcfg" "$cfg"
            ;;
        hermes-agent)
            if grep -q "^model:" "$conf_dest/config.yaml" 2>/dev/null; then
                sed -i '' "s/^model:.*/model: ${model}/" "$conf_dest/config.yaml" 2>/dev/null || \
                sed -i "s/^model:.*/model: ${model}/" "$conf_dest/config.yaml"
            else
                echo "model: ${model}" >> "$conf_dest/config.yaml"
            fi
            ;;
        nanobot)
            # JSON config: write agents.defaults.model
            local tmpfile
            tmpfile="${conf_dest}/config.json.tmp"
            python3 -c "
import json, sys
with open('${conf_dest}/config.json') as f:
    cfg = json.load(f)
cfg.setdefault('agents', {}).setdefault('defaults', {})['model'] = '${model}'
with open('${tmpfile}', 'w') as f:
    json.dump(cfg, f, indent=2)
" && mv "$tmpfile" "${conf_dest}/config.json"
            ;;
    esac
}

# Read current model from agent config
_get_model_from_config() {
    local agent="$1"
    local conf_dest
    conf_dest="$(get_agent_conf_dest "$agent")"

    case "$agent" in
        deer-flow)
            grep "^    model:" "$conf_dest/config.yaml" 2>/dev/null | tail -1 | sed 's/.*model: //' || echo "none"
            ;;
        nanobot)
            python3 -c "
import json
with open('${conf_dest}/config.json') as f:
    cfg = json.load(f)
print(cfg.get('agents',{}).get('defaults',{}).get('model','none'))
" 2>/dev/null || echo "none"
            ;;
        hermes-agent)
            grep "^model:" "$conf_dest/config.yaml" 2>/dev/null | head -1 | sed 's/^model: //' || echo "none"
            ;;
        *) echo "none" ;;
    esac
}

# Get skills list from agent
_get_skills_list() {
    local agent="$1"
    local agent_path
    agent_path="$(get_agent_path "$agent")"
    local spath="${agent_path}/$(_skills_path "$agent")"

    if [[ -d "$spath" ]]; then
        ls -1 "$spath" 2>/dev/null | tr '\n' ' ' || echo "(empty)"
    else
        echo "(missing)"
    fi
}

# Check if agent is currently running
_is_running() {
    local agent="$1"
    local pid_file
    pid_file="$(get_pid_file "$agent")"

    # pid file check (works for nanobot, hermes-agent)
    if [[ -f "$pid_file" ]]; then
        local pid
        pid="$(cat "$pid_file")"
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi

    # Fallback checks for agents that daemonize internally
    case "$agent" in
        deer-flow)
            lsof -i :8001 -sTCP:LISTEN -t &>/dev/null && return 0
            ;;
        hermes-agent)
            pgrep -f "python.*hermes.*gateway run" &>/dev/null && return 0
            ;;
        claude-code)
            lsof -i :9000 -sTCP:LISTEN -t &>/dev/null && return 0
            ;;
    esac

    return 1
}

# ============================================================
# Commands
# ============================================================

cmd_start() {
    local agent="${1:?usage: ${SCRIPT_NAME} start <agent> [model] [--no-webui]}"
    shift
    local model=""
    local no_webui=false

    # Parse remaining args
    for arg in "$@"; do
        case "$arg" in
            --no-webui) no_webui=true ;;
            --*) ;;  # skip unknown flags
            *) model="$arg" ;;
        esac
    done

    require_agent "$agent"
    check_installed "$agent"

    local agent_path
    agent_path="$(get_agent_path "$agent")"

    echo "=== Starting ${agent} ==="

    # Step b: init config — sync conf/agent_conf/<agent>/* to config destination (first)
    local conf_src
    conf_src="$(get_agent_conf_src "$agent")"
    local conf_dest
    conf_dest="$(get_agent_conf_dest "$agent")"
    if [[ -d "$conf_src" ]]; then
        mkdir -p "$conf_dest"
        shopt -s dotglob 2>/dev/null || true
        cp -r "${conf_src}/"* "$conf_dest" 2>/dev/null || true
        shopt -u dotglob 2>/dev/null || true
        echo "  [CONF] config synced: ${conf_src} -> ${conf_dest}"
    else
        echo "  [WARN] config source not found: ${conf_src}"
    fi

    # Step a: configure default model (after config sync so it overrides template)
    if [[ -n "$model" ]]; then
        echo "  [CONF] setting default model: ${model}"
        _set_model_in_config "$agent" "$model"
    fi

    # Verify model is configured
    local current_model
    current_model="$(_get_model_from_config "$agent")"
    if [[ "$current_model" == "none" || -z "$current_model" ]]; then
        echo "  [WARN] no default model configured. Set via: ${SCRIPT_NAME} start ${agent} <model>"
    else
        echo "  [INFO] model: ${current_model}"
    fi

    # Setup dependencies before start (e.g. deer-flow make install)
    _setup_deps "$agent" "$agent_path" "$no_webui"

    # Step c: start agent daemon
    mkdir -p "${PROJECT_DIR}/.run"

    local pid_file
    pid_file="$(get_pid_file "$agent")"
    local log_file
    log_file="$(get_log_file "$agent")"

    if _is_running "$agent"; then
        echo "  [SKIP] ${agent} is already running (pid $(cat "$pid_file" 2>/dev/null || echo '?'))"
        echo "=== ${agent}: already running ==="
        return 0
    fi

    # Build env-file sourcing preamble — loads .env from config dest + project root
    local env_preamble=""
    if [[ -f "${conf_dest}/.env" ]]; then
        env_preamble+="export \$(grep -v '^#' '${conf_dest}/.env' | xargs) 2>/dev/null; "
    fi
    if [[ -f "${PROJECT_DIR}/.env" ]]; then
        env_preamble+="export \$(grep -v '^#' '${PROJECT_DIR}/.env' | xargs) 2>/dev/null; "
    fi
    if [[ -n "$env_preamble" ]]; then
        echo "  [ENV] loaded env vars from .env file(s)"
    fi

    local start_cmd
    start_cmd="$(_start_cmd "$agent" "$no_webui")"

    # claude-code: PYTHONPATH uses agent_path to resolve 'server' package
    if [[ "$agent" == "claude-code" ]]; then
        local webui_env=""
        if $no_webui; then
            webui_env="CLAUDE_SERVER_NO_WEBUI=true "
            echo "  [INFO] webui disabled (--no-webui)"
        fi
        nohup bash -c "${webui_env}${env_preamble}cd '${agent_path}' && $start_cmd" > "$log_file" 2>&1 &
    else
        nohup bash -c "${env_preamble}cd '$agent_path' && $start_cmd" > "$log_file" 2>&1 &
    fi
    echo $! > "$pid_file"

    sleep 4
    # hermes-agent: capture real gateway pid (nohup bash exits after fork)
    if [[ "$agent" == "hermes-agent" ]]; then
        local real_pid tries=0
        while [[ $tries -lt 5 ]]; do
            real_pid=$(pgrep -f "python.*hermes.*gateway run" 2>/dev/null | tail -1 || true)
            [[ -n "$real_pid" ]] && break
            sleep 1
            tries=$((tries + 1))
        done
        if [[ -n "$real_pid" ]]; then
            echo "$real_pid" > "$pid_file"
        fi
    fi

    if _is_running "$agent"; then
        echo "  [OK] started (pid $(cat "$pid_file"))"
        echo "  [LOG] ${log_file}"
        local m
        m="$(_get_model_from_config "$agent")"
        echo "  [STATUS] running | model: ${m} | skills: $(_get_skills_list "$agent")"
    else
        echo "  [FAIL] agent may have exited. Check log: ${log_file}"
        rm -f "$pid_file"
        exit 1
    fi

    # Start webui if available (skip if --no-webui)
    if ! $no_webui; then
        _start_webui "$agent" "$agent_path"
    fi

    echo "=== ${agent} started ==="
}

cmd_stop() {
    for agent in ${1:-$AGENT_NAMES}; do
        _is_known_agent "$agent" || { echo "  [SKIP] unknown agent: ${agent}"; continue; }

        local agent_path
        agent_path="$(get_agent_path "$agent")"
        local pid_file
        pid_file="$(get_pid_file "$agent")"

        echo "=== Stopping ${agent} ==="

        # Use agent-specific stop command first (handles subprocesses)
        case "$agent" in
            deer-flow)
                if [[ -d "$agent_path" ]]; then
                    (cd "$agent_path" && make stop 2>&1) || true
                fi
                ;;
            nanobot)
                pkill -f "nanobot gateway" 2>/dev/null || true
                # Also stop webui if running
                if lsof -i ":$(_webui_port "$agent")" -sTCP:LISTEN -t &>/dev/null; then
                    lsof -i ":$(_webui_port "$agent")" -sTCP:LISTEN -t 2>/dev/null | xargs kill 2>/dev/null || true
                    [[ -f "${agent_path}/webui/node_modules/.vite" ]] && rm -rf "${agent_path}/webui/node_modules/.vite" 2>/dev/null || true
                    echo "  [OK] webui stopped"
                fi
                ;;
            claude-code)
                if lsof -i :9000 -sTCP:LISTEN -t &>/dev/null; then
                    lsof -i :9000 -sTCP:LISTEN -t 2>/dev/null | xargs kill 2>/dev/null || true
                    sleep 1
                    # kill orphaned SDK-spawned claude subprocesses
                    pkill -f "_bundled/claude" 2>/dev/null || true
                    echo "  [OK] claude server stopped"
                fi
                if lsof -i ":$(_webui_port "$agent")" -sTCP:LISTEN -t &>/dev/null; then
                    lsof -i ":$(_webui_port "$agent")" -sTCP:LISTEN -t 2>/dev/null | xargs kill 2>/dev/null || true
                    echo "  [OK] webui stopped"
                fi
                ;;
            hermes-agent)
                # Stop webui
                if lsof -i ":$(_webui_port "$agent")" -sTCP:LISTEN -t &>/dev/null; then
                    lsof -i ":$(_webui_port "$agent")" -sTCP:LISTEN -t 2>/dev/null | xargs kill 2>/dev/null || true
                    echo "  [OK] webui stopped"
                fi
                # Stop dashboard
                if lsof -i :9119 -sTCP:LISTEN -t &>/dev/null; then
                    lsof -i :9119 -sTCP:LISTEN -t 2>/dev/null | xargs kill 2>/dev/null || true
                    echo "  [OK] dashboard stopped"
                fi
                # Stop gateway: use hermes' own stop first, then force-kill all hermes
                "${agent_path}/.venv/bin/hermes" gateway stop 2>/dev/null || true
                sleep 1
                local tries=0 killed=false
                while pgrep -f hermes &>/dev/null && [[ $tries -lt 5 ]]; do
                    pkill -9 -f hermes 2>/dev/null || true
                    killed=true
                    sleep 1
                    tries=$((tries + 1))
                done
                if $killed && ! pgrep -f hermes &>/dev/null; then
                    echo "  [OK] hermes gateway stopped"
                fi
                ;;
        esac

        # Kill tracked pid if still alive
        if [[ -f "$pid_file" ]]; then
            local pid
            pid="$(cat "$pid_file")"
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
                sleep 1
                kill -9 "$pid" 2>/dev/null || true
            fi
            rm -f "$pid_file"
        fi

        echo "=== ${agent}: stopped ==="
    done
}

cmd_status() {
    for agent in ${1:-$AGENT_NAMES}; do
        _is_known_agent "$agent" || { echo "  [SKIP] unknown agent: ${agent}"; continue; }
        check_installed "$agent" 2>/dev/null || continue

        local agent_path
        agent_path="$(get_agent_path "$agent")"
        local pid_file
        pid_file="$(get_pid_file "$agent")"

        echo "=== ${agent} ==="

        # --- Running state + process / port info ---
        local running=false
        if [[ -f "$pid_file" ]]; then
            local pid
            pid="$(cat "$pid_file")"
            if kill -0 "$pid" 2>/dev/null; then
                running=true
            fi
        fi

        # Agent-specific process / port detection
        case "$agent" in
            deer-flow)
                # Port-based detection — more reliable than pgrep
                local gw_listen fp_listen nx_listen
                gw_listen=$(lsof -i :8001 -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
                fp_listen=$(lsof -i :3000 -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
                nx_listen=$(lsof -i :2026 -sTCP:LISTEN -t 2>/dev/null | head -1 || true)

                if [[ -n "$gw_listen" ]]; then
                    echo "  status:    RUNNING"
                    echo "  process:"
                    echo "    Gateway   pid ${gw_listen}  port 8001"
                    [[ -n "$fp_listen" ]] && echo "    Frontend  pid ${fp_listen}  port 3000"
                    [[ -n "$nx_listen" ]] && echo "    Nginx     pid ${nx_listen}  port 2026"
                    echo "  url:       http://localhost:2026"
                elif $running; then
                    echo "  status:    STARTING (pid file present, services pending)"
                else
                    echo "  status:    STOPPED"
                fi
                ;;
            nanobot)
                local gw_pid webui_pid
                gw_pid=$(lsof -i :18790 -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
                webui_pid=$(lsof -i ":$(_webui_port "$agent")" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)

                if [[ -n "$gw_pid" ]]; then
                    echo "  status:    RUNNING"
                    echo "  process:"
                    echo "    Gateway   pid ${gw_pid}  port 18790"
                    [[ -n "$webui_pid" ]] && echo "    WebUI     pid ${webui_pid}  port $(_webui_port "$agent") (http://localhost:$(_webui_port "$agent"))"
                elif $running; then
                    echo "  status:    STARTING (pid file present, services pending)"
                else
                    echo "  status:    STOPPED"
                fi
                ;;
            hermes-agent)
                local hpid dash_pid webui_pid
                hpid=$(cat "$pid_file" 2>/dev/null || true)
                dash_pid=$(lsof -i :9119 -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
                webui_pid=$(lsof -i ":$(_webui_port "$agent")" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)

                # pid_file may be stale (nohup bash exits); fall back to pgrep
                if [[ -n "$hpid" ]] && kill -0 "$hpid" 2>/dev/null; then
                    running=true
                elif [[ -z "$hpid" || "$hpid" == "0" ]] && pgrep -f "hermes.*gateway run" &>/dev/null; then
                    hpid=$(pgrep -f "hermes.*gateway run" 2>/dev/null | tail -1 || true)
                    running=true
                fi

                if $running; then
                    echo "  status:    RUNNING"
                    echo "  process:"
                    echo "    Gateway   pid ${hpid}"
                    [[ -n "$dash_pid" ]] && echo "    Dashboard pid ${dash_pid}  port 9119"
                    [[ -n "$webui_pid" ]] && echo "    WebUI     pid ${webui_pid}  port $(_webui_port "$agent") (http://localhost:$(_webui_port "$agent"))"
                elif _is_running "$agent"; then
                    echo "  status:    STARTING"
                else
                    echo "  status:    STOPPED"
                fi
                ;;
            claude-code)
                local cpid
                cpid=$(lsof -i :9000 -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
                if [[ -n "$cpid" ]]; then
                    echo "  status:    RUNNING"
                    echo "  process:   pid ${cpid}  port 9000"
                else
                    echo "  status:    STOPPED"
                fi
                ;;
        esac

        # --- Default model ---
        local model
        model="$(_get_model_from_config "$agent")"
        echo "  model:     ${model:-none}"

        # --- Skills list ---
        local skills
        skills="$(_get_skills_list "$agent")"
        echo "  skills:    ${skills:-none}"
    done
}

cmd_clean() {
    for agent in ${1:-$AGENT_NAMES}; do
        _is_known_agent "$agent" || { echo "  [SKIP] unknown agent: ${agent}"; continue; }

        echo "=== Cleaning ${agent} ==="

        # Stop first if running (use agent-specific stop for reliability)
        if _is_running "$agent"; then
            local ap
            ap="$(get_agent_path "$agent")"
            case "$agent" in
                deer-flow)
                    (cd "$ap" && make stop 2>&1) || true
                    ;;
                nanobot)
                    pkill -f "nanobot gateway" 2>/dev/null || true
                    lsof -i ":$(_webui_port "$agent")" -sTCP:LISTEN -t 2>/dev/null | xargs kill 2>/dev/null || true
                    ;;
                hermes-agent)
                    pkill -9 -f "hermes.*gateway" 2>/dev/null || true
                    sleep 1
                    ;;
                claude-code)
                    lsof -i :9000 -sTCP:LISTEN -t 2>/dev/null | xargs kill 2>/dev/null || true
                    pkill -f "_bundled/claude" 2>/dev/null || true
                    lsof -i ":$(_webui_port "$agent")" -sTCP:LISTEN -t 2>/dev/null | xargs kill 2>/dev/null || true
                    ;;
            esac
            echo "  [OK] stopped running instance"
        fi
        # Also clean up stale pid file
        rm -f "$(get_pid_file "$agent")"

        # Remove config
        # "home" type (conf in ~/.xxx): safe to delete entire dir
        # "agent" type (conf == agent_path): only remove specific files
        local conf_dest
        conf_dest="$(get_agent_conf_dest "$agent")"
        local agent_path
        agent_path="$(get_agent_path "$agent")"

        # claude-code: remove everything except server/ + .claude/skills/
        if [[ "$agent" == "claude-code" ]]; then
            local claude_dir="${agent_path}/.claude"
            # save skills/ temporarily, wipe .claude/, restore skills/
            if [[ -d "${claude_dir}/skills" ]]; then
                mv "${claude_dir}/skills" "${agent_path}/.skills-tmp" 2>/dev/null
            fi
            rm -rf "$claude_dir" 2>/dev/null
            mkdir -p "$claude_dir"
            if [[ -d "${agent_path}/.skills-tmp" ]]; then
                mv "${agent_path}/.skills-tmp" "${claude_dir}/skills"
            fi
            # wipe everything else in agent_path except server/ + .claude/
            shopt -s dotglob 2>/dev/null || true
            for item in "$agent_path"/*; do
                local name; name="$(basename "$item")"
                [[ "$name" == "." || "$name" == ".." ]] && continue
                [[ "$name" == "server" || "$name" == ".claude" ]] && continue
                rm -rf "$item"
            done
            shopt -u dotglob 2>/dev/null || true
            echo "  [OK] cleaned (kept server/ + .claude/skills/)"
        elif [[ "$(_conf_type "$agent")" == "home" ]]; then
            if [[ -n "$conf_dest" && -d "$conf_dest" ]]; then
                rm -rf "$conf_dest"
                echo "  [OK] removed config dir: ${conf_dest}"
            fi
        else
            if [[ -n "$conf_dest" ]]; then
                for f in $(_conf_files "$agent"); do
                    if [[ -f "${conf_dest}/${f}" ]]; then
                        rm -f "${conf_dest}/${f}"
                        echo "  [OK] removed config file: ${conf_dest}/${f}"
                    fi
                done
                if [[ -f "${conf_dest}/.env" ]]; then
                    rm -f "${conf_dest}/.env"
                    echo "  [OK] removed config file: ${conf_dest}/.env"
                fi
            fi
        fi

        # Remove runtime cache data in agent path (non-claude agents)
        if [[ "$agent" != "claude-code" && -d "$agent_path" ]]; then
            for d in .deer-flow .cache __pycache__ logs; do
                if [[ -d "${agent_path}/${d}" ]]; then
                    rm -rf "${agent_path}/${d}"
                    echo "  [OK] removed cache: ${agent_path}/${d}"
                fi
            done
            if [[ -d "${agent_path}/backend/.deer-flow" ]]; then
                rm -rf "${agent_path}/backend/.deer-flow"
                echo "  [OK] removed cache: ${agent_path}/backend/.deer-flow"
            fi
        fi

        # Remove run logs
        local log_file
        log_file="$(get_log_file "$agent")"
        if [[ -f "$log_file" ]]; then
            rm -f "$log_file"
            echo "  [OK] removed log: ${log_file}"
        fi
        # Also remove webui / dashboard logs
        for suffix in webui dashboard; do
            local extra_log="${PROJECT_DIR}/.run/${agent}-${suffix}.log"
            if [[ -f "$extra_log" ]]; then
                rm -f "$extra_log"
                echo "  [OK] removed log: ${extra_log}"
            fi
        done

        echo "=== ${agent} cleaned ==="
    done
}

cmd_sync() {
    local agent="${1:?usage: ${SCRIPT_NAME} sync <agent> [skills]}"
    local skills_arg="${2:-}"
    # Capture extra args (shell-expanded wildcard) before shifting
    if [[ $# -gt 2 ]]; then
        local extra="${*:3}"
        skills_arg="${skills_arg:+${skills_arg},}${extra// /,}"
    fi

    # If no skills_arg provided, fall back to SKILL_BOT_SKILL_PATH env var
    if [[ -z "$skills_arg" ]]; then
        if [[ -n "${SKILL_BOT_SKILL_PATH:-}" ]]; then
            skills_arg="$SKILL_BOT_SKILL_PATH"
            echo "  [ENV] using SKILL_BOT_SKILL_PATH=${skills_arg}"
        else
            echo "ERROR: no skills specified. Use: ${SCRIPT_NAME} sync <agent> <skills>" >&2
            echo "       Or set SKILL_BOT_SKILL_PATH env var." >&2
            exit 1
        fi
    fi

    require_agent "$agent"
    check_installed "$agent"

    # Only allow sync when agent is stopped
    if _is_running "$agent"; then
        echo "ERROR: ${agent} is currently running. Stop it first: ${SCRIPT_NAME} stop ${agent}" >&2
        exit 1
    fi

    local agent_path
    agent_path="$(get_agent_path "$agent")"
    local dest="${agent_path}/$(_skills_path "$agent")"
    local src_dir="${PROJECT_DIR}/skills"

    echo "=== Syncing skills to ${agent} ==="

    if [[ ! -d "$src_dir" ]]; then
        echo "  [FAIL] skills source directory not found: ${src_dir}"
        exit 1
    fi

    echo "  source: ${src_dir}"
    echo "  target: ${dest}"

    # Clear target skill directory first
    if [[ -d "$dest" ]]; then
        rm -rf "${dest:?}"/*
        echo "  [OK] cleared target"
    fi
    mkdir -p "$dest"

    # Parse skills_arg
    # "skills/*"              -> copy all skills under src_dir
    # "skills/sA,skills/sB"   -> copy specific skills (comma-separated)
    # "/abs/path/to/skills"   -> absolute path — copy all from that dir
    if [[ "$skills_arg" == "skills/*" ]] || [[ "$skills_arg" == "${src_dir}" ]] || [[ "$skills_arg" == "${src_dir}/" ]]; then
        shopt -s dotglob 2>/dev/null || true
        cp -r "${src_dir}/"* "$dest"/
        shopt -u dotglob 2>/dev/null || true
        echo "  [OK] synced all skills"
    elif [[ "$skills_arg" == /* ]]; then
        # Absolute path — copy skills from external directory
        local count=0
        shopt -s dotglob 2>/dev/null || true
        for s in "$skills_arg"/*/; do
            local skill_name
            skill_name="$(basename "$s")"
            cp -r "$s" "$dest/"
            echo "  [OK] ${skill_name}"
            count=$((count + 1))
        done
        shopt -u dotglob 2>/dev/null || true
        echo "  [OK] synced ${count} skills from ${skills_arg}"
    else
        local count=0
        local IFS=','
        for s in $skills_arg; do
            local skill_name="${s#skills/}"
            skill_name="${skill_name#${src_dir}/}"
            skill_name="${skill_name#${src_dir}}"
            local skill_src="${src_dir}/${skill_name}"
            if [[ -d "$skill_src" ]]; then
                cp -r "$skill_src" "$dest/"
                echo "  [OK] ${skill_name}"
                count=$((count + 1))
            else
                echo "  [WARN] skill not found: ${skill_src}"
            fi
        done
    fi

    echo ""
    echo "  result: $(_get_skills_list "$agent")"
    echo "=== ${agent} skills synced ==="
}

# ============================================================
# Main
# ============================================================

main() {
    _load_env
    local cmd="${1:-}"

    case "$cmd" in
        start)
            shift
            cmd_start "$@"
            ;;
        stop)
            cmd_stop "${2:-}"
            ;;
        status)
            cmd_status "${2:-}"
            ;;
        clean)
            cmd_clean "${2:-}"
            ;;
        sync)
            cmd_sync "${2:-}" ${3:+"${@:3}"}
            ;;
        -h|--help|help)
            usage
            ;;
        *)
            usage
            ;;
    esac
}

main "$@"
