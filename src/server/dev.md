# Claude Code HTTP Server — claude-agent-sdk 实现

## 架构

```
HTTP → FastAPI → SessionManager → ClaudeSDKClient → claude CLI 子进程
```

`session.py` 使用 `claude-agent-sdk`（Python 包）替代了原来的 `subprocess claude -p` 调用：

- **前**: 每次请求 spawn 新 `claude -p` 进程，通过 prompt 注入实现多轮
- **后**: `ClaudeSDKClient` 持久连接，SDK 原生支持多轮对话

## 核心实现

### Session（session.py）

每个 `Session` 持有一个 `ClaudeSDKClient` 实例：

| 方法 | 用途 | 说明 |
|------|------|------|
| `send()` | 非流式对话 | 首条用 `connect()`，后续用 `query()`，`receive_response()` 累积全文 |
| `send_stream()` | SSE 流式对话 | 设置 `include_partial_messages=True`，`receive_response()` 逐 chunk yield |
| `close()` | 清理 | `client.disconnect()` 关闭子进程 |

**`send()`** — 返回完整文本：

1. `client.connect(prompt=message)` 或 `client.query(message)`
2. `receive_response()` 遍历 `AssistantMessage` → 提取 `TextBlock.text` → 拼接返回
3. `asyncio.wait_for(coro, timeout)` 整体超时

**`send_stream()`** — 渐进 yield 文本增量：

1. 同上建立/复用连接，设置 `include_partial_messages=True`
2. `receive_response()` 遍历 `StreamEvent` → 解析 `event.content_block_delta.text_delta`
3. 逐 chunk yield，每个 chunk 独立超时（`asyncio.wait_for(gen.__anext__(), timeout)`）
4. 流结束后将完整文本记录到 history

`send()` 和 `send_stream()` 的 lock 都由调用方（app.py）持有。

### ClaudeAgentOptions

```python
ClaudeAgentOptions(
    allowed_tools=["Bash", "Read", ...],
    permission_mode="bypassPermissions",     # 替换 --dangerously-skip-permissions
    cwd="/working/dir",
    env={"HOME": "/path/to/claude-home"},     # 隔离 claude 配置
    setting_sources=["user"],                 # 仅加载 isolated HOME 的用户配置
    max_turns=50,
    include_partial_messages=True,            # 仅 send_stream() 启用
)
```

### SessionManager

内存管理 session 生命周期，`delete()` 异步清理 SDK client。

## 流式输出（SSE）

`POST /sessions/{sid}/chat/stream` 返回 `text/event-stream`，token 级别渐进输出。

### SSE 事件格式

| 事件 | 格式 | 说明 |
|------|------|------|
| 文本增量 | `data: {"text": "..."}\n\n` | 每个 token/文本块 |
| 完成 | `data: {"type": "done"}\n\n` | 流正常结束 |
| 错误 | `data: {"type": "error", "error": "..."}\n\n` | 超时或 SDK 错误 |

### 流式调用链

```
HTTP SSE → app.py chat_stream() → session.send_stream() → _send_inner_stream()
          → client.receive_response() → StreamEvent → content_block_delta.text_delta
```

`send_stream()` 的 lock 贯穿整个流生命周期，流结束后释放。`receive_response()` 在遇到 `ResultMessage` 时自动终止。

### 客户端消费

```python
from chat import ChatClient
c = ChatClient("claude-code")
for chunk in c.stream("讲个笑话", session="s1"):
    print(chunk, end="")
# → "1"\n"2"\n"3"  (逐 token 输出)
```

底层 `ClaudeBackend.stream()` 通过 `requests.post(stream=True)` + `iter_lines()` 解析 SSE。

## SDK vs CLI 对比

| | CLI (`subprocess`) | SDK (`claude-agent-sdk`) |
|---|---|---|
| 启动延迟 | ~3-5s（冷启动进程） | 进程内复用 |
| 多轮对话 | prompt 注入历史 | SDK 原生 session |
| 流式输出 | 不支持 | SSE（token 级别） |
| 权限控制 | `--dangerously-skip-permissions` | `permission_mode="bypassPermissions"` |
| 配置隔离 | `HOME` env var | `env={"HOME": ...}` |

## API

```
GET  /health
POST /sessions
GET  /sessions
GET  /sessions/{sid}
DELETE /sessions/{sid}
POST /sessions/{sid}/chat         {"message": "...", "timeout": 300, "allowed_tools": "..."}
POST /sessions/{sid}/chat/stream  {"message": "...", "timeout": 300, "allowed_tools": "..."}
GET  /sessions/{sid}/history
```
