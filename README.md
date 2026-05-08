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
./scripts/run.sh start claude-code              # HTTP Server :9000

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
│   └── eval.sh       # 批量评测执行器（YAML 配置驱动）
├── src/
│   ├── chat/         # 统一 Python chat 客户端（同步 + 异步）
│   ├── eval/         # JSONL 驱动的 agent 评测框架
│   └── server/       # Claude Code HTTP 服务端（claude-agent-sdk + SSE）
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
| [hermes-agent](https://github.com/nousresearch/hermes-agent) | — | 5173 (Vite) | OpenAI REST :8642 | ✓ |
| [claude-code (SDK + SSE)](https://github.com/anthropics/claude-agent-sdk-python) | — | — | HTTP :9000 | ✓ |

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
```

### 批量执行

```yaml
# tasks.yaml
output_dir: results/
tasks:
  - name: math-smoke
    dataset: data/math.jsonl
    agent: nanobot
    grader: score                       # 使用注册的 grader（可选）
    concurrency: 2
```

```bash
bash scripts/eval.sh run tasks.yaml                           # 运行全部
bash scripts/eval.sh run tasks.yaml -t math-smoke -o results/ # 运行指定
bash scripts/eval.sh list tasks.yaml                          # 列出 task
```

输出：`<name>.jsonl` + `<name>.report.txt` + `summary.txt`。

## 配置

### conf/.env

```bash
DEEPSEEK_API_KEY=sk-xxx
SKILL_BOT_SKILL_PATH=skills/*           # skill 同步路径
SKILL_BOT_SKILL_DIR=/custom/skills      # 可选，覆盖默认源目录
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
PYTHONPATH="src" .venv/bin/pytest tests/chat/ -v
PYTHONPATH="src" .venv/bin/pytest tests/eval/ -v
PYTHONPATH="src" .venv/bin/pytest tests/server/ -v
```

## License

MIT
