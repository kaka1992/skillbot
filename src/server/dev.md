# Claude Code HTTP Server

## 文件结构

```
src/server/
├── app.py            # FastAPI 核心 API + skill 端点
├── session.py        # SDK Session + ClaudeSDKClient 生命周期
├── webui/            # TypeScript 前端（独立构建，esbuild + serve）
└── dev.md
```

## 架构

```
WebUI :5175 ──CORS──▶ :9000 FastAPI → SessionManager → ClaudeSDKClient
```

`--no-webui` 时仅启动 :9000，WebUI 独立通过 `npm run start` 启动。

## Session（session.py）

每个 `Session` 持有一个 `ClaudeSDKClient`，通过 `asyncio.Lock` 串行化请求。

| 方法 | 产出 |
|------|------|
| `send()` | 全文 `str` |
| `send_stream()` | `AsyncIterator[str]`，token 级增量 |
| `send_stream_chunks()` | `AsyncIterator[StreamChunk]`，text + trace blocks |

```python
ClaudeAgentOptions(
    allowed_tools=["Bash", "Read", ...],
    permission_mode="bypassPermissions",
    env={"HOME": str(claude_home)},
    setting_sources=["user"],
    max_turns=50,
    include_partial_messages=True,      # send_stream / send_stream_chunks 需要
)
```

## SSE 端点

| 端点 | trace 事件 type |
|------|------|
| `POST /sessions/{sid}/chat/stream` | `text`, `done`, `error` |
| `POST /sessions/{sid}/chat/trace` | 额外: `thinking`, `tool_use`, `tool_result`, `subagent`, `usage` |

Trace 事件来源：`StreamEvent`（text_delta）→ text；`AssistantMessage`（ThinkingBlock / ToolUseBlock / ToolResultBlock）→ thinking / tool_use / tool_result；`TaskStartedMessage` / `TaskProgressMessage` / `TaskNotificationMessage` → subagent；`ResultMessage` → usage。

## WebUI

TypeScript + esbuild 构建，`serve` 启动。构建和安装由 `install.sh` + `run.sh` 管理，详见 `scripts/dev.md`。

```bash
cd src/server/webui
npm install && npm run build && npm run start   # http://localhost:5175
```

## API

```
GET  /health
POST /sessions
GET  /sessions
GET  /sessions/{sid}
DELETE /sessions/{sid}
POST /sessions/{sid}/chat         {"message": "...", "timeout": 300}
POST /sessions/{sid}/chat/stream  {"message": "...", "timeout": 300}
POST /sessions/{sid}/chat/trace   {"message": "...", "timeout": 300}
GET  /sessions/{sid}/history
GET  /skills
GET  /skills/{name}
```

- CORS: `allow_origins=["*"]`
- `/skills` 从 `_resolve_claude_home()/.claude/skills/` 读取
