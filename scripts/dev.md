# skillbot 开发脚本

## Step 1: 安装脚本 install.sh

### 环境变量加载

所有命令执行前自动加载 `conf/.env`（`_load_env` 在 `main()` 入口），不会覆盖已在环境中设置的变量。

自定义变量示例：
```bash
# conf/.env
DEEPSEEK_API_KEY=sk-xxx
SKILL_BOT_SKILL_PATH=skills/*
SKILL_BOT_AGENT_INSTALL_DIR=/opt/skillbot/agents  # 可选，覆盖安装目录
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
| `install [agent]` | clone 仓库 / 复制代码 → 创建 venv → 安装依赖 → 安装 WebUI |
| `uninstall [agent]` | 删除 agent 目录 + 删除 config 目录 |
| `update [agent]` | 更新代码 → 重装依赖 |
| `check [agent]` | 检查安装完整性 |

### 示例

```bash
# 安装所有 agent
install.sh install

# deer-flow: git clone + uv venv + uv pip install
install.sh install deer-flow

# nanobot: git clone + uv venv + pip install + webui npm install
install.sh install nanobot

# hermes-agent: git clone + uv venv + pip install + dashboard + webui npm install
install.sh install hermes-agent

# claude-code: 复制 src/server/*.py + webui/* 到 agents/claude-code/server/ + npm install
install.sh install claude-code

# 卸载
install.sh uninstall nanobot
install.sh uninstall                          # 卸载全部

# 更新
install.sh update nanobot                     # git pull + pip install + npm install
install.sh update claude-code                 # cp 覆盖源文件 + npm install

# 检查
install.sh check deer-flow                    # path / venv / python / packages / config
install.sh check claude-code                  # server/*.py / webui/dist / webui/node_modules
```

### 支持的 agent 列表

| Agent name | 安装方式 | Config Path | Config Files | Skills Path |
|---|------|---|---|------|
| deer-flow | git clone https://github.com/bytedance/deer-flow | ${agent_path}/ | config.yaml .env | ${agent_path}/skills/custom |
| nanobot | git clone https://github.com/HKUDS/nanobot | ~/.nanobot/ | config.json | ${agent_path}/nanobot/skills |
| hermes-agent | git clone https://github.com/nousresearch/hermes-agent | ~/.hermes/ | config.yaml .env | ${agent_path}/skills/custom |
| claude-code | cp src/server/*.py → ${agent_path}/server/ | ${agent_path}/.claude/ | settings.json .env | ${agent_path}/.claude/skills |

### WebUI 安装策略

| Agent | WebUI 位置 | 安装命令 | 启动方式 |
|-------|-----------|---------|----------|
| deer-flow | Next.js（集成在 make dev-daemon） | make install | make dev-daemon |
| nanobot | webui/ (Vite + React) | npm install | npm run dev |
| hermes-agent | web/ (Vite + React) | npm install | npm run dev |
| claude-code | server/webui/ (TypeScript + esbuild + serve) | npm install | npm run build && npx serve dist -l 5175 |

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
| hermes-agent | 仅 Gateway，跳过 Dashboard(9119)+WebUI(5174) |
| claude-code | 仅 HTTP Server(9000)，跳过 WebUI serve(5175) |

claude-code 的 `--no-webui` 通过 `CLAUDE_SERVER_NO_WEBUI=true` 环境变量传递给 Python 进程。

#### stop — 停止 agent

```
run.sh stop [agent]
```

- deer-flow：`make stop`（停止 Gateway + Frontend + Nginx）
- nanobot：pkill gateway + webui port
- hermes-agent：webui port → dashboard :9119 → `hermes gateway stop` → pkill -9
- claude-code：server :9000 + webui :5175

WebUI 端口由 `_webui_port()` 函数统一管理：

| Agent | WebUI Port |
|-------|:---:|
| nanobot | 5173 |
| hermes-agent | 5174 |
| claude-code | 5175 |

#### status — 查看运行状态

```
run.sh status [agent]
```

显示：运行状态 + 进程/PID/端口 + 默认模型 + skills 列表

```bash
# claude-code 示例输出
=== claude-code ===
  status:    RUNNING
  process:
    Server   pid 12345  port 9000
    WebUI    pid 12346  port 5175 (http://localhost:5175)
  model:     none
  skills:    chatlog-http-cli stock-analysis stock-data-fetch
```

#### clean — 清理运行时数据

```
run.sh clean [agent]
```

- 停止 agent（如果运行中）
- 删除配置文件 + 缓存目录 + 运行日志
- **home 型**（nanobot/hermes）：删除整 config 目录
- **agent 型**（deer-flow）：仅删除 config.yaml/.env，保留 agent 代码
- **claude-code**：删除 server/ + .claude/ 目录

#### sync — 同步 skills

```
run.sh sync <agent> [skills]
```

仅在 agent **未启动** 状态可执行。先清空目标目录，再复制 skill。

```bash
run.sh sync deer-flow skills/*
run.sh sync claude-code skills/stock-analysis,skills/stock-data-fetch

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

### 端口参考

| Agent | Gateway | WebUI | Dashboard | API Server |
|-------|---------|:---:|-----------|------------|
| deer-flow | 8001 | 3000 / 2026 (Nginx) | — | — |
| nanobot | 18790 | 5173 (Vite) | — | 8900 |
| hermes-agent | — | 5174 (Vite) | 9119 | 8642 |
| claude-code | — | 5175 (serve) | — | 9000 |

---

## Step3: 评测脚本 eval.sh

### 命令签名

```bash
eval.sh run  <config>            # 运行 YAML 配置中的所有 task
eval.sh run  <config> -t <name>  # 运行指定 task
eval.sh run  <config> -o <dir>   # 指定输出目录
eval.sh list <config>            # 列出配置中的 task
eval.sh -h|--help                # 帮助
```

### 配置文件格式（YAML）

```yaml
output_dir: results/
tasks:
  - name: math-smoke
    dataset: tests/eval/data/sample.jsonl
    agent: nanobot
    tags: [math]
    concurrency: 2
    grader: default                # default / none / 注册名 / pkg:fn
    trace: true                    # 开启 process trace 采集
```

### EvalTask 字段

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `name` | **必填** | task 名称 |
| `dataset` | **必填** | JSONL 路径 |
| `agent` | `"nanobot"` | agent 名称 |
| `model` | — | 模型 |
| `tags` | — | tag 过滤（OR） |
| `limit` | — | 截取条数 |
| `shuffle` | `false` | 随机打乱 |
| `concurrency` | `5` | 并发数 |
| `timeout` | `120` | 单条超时（秒） |
| `output` | — | 自定义输出路径 |
| `grader` | — | grader 名（default/none/注册名/pkg:fn） |
| `trace` | `false` | 开启 process trace 采集 |

### 示例

```bash
# 查看所有 task
bash scripts/eval.sh list tasks.yaml

# 运行全部
bash scripts/eval.sh run tasks.yaml

# 运行指定 task
bash scripts/eval.sh run tasks.yaml -t math-smoke -o ci_results/
```

内部通过 `PYTHONPATH="src" python -c "from eval.task import ..."` 调用 `load_tasks()` + `run_tasks()`。

### 输出结构

```
results/
├── math-smoke.jsonl          # AsyncEvalRunner.save()
├── math-smoke.report.txt     # 自动生成
├── geo-claude.jsonl
├── geo-claude.report.txt
└── summary.txt               # 跨 task 汇总报告
```
