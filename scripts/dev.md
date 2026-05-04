# skillbot 开发脚本

## Step 1: 安装脚本 install.sh

### 环境变量加载

所有命令执行前自动加载 `conf/.env`（`_load_env` 在 `main()` 入口），不会覆盖已在环境中设置的变量。

自定义变量示例：
```bash
# conf/.env
DEEPSEEK_API_KEY=sk-xxx
SKILL_BOT_SKILL_PATH=skills/*
SKILL_BOT_SKILL_DIR=/custom/skills/path    # 可选，覆盖默认源目录
```

### 安装配置

```bash
[agent_path]
default: ${PROJECT_DIR}/agents/
指定安装目录: SKILL_BOT_AGENT_INSTALL_DIR=/opt/skillbot/agents/

[agent_conf_path]
default: ${PROJECT_DIR}/conf/agent_conf/[agent-name]/
```

### 命令签名

```bash
install.sh [install|uninstall|update|check] [agent]
```

### 命令详解

| 命令 | 说明 |
|------|------|
| `install [agent]` | clone 仓库 → 创建 uv venv → 安装 Python 依赖 → 安装 WebUI 依赖 |
| `uninstall [agent]` | 删除 agent 目录 + 删除 config 目录（home 型整目录，agent 型逐文件） |
| `update [agent]` | git pull → 更新 Python 依赖 → 更新 WebUI 依赖 |
| `check [agent]` | 检查 agent path / venv / python binary / packages / config 文件 |

### 示例

```bash
# 安装所有 agent（deer-flow + nanobot + hermes-agent）
install.sh install

# 安装 deer-flow
## ① clone https://github.com/bytedance/deer-flow → agents/deer-flow
## ② uv venv .venv (CPython 3.12)
## ③ uv pip install -e .（根 pyproject.toml）
## 注：deer-flow 实际依赖在 backend/.venv，由 run.sh start 的 make install 管理
install.sh install deer-flow

# 安装 nanobot（含 WebUI）
## ① clone → uv venv → uv pip install -e . (109 Python 包)
## ② cd webui && npm install (410 npm 包)
install.sh install nanobot

# 安装 hermes-agent（含 WebUI + Dashboard）
## ① clone → uv venv → uv pip install -e . (61 基础包)
## ② uv pip install -e ".[web]" (+9 packages: fastapi + uvicorn)
## ③ cd web && npm install (345 npm 包)
install.sh install hermes-agent

# 卸载 agent（删除 agent 目录 + 配置）
## nanobot (~/.nanobot/) → 整目录删除（home 型）
## hermes (~/.hermes/) → 整目录删除（home 型）
## deer-flow (agents/deer-flow/) → 仅删除 config.yaml .env（agent 型，config 在 agent 内）
install.sh uninstall nanobot
install.sh uninstall                          # 卸载全部

# 更新 agent 到最新版本
install.sh update nanobot                     # git pull + pip install + npm install
install.sh update                             # 更新全部

# 安装 claude-code（npm 全局安装）
install.sh install claude-code

# 检查安装状态
install.sh check deer-flow                    # 检查 5 项：path / venv / python / packages / config
install.sh check claude-code                  # 检查 claude 二进制是否存在
```

### 支持的 agent 列表

| Agent name | Git Url                                      | Agent Config Path | Config Files | Skills Path                  |
|---|----------------------------------------------|---|---|------------------------------|
| deer-flow | https://github.com/bytedance/deer-flow       | ${agent_path}/ | config.yaml .env | ${agent_path}/skills/custom  |
| nanobot | https://github.com/HKUDS/nanobot             | ~/.nanobot/ | config.json | ${agent_path}/nanobot/skills |
| hermes-agent | https://github.com/nousresearch/hermes-agent | ~/.hermes/ | config.yaml .env | ${agent_path}/skills/custom  |
|claude-code| npm包路径：anthropic-ai/claude-code@latest       |${agent_path}/| settings.json .env| ${agent_path}/.claude/skills |
### WebUI 安装策略

| Agent | WebUI 位置 | 安装命令 | Python Dashboard 依赖 |
|-------|-----------|---------|---------------------|
| deer-flow | Next.js（集成在 make dev-daemon） | make install | 无需额外操作 |
| nanobot | webui/ (Vite + React) | npm install | 无 |
| hermes-agent | web/ (Vite + React) | npm install | uv pip install -e ".[web]" (fastapi + uvicorn) |
| claude-code | — | 无需安装 | 无需额外操作 |

---

## Step2: 运行脚本 run.sh

### 命令签名

```bash
run.sh start   [agent] [model] [--no-webui]
run.sh stop    [agent]
run.sh status  [agent]
run.sh clean   [agent]
run.sh sync    [agent] <skills>
```

### 命令详解

#### start — 启动 agent（daemon 模式）

```
run.sh start <agent> [model] [--no-webui]
```

对每个 agent 执行：
1. **config sync**：`conf/agent_conf/<agent>/*` → config 目标目录
2. **model 配置**：如果指定 model，写入配置文件
3. **依赖安装**：deer-flow 执行 `make install`（--no-webui 时仅 `uv sync`）
4. **启动 daemon**：nohup 后台运行
5. **WebUI 启动**：自动检测并启动 webui（--no-webui 跳过）

| Agent | --no-webui 行为 |
|-------|----------------|
| deer-flow | `make -C backend gateway` 仅 Gateway(8001)，跳过 Frontend(3000)+Nginx(2026) |
| nanobot | 仅 Gateway(18790)，跳过 WebUI Vite(5173) |
| hermes-agent | 仅 Gateway，跳过 Dashboard(9119)+WebUI(5173) |
| claude-code | 不适用（HTTP Server 无 WebUI） |

#### stop — 停止 agent

```
run.sh stop [agent]
```

- deer-flow：`make stop`（停止 Gateway + Frontend + Nginx）
- nanobot：pkill gateway + pkill webui(:5173)
- hermes-agent：pkill webui(:5173) → pkill dashboard(:9119) → `hermes gateway stop` → pkill -9 all hermes（5 次重试防 auto-restart）
- claude-code：`lsof -i :9000 -t | xargs kill`（通过端口终止 HTTP server）

#### status — 查看运行状态

```
run.sh status [agent]
```

显示：运行状态 + 进程/PID/端口 + 默认模型 + skills 列表

```bash
# deer-flow 示例输出
=== deer-flow ===
  status:    RUNNING
  process:
    Gateway   pid 76503  port 8001
    Frontend  pid 76540  port 3000
    Nginx     pid 76549  port 2026
  url:       http://localhost:2026
  model:     deepseek-v4-flash
  skills:    code-review web-search

# hermes-agent 示例输出
=== hermes-agent ===
  status:    RUNNING
  process:
    Gateway   pid 56145
    Dashboard pid 59955  port 9119
    WebUI     pid 56277  port 5173 (http://localhost:5173)
  model:     deepseek-v4-flash
  skills:    code-review web-search

# claude-code 示例输出
=== claude-code ===
  status:    RUNNING
  process:   pid 74084  port 9000
  model:     none
  skills:    stock-analysis stock-data-fetch
```

#### clean — 清理运行时数据

```
run.sh clean [agent]
```

- 停止 agent（如果运行中）
- 删除配置文件 + 缓存目录 + 运行日志
- **home 型**（nanobot/hermes）：删除整 config 目录
- **agent 型**（deer-flow）：仅删除 config.yaml/.env，保留 agent 代码
- 额外清理：`.deer-flow/` `backend/.deer-flow/` `__pycache__/` `logs/`

```bash
# nanobot clean — 整目录删除
[OK] removed config dir: ~/.nanobot/

# deer-flow clean — 仅删除配置文件和缓存
[OK] removed config file: config.yaml
[OK] removed config file: .env
[OK] removed cache: backend/.deer-flow
[OK] removed log: .run/deer-flow.log
```

#### sync — 同步 skills

```
run.sh sync <agent> [skills]
```

仅在 agent **未启动** 状态可执行。先清空目标目录，再复制 skill。
如果省略 `[skills]` 参数，自动从 `SKILL_BOT_SKILL_PATH` 环境变量读取（支持相对路径 `skills/*`、逗号列表 `skills/A,skills/B`、绝对路径 `/abs/path`）。
源目录默认 `${PROJECT_DIR}/skills`，可通过 `SKILL_BOT_SKILL_DIR` 覆盖。

```bash
# 通过环境变量预设 skill 路径（无需每次输入）
export SKILL_BOT_SKILL_PATH="skills/*"
run.sh sync deer-flow                    # 自动 sync 所有 skill
run.sh sync hermes-agent                # 同样生效

# 逗号分隔指定 skills
export SKILL_BOT_SKILL_PATH="skills/skillA,skills/skillB"
run.sh sync deer-flow                    # sync skillA + skillB

# CLI 参数优先于环境变量
SKILL_BOT_SKILL_PATH="skills/*" run.sh sync deer-flow skills/code-review
# → 仅 sync code-review（忽略 SKILL_BOT_SKILL_PATH）

# 传统方式：每次指定 skills
run.sh sync deer-flow skills/*
run.sh sync deer-flow skills/skillA,skills/skillB

# 运行时拒绝同步
run.sh sync deer-flow skills/*
# → ERROR: deer-flow is currently running. Stop it first.
```

| Agent | 目标路径 |
|-------|---------|
| deer-flow | agents/deer-flow/skills/custom/ |
| nanobot | agents/nanobot/nanobot/skills/ |
| hermes-agent | agents/hermes-agent/skills/custom/ |
| claude-code | agents/claude-code/.claude/skills/ |

### 完整流程示例

```bash
# 1. 安装
install.sh install deer-flow
install.sh install nanobot
install.sh install hermes-agent

# 2. 启动（带模型配置）
run.sh start deer-flow deepseek-v4-flash
run.sh start nanobot deepseek-v4-flash --no-webui       # 仅 Gateway
run.sh start hermes-agent deepseek-v4-flash              # 全栈含 WebUI
python3 -c "from server.app import main; main()"        # Claude Code HTTP Server

# 3. 查看状态
run.sh status                     # 所有 agent
run.sh status deer-flow           # 指定 agent

# 4. 同步 skills
run.sh stop deer-flow
run.sh sync deer-flow skills/*
run.sh start deer-flow deepseek-v4-flash

# 5. 停止
run.sh stop                       # 停止所有
run.sh stop hermes-agent

# 6. 清理运行时数据（保留 agent 安装）
run.sh clean nanobot

# 7. 卸载（完全移除）
install.sh uninstall nanobot
```

### 端口参考

| Agent | Gateway | Frontend/WebUI | Dashboard | API Server |
|-------|---------|----------------|-----------|------------|
| deer-flow | 8001 | 3000 / 2026 (Nginx) | — | — |
| nanobot | 18790 | 5173 (Vite) | — | 8900 (nanobot serve) |
| hermes-agent | — | 5173 (Vite) | 9119 | 8642 (/v1/chat) |
| claude-code | — | — | — | 9000 (HTTP) |
