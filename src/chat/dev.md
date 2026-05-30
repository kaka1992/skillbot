# 通用 Python Chat API

## 设计目标

提供统一的 Python chat 客户端 `ChatClient`，封装 deer-flow / nanobot / hermes-agent / claude-code
四套 agent 的底层差异。对外暴露一致的接口，支持：

- 单次 / 流式对话
- 会话隔离（多轮对话上下文）
- 动态模型选择（可缺省）
- agent 自动启动（nanobot / hermes）

## Python API

```python
from chat import ChatClient

client = ChatClient(agent="deer-flow")

# 单次对话
reply = client.chat(content="你好，我叫张三", session="s1")

# 多轮对话（同一 session 保留上下文）
reply = client.chat(content="我叫什么名字？", session="s1")  # → "你叫张三"

# 流式对话
for chunk in client.stream(content="讲个笑话", session="s2"):
    print(chunk, end="")

# 会话管理
sessions = client.list_sessions()
client.clear_session("s1")
```

## 架构

```
ChatClient(agent, model, auto_start)
     │
     ├── agent == "deer-flow"
     │     → DeerFlowBackend (LangGraph REST)
     │     → POST :8001/api/threads/{id}/runs/stream  (SSE)
     │
     ├── agent == "nanobot"
     │     → NanobotBackend (OpenAI REST)
     │     → POST :8900/v1/chat/completions
     │
     └── agent == "hermes-agent"
           → HermesBackend (OpenAI REST)
           → POST :8642/v1/chat/completions

ChatClient("claude-code")
     │
     └── agent == "claude-code"
           → ClaudeBackend (HTTP Server)
           → POST :9000/sessions/{id}/chat
```

## 文件结构

```
src/chat/
├── __init__.py          # ChatClient 入口（chat / stream / stream_chunks / async 系列）
├── base.py              # AbstractBackend + TraceBlock + StreamChunk 数据模型
├── deerflow.py          # DeerFlowBackend（LangGraph SSE + messages-tuple + custom events）
├── nanobot.py           # NanobotBackend（OpenAI REST，stream_chunks 默认 wrap）
├── hermes.py            # HermesBackend（OpenAI SSE + hermes.tool.progress events）
├── claude.py            # ClaudeBackend（HTTP :9000 + trace SSE + interrupt 端点）
└── dev.md               # 设计文档
```

## 核心接口

### ChatClient

```
ChatClient(
    agent: str,                    # "deer-flow" | "nanobot" | "hermes-agent"
    model: str | None = None,      # 默认使用 agent 配置的模型
    auto_start: bool = True,       # nanobot/hermes 端口不可达时自动启动
)

chat(content: str, session: str, model: str | None = None) -> str
stream(content: str, session: str, model: str | None = None) -> Iterator[str]
interrupt(session: str) -> None
list_sessions() -> list[str]
clear_session(session: str) -> None
```

### AbstractBackend

```python
class AbstractBackend(ABC):
    @abstractmethod
    def chat(self, content: str, session: str, model: str | None) -> str: ...

    @abstractmethod
    def stream(self, content: str, session: str, model: str | None) -> Iterator[str]: ...

    def interrupt(self, session: str) -> None: ...

    @abstractmethod
    def list_sessions(self) -> list[str]: ...

    @abstractmethod
    def clear_session(self, session: str) -> None: ...
```

## 会话隔离机制

| Agent | 隔离参数 | 传输方式 | 持久化 |
|-------|---------|---------|--------|
| deer-flow | `thread_id` | POST body 参数 | SQLite `.deer-flow/data/` |
| nanobot | `X-Nanobot-Session-ID` | HTTP Header | `~/.nanobot/sessions/` |
| hermes | `X-Hermes-Session-Id` | HTTP Header | `state.db` (opt-in) |
| claude-code | `session` → server-side session | HTTP body | 内存（SessionManager） |

- **deer-flow**: 不同 `session` → 不同 `thread_id`，`DeerFlowClient` 单例复用
- **nanobot**: 不带 header → 共享 `api:default`；带 header → 独立 session
- **hermes**: 不带 header → 无状态；带 header → 启用沙箱复用 + 对话历史

## 底层调用映射

### deer-flow — LangGraph REST API

deer-flow 通过 Gateway 端口 8001 暴露 LangGraph-compatible REST API。
认证采用 JWT Cookie + CSRF Token 双校验，session 映射为 LangGraph `thread_id`。

```python
import requests

DEER_BASE = "http://127.0.0.1:8001/api"

class DeerFlowBackend(AbstractBackend):
    def __init__(self, model=None, auto_start=True):
        self._threads: dict[str, str] = {}  # session → thread_id
        self._session = requests.Session()
        if auto_start:
            self._ensure_running()
        self._auth_init()

    def _auth_init(self):
        r = self._session.get(f"{DEER_BASE}/v1/auth/setup-status")
        if r.json().get("needs_setup"):
            self._session.post(f"{DEER_BASE}/v1/auth/initialize", json={
                "email": "admin@skillbot.com", "password": "skillbot123"})
        self._session.post(f"{DEER_BASE}/v1/auth/login/local",
            data={"username": "admin@skillbot.com", "password": "skillbot123"})
        self._csrf = self._session.cookies.get("csrf_token", "")

    @staticmethod
    def _build_config(model):
        """Only include model_name when explicitly set."""
        cfg = {}
        if model:
            cfg["model_name"] = model
        return cfg

    def _get_thread(self, session):
        if session not in self._threads:
            r = self._session.post(f"{DEER_BASE}/threads", json={},
                headers={"X-CSRF-Token": self._csrf})
            self._threads[session] = r.json()["thread_id"]
        return self._threads[session]

    def chat(self, content, session, model=None):
        tid = self._get_thread(session)
        r = self._session.post(f"{DEER_BASE}/threads/{tid}/runs/wait", json={
            "input": {"messages": [{"role": "user", "content": content}]},
            "config": {"configurable": self._build_config(model)},
        }, headers={"X-CSRF-Token": self._csrf})
        data = r.json()
        messages = data.get("messages") or data.get("values", {}).get("messages", [])
        return messages[-1]["content"] if messages else ""

    def stream(self, content, session, model=None):
        tid = self._get_thread(session)
        r = self._session.post(f"{DEER_BASE}/threads/{tid}/runs/stream", json={
            "input": {"messages": [{"role": "user", "content": content}]},
            "config": {"configurable": self._build_config(model)},
            "stream_mode": ["messages-tuple"],
        }, headers={"X-CSRF-Token": self._csrf}, stream=True)
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            if line == "data: [DONE]":
                break
            try:
                chunk = json.loads(line[6:])
                if isinstance(chunk, list):
                    for item in chunk:
                        if isinstance(item, dict) and item.get("type") == "AIMessageChunk":
                            if text := item.get("content", ""):
                                yield text
            except json.JSONDecodeError:
                continue
```

### nanobot — OpenAI REST API

```python
import json, urllib.request

class NanobotBackend(AbstractBackend):
    BASE = "http://127.0.0.1:8900/v1"

    @staticmethod
    def _build_body(model, content, stream=False):
        body = {"messages": [{"role": "user", "content": content}]}
        if model:
            body["model"] = model
        if stream:
            body["stream"] = True
        return body

    def chat(self, content, session, model=None):
        body = json.dumps(self._build_body(model, content)).encode()
        req = urllib.request.Request(f"{self.BASE}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json",
                     "X-Nanobot-Session-ID": session})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]

    def stream(self, content, session, model=None):
        body = json.dumps(self._build_body(model, content, stream=True)).encode()
        req = urllib.request.Request(f"{self.BASE}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json",
                     "X-Nanobot-Session-ID": session})
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                delta = json.loads(line[6:])["choices"][0]["delta"]
                if "content" in delta:
                    yield delta["content"]
```

### hermes — OpenAI REST API

API key 从 `conf/agent_conf/hermes-agent/.env` 自动加载。需同时设置
`Authorization: Bearer <key>` 和 `X-Hermes-Session-Id` 实现会话隔离。

```python
HERMES_API_KEY = _load_from_env()  # reads API_SERVER_KEY from .env

class HermesBackend(AbstractBackend):
    BASE = "http://localhost:8642/v1"

    @staticmethod
    def _build_body(model, content, stream=False):
        body = {"messages": [{"role": "user", "content": content}]}
        if model:
            body["model"] = model
        if stream:
            body["stream"] = True
        return body

    @staticmethod
    def _headers(session):
        return {
            "Authorization": f"Bearer {HERMES_API_KEY}",
            "X-Hermes-Session-Id": session,
        }

    def chat(self, content, session, model=None):
        resp = requests.post(f"{self.BASE}/chat/completions",
            json=self._build_body(model, content),
            headers=self._headers(session))
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
```

## Agent 自动启动策略

```python
def _ensure_agent_running(self) -> None:
    ports = {"deer-flow": 8001, "nanobot": 8900, "hermes-agent": 8642}
    port = ports[self._agent]
    if self._is_port_ready(port):
        return
    subprocess.run(
        ["bash", "scripts/run.sh", "start", self._agent, "--no-webui"],
        cwd=PROJECT_DIR, check=True
    )
    self._wait_port(port, timeout=30)
```

## 兼容性矩阵

| 特性 | deer-flow | nanobot | hermes-agent | claude-code |
|------|:---:|:---:|:---:|:---:|
| 单次对话 | ✓ | ✓ | ✓ | ✓ |
| 多轮对话（会话隔离） | ✓ | ✓ | ✓ | ✓ |
| 流式输出 | ✓ | ✓ | ✓ | ✓（SSE token 级别） |
| stream_chunks（结构化 trace） | ✓ | ✓ | ✓ | ✓ |
| trace: thinking | — | — | — | ✓ |
| trace: tool_use / tool_result | ✓（messages-tuple） | —（API 未暴露） | ✓（hermes.tool.progress） | ✓ |
| trace: subagent | — | — | — | ✓ |
| trace: usage | — | — | ✓ | ✓ |
| 动态选模型 | ✓ | ✓ | ✓ | — (settings.json) |
| 缺省模型 | ✓ | ✓ | ✓ | — |
| 无需预启动 HTTP | — | — | — | ✓ (server 内嵌) |
| 自动补启 agent | ✓ | ✓ | ✓ | ✓ |

## 模型默认值

| Agent | 不填 `model` 时 | 来源 |
|-------|------|------|
| deer-flow | agent 配置的第一个模型 | `config.yaml` 中 `models[0]`，不传 model 时不注入字段 |
| nanobot | gateway 启动时加载的模型 | `config.json` 的 `agents.defaults.model` |
| hermes-agent | `config.yaml` 的 `model` 字段 | `~/.hermes/config.yaml` |
| claude-code | `.claude/settings.json` 的 `ANTHROPIC_MODEL` | `agents/claude-code/.claude/settings.json` |

## 【example】

```python
from chat import ChatClient

# deer-flow — LangGraph REST API，多轮对话
c = ChatClient("deer-flow", model="deepseek-v4-flash")
c.chat("我叫张三", session="s1")
print(c.chat("我叫什么？", session="s1"))         # → "你叫张三"

# nanobot — REST API，流式
c = ChatClient("nanobot")
for chunk in c.stream(content="1+1=?", session="math"):
    print(chunk, end="")

# hermes — REST API，会话持久化
c = ChatClient("hermes-agent", model="deepseek-v4-flash")
c.chat("我叫李四", session="who")
print(c.chat("我是谁？", session="who"))           # → "你是李四"

# claude-code — HTTP Server，单轮对话
c = ChatClient("claude-code", timeout=300)
print(c.chat("1+1=?", session="cc"))              # → "2"

# stream_chunks — 结构化 trace 采集
from chat.base import StreamChunk
from eval.trace import TraceCollector

collector = TraceCollector()
for chunk in c.stream_chunks("执行python: print(123)", session="trace"):
    collector.feed(chunk)
    if chunk.text:
        print(chunk.text, end="")
# trace = collector.to_dict()  → {"thinking": [...], "tool_calls": [...], ...}

# 会话管理
print(c.list_sessions())    # → ["who"]
c.clear_session("who")
```

## 测试

### 测试文件结构

```
tests/chat/
├── test_base.py         # 异常类型 + TraceBlock/StreamChunk 数据模型 + ChatClient API
├── test_async.py        # 异步 chat/stream 测试（nanobot + hermes + deer-flow）
├── test_claude.py       # ClaudeBackend 测试（需 claude :9000 可达）
├── test_deerflow.py     # DeerFlowBackend 测试（需 deer-flow :8001 可达）
├── test_nanobot.py      # NanobotBackend 测试（需 nanobot :8900 可达）
├── test_hermes.py       # HermesBackend 测试（需 hermes :8642 可达）
└── conftest.py          # 共享 fixtures（端口检测 + skip 逻辑）
```

### 测试覆盖矩阵

| 测试场景 | deer-flow | nanobot | hermes-agent | claude-code |
|---------|:---:|:---:|:---:|:---:|
| 单次对话返回非空文本 | ✓ | ✓ | ✓ | ✓ |
| 流式对话逐 token 输出 | ✓ | ✓ | ✓ | ✓ |
| 多轮对话上下文保持 | ✓ | ✓ | ✓ | ✓ |
| 不同 session 完全隔离 | ✓ | ✓ | ✓ | ✓ |
| stream_chunks 返回 StreamChunk | ✓ | ✓ | ✓ | ✓ |
| stream_chunks 文本验证 | ✓ | ✓ | ✓ | ✓ |
| trace: tool_use / tool_result | ✓ | skip | ✓ | ✓ |
| trace: usage | — | — | ✓ | ✓ |
| 不填 model 使用默认值 | ✓ | ✓ | ✓ | ✓ |
| 动态切换 model | ✓ | ✓ | ✓ | ✓ |
| list_sessions 追踪 | ✓ | ✓ | ✓ | ✓ |
| clear_session 清除 | ✓ | ✓ | ✓ | ✓ |
| unknown agent 报错 | — | — | — | — |
| 端口不可达抛异常 | — | ✓ | ✓ | ✓ |
| 端口自动检测通过 | — | ✓ | ✓ | ✓ |

### 运行测试

```bash
# 全部测试（需对应 agent 端口可达）
cd $PROJECT_DIR
PYTHONPATH="src" .venv/bin/pytest tests/chat/ -v

# 只跑某一组
PYTHONPATH="src" .venv/bin/pytest tests/chat/test_nanobot.py -v
PYTHONPATH="src" .venv/bin/pytest tests/chat/test_hermes.py -v
PYTHONPATH="src" .venv/bin/pytest tests/chat/test_deerflow.py -v
```

### 测试标记

```python
# pytest marker 用于条件跳过
@pytest.mark.deerflow      # 需要 deer-flow venv + DEEPSEEK_API_KEY
@pytest.mark.nanobot        # 需要 nanobot :8900 可达
@pytest.mark.hermes         # 需要 hermes :8642 可达
@pytest.mark.integration    # 需要 agent 实际运行
```

### 示例：会话隔离测试

```python
import pytest

def test_session_isolation(client):
    """不同 session 之间完全隔离，互不可见上下文。"""
    client.chat("我叫张三", session="a")
    client.chat("我叫李四", session="b")

    r_a = client.chat("我叫什么？", session="a")
    r_b = client.chat("我叫什么？", session="b")

    assert "张三" in r_a
    assert "李四" in r_b
    assert "张三" not in r_b, "session b 不应看到 session a 的内容"

def test_clear_session(client):
    """清除 session 后上下文丢失。"""
    client.chat("我叫王五", session="x")
    client.clear_session("x")
    r = client.chat("我叫什么？", session="x")
    assert "王五" not in r or "不知道" in r.lower()
```

### 示例：conftest.py fixture

```python
import pytest
import os
import subprocess
import sys

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

@pytest.fixture
def deerflow_client():
    """Skip if deer-flow Gateway :8001 not reachable."""
    s = socket.socket()
    try:
        s.settimeout(1)
        s.connect(("127.0.0.1", 8001))
    except Exception:
        pytest.skip("deer-flow :8001 not reachable")
    finally:
        s.close()
    sys.path.insert(0, os.path.join(PROJECT_DIR, "src"))
    from chat import ChatClient
    return ChatClient("deer-flow", model="deepseek-v4-flash")

@pytest.fixture
def nanobot_client():
    """Skip if nanobot :8900 not reachable."""
    import socket
    s = socket.socket()
    try:
        s.settimeout(1)
        s.connect(("localhost", 8900))
    except Exception:
        pytest.skip("nanobot :8900 not reachable")
    finally:
        s.close()
    sys.path.insert(0, os.path.join(PROJECT_DIR, "src"))
    from chat import ChatClient
    return ChatClient("nanobot")

@pytest.fixture
def hermes_client():
    """Skip if hermes :8642 not reachable."""
    import socket
    s = socket.socket()
    try:
        s.settimeout(1)
        s.connect(("localhost", 8642))
    except Exception:
        pytest.skip("hermes :8642 not reachable")
    finally:
        s.close()
    sys.path.insert(0, os.path.join(PROJECT_DIR, "src"))
    from chat import ChatClient
    return ChatClient("hermes-agent")
```

## 【troubleshooting】

- agent 未安装 → `AgentNotInstalledError`，提示 `install.sh install <agent>`
- 端口 30s 未就绪 → `AgentStartupTimeout`，提示检查 `run.sh status <agent>`
- 模型不存在 → 使用默认模型 + 打印 warning
- deer-flow checkpointer 不存在 → 自动创建 SQLite `backend/.deer-flow/data/deerflow.db`
