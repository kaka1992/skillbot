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

# deer-flow: git clone + uv venv + uv uv pip install
install.sh install deer-flow

# nanobot: git clone + uv venv + uv pip install + webui npm install
install.sh install nanobot

# hermes-agent: git clone + uv venv + uv pip install + dashboard + webui npm install
install.sh install hermes-agent

# claude-code: 复制 src/server/*.py + webui/*（含 server.js） 到 agents/claude-code/server/ + npm install
install.sh install claude-code

# 卸载
install.sh uninstall nanobot
install.sh uninstall                          # 卸载全部

# 更新
install.sh update nanobot                     # git pull + uv pip install + npm install
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
| claude-code | cp src/server/*.py → ${agent_path}/server/ | ${agent_path}/.claude/ | settings.json .env | ${agent_path}/.claude/skills（内置 subagent: general-purpose, coding, code-reviewer） |

### WebUI 安装策略

| Agent | WebUI 位置 | 安装命令 | 启动方式 |
|-------|-----------|---------|----------|
| deer-flow | Next.js（集成在 make dev-daemon） | make install | make dev-daemon |
| nanobot | webui/ (Vite + React) | npm install | npm run dev |
| hermes-agent | web/ (Vite + React) | npm install | npm run dev |
| claude-code | server/webui/ (TypeScript + esbuild + node proxy) | npm install | npm run build && node server.js |

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
| claude-code | 仅 HTTP Server(9000)，跳过 WebUI 代理(5175) |

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
| claude-code | — | 5175 (node proxy) | — | 9000 |

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

内部通过 `PYTHONPATH="src" python -c "from eval.evaltask import ..."` 调用 `load_tasks()` + `run_tasks()`。

### 输出结构

```
results/
├── math-smoke.jsonl          # AsyncEvalRunner.save()
├── math-smoke.report.txt     # 自动生成
├── geo-claude.jsonl
├── geo-claude.report.txt
└── summary.txt               # 跨 task 汇总报告
```

---

## Step4: Jupyter 集成 jupyter.sh

### 命令签名

```bash
jupyter.sh [lab|notebook] [options]
jupyter.sh --rebuild              # 仅重建前端扩展（不改 Python 时）
```

### 功能

启动 Jupyter 并自动注册 `%agent_config` + `%%sql` magic + Agent Panel。脚本执行：
1. 安装依赖（ipython + jupyter + notebook + jupyterlab + pandas + ipykernel）
2. 注册 "skillbot (Python 3.12)" kernel（使用 .venv Python + 自动加载 jupyter extension）
3. 创建 IPython profile + 启动脚本
4. 构建前端扩展（Shadow DOM panel + SQL 高亮）
5. 启动 Jupyter（工作目录：`.jupyter/run/`）

### Agent Panel（右侧面板）

所有 agent 交互通过右侧 "Agent" panel 进行，替代了原有的 `%%agent` cell magic。
Panel 使用 Shadow DOM 完全隔离 JupyterLab CSS。

**模式系统（Shift+Tab 循环）：**

| 模式 | 标记 | 行为 |
|------|:---:|------|
| default | ❯ | cell 注入，手动执行 |
| plan | ⏸ | 先调研出方案 → plan 确认 UI（3 选项 + 反馈修订）→ 确认后执行 |
| auto | ⏵⏵ | cell 注入 + 自动执行 + 错误自动修复（最多 3 次） |

**输入框快捷键（对齐 cc-haha）：**

| 类别 | 快捷键 | 功能 |
|------|--------|------|
| 光标 | Ctrl+A/E, Ctrl+B/F, Alt+B/F | 行首/尾、字符、单词跳转 |
| 编辑 | Ctrl+H/D/K/U/W/Y | 退格、删除、剪切、粘贴（kill ring） |
| 历史 | ↑↓（首/末行）、Ctrl+P/N | 历史导航（保存草稿） |
| 提交 | Enter / Shift+Enter | 发送 / 换行 |
| 面板 | Ctrl+L | 清空面板 |

**计划确认 UI：**
- 计划预览（可滚动，深色背景 + 青色边框）
- 3 选项：Yes (审查后执行) / Yes (自动执行) / No (修订)
- No 选项支持反馈文本域输入修订意见

**自动错误修复（auto 模式）：**
- cell 执行失败 → AI 分析错误 → 生成修复代码 → 替换原 cell → 自动执行
- 最多重试 3 次，递归保护

### 配置 agent

```
%agent_config --agent claude-code --timeout 600
%agent_config --config conf/jupyter_agent.yaml
%agent_config --claude-md conf/claude-md.example
%agent_config --debug
```

不调用 `%agent_config` 时默认使用 `claude-code`。切换 agent 自动重建 session。

### 流式输出

文本逐 token 显示在 panel 中，tool 调用实时展示 `⬢ [Bash]`，thinking 摘要灰色斜体显示。

### 变量上下文

每次调用自动读取 shell namespace 中的用户变量（DataFrame/list/dict/str），注入 prompt 末尾。首次调用全量，后续增量（仅新变量 + 新 cell）。

### 单元追踪

通过 `post_run_cell` hook 自动记录所有 cell 执行（含普通 cell），为 agent 提供完整的执行历史上下文。

### 会话关联

同一个 `.ipynb` 文件共享同一个 agent session（session key = MD5(notebook_path)）。Kernel 重启时自动重建。

### 输出格式

| Block | 行为 |
|------|------|
| 纯文本 | streaming 逐 token 输出到 panel |
| `python` | 注入下一 cell（auto 模式自动执行） |
| `csv:name` / `file:name.csv` | → DataFrame |
| `image` | 内联渲染 |
| `file:name` | → 字符串变量 |

### 日志

每次调用记录到 `.run/jupyter.log` + `.run/claude-code.log`。
