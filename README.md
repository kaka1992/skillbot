# skillbot

多 agent 管理框架 — 统一管理 deer-flow、nanobot、hermes-agent、claude-code，提供一致的 CLI 运维工具和 Python chat API。

## 快速开始

```bash
# 安装所有 agent
./scripts/install.sh install

# 启动并配置模型
./scripts/run.sh start deer-flow deepseek-v4-flash
./scripts/run.sh start nanobot deepseek-v4-flash --no-webui
./scripts/run.sh start hermes-agent deepseek-v4-flash
./scripts/run.sh start claude-code              # HTTP Server :9000 + WebUI :5175
./scripts/run.sh start claude-code --no-webui    # 仅 API，跳过 WebUI

# 查看状态
./scripts/run.sh status

# 停止全部
./scripts/run.sh stop
```

## 架构

```
skillbot/
├── scripts/
│   ├── install.sh    # agent 安装 / 更新 / 卸载 / 检查
│   ├── run.sh        # agent 启动 / 停止 / 状态 / 清理 / skill 同步
│   ├── eval.sh       # 批量评测执行器（YAML 配置驱动）
│   └── jupyter.sh     # Jupyter 集成（%%agent cell magic）
├── src/
│   ├── agent/        # AgentSession + SubAgentSession + system prompt
│   ├── chat/         # 统一 Python chat 客户端（同步 + 异步）
│   ├── eval/         # JSONL 驱动的 agent 评测框架
│   ├── hook/         # Hook 系统 + subagent review
│   ├── jupyter/      # Jupyter 集成（%%agent/%%sql magic + telemetry + extension）
│   ├── task/         # Task + TaskManager（通用任务 + 依赖管理）
│   ├── server/       # Claude Code HTTP 服务端（claude-agent-sdk + SSE + subagent）
│   │   └── webui/     # TypeScript WebUI（esbuild + node proxy）
├── conf/
│   ├── .env          # 项目级环境配置（API key 等）
│   └── agent_conf/   # 各 agent 配置模板
├── agents/           # 已安装的 agent（gitignore）
├── skills/           # 共享 skill
└── tests/            # 测试套件
```

## 支持的 Agent

| Agent | Gateway | WebUI | REST API | Python Client |
|-------|:---:|:---:|:---:|:---:|
| [deer-flow](https://github.com/bytedance/deer-flow) | 8001 | 3000/2026 (Next.js+Nginx) | LangGraph SSE | ✓ |
| [nanobot](https://github.com/HKUDS/nanobot) | 18790 | 5173 (Vite) | OpenAI REST :8900 | ✓ |
| [hermes-agent](https://github.com/nousresearch/hermes-agent) | — | 5174 (Vite) | OpenAI REST :8642 | ✓ |
| [claude-code (SDK + SSE)](https://github.com/anthropics/claude-agent-sdk-python) | — | 5175 (node proxy) | HTTP :9000 | ✓ |

## CLI 命令

### install.sh

```bash
./scripts/install.sh install [agent]     # clone 仓库 + 创建 uv venv + 安装依赖
./scripts/install.sh update  [agent]     # git pull + 更新依赖
./scripts/install.sh uninstall [agent]   # 删除 agent 目录 + 配置文件
./scripts/install.sh check [agent]       # 检查安装完整性
```

### run.sh

```bash
./scripts/run.sh start  [agent] [model] [--no-webui]   # 启动 daemon
./scripts/run.sh stop   [agent]                          # 停止 agent
./scripts/run.sh status [agent]                          # 查看运行状态/端口/模型/skills
./scripts/run.sh clean  [agent]                          # 清理配置 + 缓存 + 日志
./scripts/run.sh sync   [agent] [skills]                 # 同步 skill 到 agent
```

### eval.sh

```bash
./scripts/eval.sh run  tasks.yaml              # 运行全部 task
./scripts/eval.sh run  tasks.yaml -t <name>    # 运行指定 task
./scripts/eval.sh run  tasks.yaml -o results/  # 指定输出目录
./scripts/eval.sh list tasks.yaml              # 列出 task
```

### jupyter.sh

```bash
./scripts/jupyter.sh                    # 启动 notebook (port 8888)
./scripts/jupyter.sh lab                # 启动 JupyterLab
./scripts/jupyter.sh notebook --port 9999
```

新建 notebook 选择 "skillbot (Python 3.12)" kernel，`%%agent` 自动可用。

**配置 agent：**

```
%agent_config --agent claude-code --timeout 600
%agent_config --config conf/jupyter_agent.yaml
%agent_config --claude-md conf/claude-md.example
%agent_config --debug
```

不调用 `%agent_config` 时默认使用 `claude-code`，切换 agent 自动重建 session。支持 `--config <yaml>` 加载配置、`--agent` 指定 agent、`--claude-md` 项目约束、`--debug` 日志、`--KEY=VALUE` 注入环境变量。

YAML 配置可加载第三方 tool 实现并设定实现偏好（`tools.paths` / `tools.preferences`）。

**用法：**

```
%%agent
1+1=?
# → 流式进度（工具调用）+ 解析后打印结果文本

%%agent --timeout 1200
complex multi-step analysis
# → 单次超时 1200s

%%agent
使用 stock_df 绘制收盘价走势
# → agent 可访问 stock_df 变量信息，生成的图表自动内联显示
```

| Flag | 效果 |
|------|------|
| `--timeout N` | 本次调用超时秒数（默认 600） |
| `--trace` | agent 执行后触发 review（AgentCellReviewHook），生成 review/fix cell |
| `--auto` | 自动执行生成的 cell（独立使用，也可配合 --trace） |

**Agent 输出（JSON 格式，支持裸 JSON 或 fenced block）：**

```json
{
  "text": "markdown 解释文本",
  "files": ["/tmp/chart.png", "/tmp/data.csv"],
  "code": "print('hello')"
}
```

| 字段 | 行为 |
|------|------|
| `text` | 自动检测 markdown→渲染，纯文本→print |
| `files[]` | `.csv` → DataFrame，`.png/.jpg/.svg` → 内联图片，`.py` → 追加到 code_list |
| `code` | 字符串或数组，始终注入下一 cell（数组每元素一个 cell） |

**变量上下文：** 每次 `%%agent` 调用自动收集 shell 中用户变量信息（DataFrame shape、list 长度等）和近期 cell 执行记录，注入 prompt 供 agent 参考。首次 `%%agent` 后只发送增量变更。

### Spark SQL Magic

`%%sql` cell magic 和 `%sql` line magic 提供 Spark SQL 查询能力，基于 Tool 框架的 spark preset，与具体实现解耦：

```
# 直接查询（analyze → submit → poll → result 流式进度）
%%sql --var df1 --timeout 600 --poll 30
select * from table

# 提交异步任务
%%sql submit
select * from table

# 任务管理（行魔法）
%sql status --job_id xxxx
%sql cancel --job_id xxxx
%sql result --job_id xxxx --limit 100
```

查询结果自动注入为 DataFrame 变量（默认 `var_1`、`var_2`...）。poll 阶段 `\r` + `flush` 实现单行实时刷新。

### 用户反馈 + 数据采集

`%fb yes|no [--comment '...']` 确认 agent 输出是否符合预期。Telemetry 自动采集 cell 执行、agent 调用、hook 事件、用户反馈到 `.run/sessions/{id}.jsonl`，用于改进 agent 准确性和 LLM 训练。

### Session + SubAgent

`AgentSession` 管理主 agent 生命周期。`SubAgentSession` 为 review hook 提供独立 session 和工具权限：

```python
from agent import AgentSession, SubAgentConfig

session = AgentSession("claude-code", timeout=600)
session.configure_subs({
    "cell_review": SubAgentConfig(name="cell_review", tools=["Read", "Bash"]),
})
session.init_session(system_prompt=..., session_key=...)

# Hook 中通过 session.get_sub("cell_review").execute(task) 执行 review
```

## Python API

```python
from chat import ChatClient

# 同步调用
c = ChatClient("nanobot", model="deepseek-v4-flash")
reply = c.chat("你好", session="s1")

# 流式输出
for chunk in c.stream("讲个笑话", session="s2"):
    print(chunk, end="")

# claude-code 流式（SSE，token 级别）
cc = ChatClient("claude-code", timeout=60)
for chunk in cc.stream("数 1 到 3", session="s3"):
    print(repr(chunk))   # → '1' '\n' '2' '\n' '3'

# stream_chunks — 结构化 trace 采集
from eval.trace import TraceCollector
collector = TraceCollector()
for chunk in cc.stream_chunks("执行python: print(123)", session="trace"):
    collector.feed(chunk)
    if chunk.text:
        print(chunk.text, end="")
trace = collector.to_dict()
# → {"thinking": [...], "tool_calls": [...], "usage": [...]}

# 异步 + 并发
import asyncio
c = ChatClient("nanobot")

async def main():
    reply = await c.async_chat("你好", session="s4")
    async for chunk in c.async_stream("数 1 到 3", session="s5"):
        print(chunk, end="")

asyncio.run(main())
```

### 会话隔离

| Agent | 隔离参数 | 实现机制 |
|-------|---------|---------|
| deer-flow | `session` → `thread_id` | LangGraph SQLite checkpointer |
| nanobot | `X-Nanobot-Session-ID` 请求头 | API session 持久化 |
| hermes-agent | `X-Hermes-Session-Id` 请求头 | state.db 持久化 |
| claude-code | `session` → server-side session | `ClaudeSDKClient` 持久连接 |

## Tool 框架

通用工具接口与注册机制，支持接口与实现分离、多实现共存、偏好路由、运行时依赖检查。

```python
from tools import ToolRegistry, ToolPreset, ToolResult, ToolRequirement, ReturnProperty, impl

# 定义接口（纯契约，零依赖）
PRESET = ToolPreset(
    name="my_tool",
    description="...",
    parameters={"type": "object", "properties": {...}},
    returns={"key": ReturnProperty(type="str", description="...")},
    group="my_group",
)

# 绑定默认实现（含运行时依赖）
@impl(PRESET, requires=[
    ToolRequirement(type="env", key="MY_ENV", description="API endpoint"),
    ToolRequirement(type="import", key="my_pkg", description="My package"),
])
async def my_tool(params: dict) -> ToolResult:
    return ToolResult(data={"key": "value"})

# 备选实现
@impl(PRESET, impl_name="v2")
async def my_tool_v2(params: dict) -> ToolResult: ...

# 偏好切换
ToolRegistry.set_preferred("my_tool", "v2")
tool = ToolRegistry.get("my_tool")  # → v2 实现

# 运行时检查
ToolRegistry.discover("path/to/tools/")   # 自动 check_requirements + 冲突检测
ToolRegistry.check_all()                  # → {tool_name: [errors]} 空=全部 OK
```

## 评测框架

```python
from eval import EvalDataset, AsyncEvalRunner
from chat import ChatClient

ds = EvalDataset("questions.jsonl", tags=["math"], limit=10)
c = ChatClient("nanobot")
runner = AsyncEvalRunner(
    lambda q: c.async_chat(q, session="eval"),
    concurrency=5,       # 默认使用 default_grader（子串匹配）
)

async for result in runner.run(ds):
    print(f"{result.id}: {'OK' if result.success else 'FAIL'}")

print(runner.report())
runner.save("results.jsonl")   # 同时写入 .jsonl 和 .report.txt
```

### 自定义 Grader

```python
from eval import GraderOutput, register_grader

# 定义 grader 并注册到 YAML 可用名
def score_grader(expected, answer, extra):
    ok = expected.strip().lower() in answer.strip().lower()
    return GraderOutput(success=ok, score=1.0 if ok else 0.0)

register_grader("score", score_grader)

# 通过 API 直接使用
runner = AsyncEvalRunner(chat_fn, grader=score_grader)
runner = AsyncEvalRunner(chat_fn, grader=None)   # 禁用评分
runner = AsyncEvalRunner(chat_fn, trace=True)    # trace 采集
```

### 批量执行

```yaml
# tasks.yaml
output_dir: results/
tasks:
  - name: math-smoke
    dataset: data/math.jsonl
    agent: nanobot
    grader: score                       # grader 名（default / none / 注册名 / pkg:fn）
    trace: true                         # 开启 process trace 采集
    concurrency: 2
```

```bash
bash scripts/eval.sh run tasks.yaml                           # 运行全部
bash scripts/eval.sh run tasks.yaml -t math-smoke -o results/ # 运行指定
bash scripts/eval.sh list tasks.yaml                          # 列出 task
```

输出：`<name>.jsonl` + `<name>.report.txt` + `summary.txt`。

### Trace 能力矩阵

| trace 数据 | deer-flow | nanobot | hermes-agent | claude-code |
|------|:---:|:---:|:---:|:---:|
| thinking / 推理过程 | — | — | — | ✓ |
| tool_use / tool_result | ✓ | — | ✓ | ✓ |
| subagent 生命周期 | — | — | — | ✓ |
| usage / token 用量 | — | — | ✓ | ✓ |

## 配置

### conf/.env

```bash
DEEPSEEK_API_KEY=sk-xxx
SKILL_BOT_SKILL_PATH=skills/*           # skill 同步路径
```

`install.sh` 和 `run.sh` 启动时自动加载。

### Agent 配置模板

```
conf/agent_conf/
├── deer-flow/config.yaml + .env
├── nanobot/config.json + .env
├── hermes-agent/config.yaml + .env
└── claude-code/settings.json + .env
```

`run.sh start` 第一次启动时自动同步到 agent 的配置目录。

## 开发

```bash
# 初始化环境
uv venv && uv pip install -e ".[dev]"

# 运行全部测试
PYTHONPATH="src" .venv/bin/pytest tests/ -v

# 按模块测试
PYTHONPATH="src" .venv/bin/pytest tests/tools/ -v   # 57 测试
PYTHONPATH="src" .venv/bin/pytest tests/chat/ -v    # 58 测试
PYTHONPATH="src" .venv/bin/pytest tests/eval/ -v    # 83 测试
PYTHONPATH="src" .venv/bin/pytest tests/jupyter/ -v # 120 测试
PYTHONPATH="src" .venv/bin/pytest tests/hook/ -v    # 14 测试
PYTHONPATH="src" .venv/bin/pytest tests/task/ -v    # 11 测试
PYTHONPATH="src" .venv/bin/pytest tests/server/ -v  # 27 测试
```

## License

MIT
