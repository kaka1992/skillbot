# Claude Code HTTP Server

## 文件结构

```
src/server/
├── app.py            # FastAPI 核心 API + skill 端点
├── session.py        # SDK Session + ClaudeSDKClient 生命周期
├── webui/            # TypeScript 前端（esbuild 构建 + node 代理）
│   ├── server.js     # 静态文件 + API 反向代理（端口 5175）
│   ├── package.json
│   ├── tsconfig.json
│   ├── index.html
│   └── src/          # *.ts 源文件
└── dev.md
```

## 架构

```
Browser :5175 → server.js (proxy) → :9000 FastAPI → SessionManager → ClaudeSDKClient
```

`server.js` 将 `/sessions*`、`/skills*`、`/health` 代理到 `:9000`，其他请求返回 `dist/` 静态文件。同源部署，无需 CORS。`--no-webui` 时仅启动 :9000。

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
    include_partial_messages=True,
    agents={
        "general-purpose": AgentDefinition(
            description="General-purpose agent for complex multi-step tasks",
            tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        ),
        "coding": AgentDefinition(
            description="Coding specialist for writing and refactoring code",
            tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        ),
        "code-reviewer": AgentDefinition(
            description="Reviews code for bugs, style, and security issues",
            tools=["Read", "Grep", "Glob"],
        ),
    },
)
```

### Subagent

主 agent 通过 `Task` 工具 spawn 子 agent，`MAX_CONCURRENT_SUBAGENTS = 3`。子 agent 生命周期事件通过 trace 端点暴露：

| 事件 | 消息类型 | 字段 |
|------|------|------|
| 启动 | `TaskStartedMessage` | `task_id`, `agent_type`, `description` |
| 进度 | `TaskProgressMessage` | `task_id`, `usage`, `last_tool_name` |
| 完成 | `TaskNotificationMessage` | `task_id`, `status`, `summary` |

## SSE 端点

| 端点 | trace 事件 type |
|------|------|
| `POST /sessions/{sid}/chat/stream` | `text`, `done`, `error` |
| `POST /sessions/{sid}/chat/trace` | `text`, `thinking`, `tool_use`, `tool_result`, `subagent`, `usage` |
| `POST /sessions/{sid}/chat/stream` | `text`, `done`, `error` |

### Trace 事件来源

| type | 来源 |
|------|------|
| `text` | `StreamEvent.content_block_delta.text_delta` |
| `thinking` | `ThinkingBlock` / `content_block_delta.thinking_delta` |
| `tool_use` | `ToolUseBlock`（id, name, input） |
| `tool_result` | `ToolResultBlock`（tool_use_id, content, is_error） |
| `subagent` | `TaskStartedMessage` / `TaskProgressMessage` / `TaskNotificationMessage` |
| `usage` | `ResultMessage`（total_cost_usd, num_turns, usage） |

## WebUI

TypeScript + esbuild 构建，`server.js`（Node.js 无依赖代理）启动。

```bash
cd src/server/webui
npm install
npm run build   # esbuild → dist/
npm run start   # node server.js → http://localhost:5175
```

`server.js` 将 API 请求代理到 `:9000`，避免 CORS 问题。

## API

```
GET  /health
POST /sessions
GET  /sessions
GET  /sessions/{sid}
DELETE /sessions/{sid}
POST /sessions/{sid}/chat         {"message": "...", "timeout": 600}
POST /sessions/{sid}/chat/stream  {"message": "...", "timeout": 600}
POST /sessions/{sid}/chat/trace   {"message": "...", "timeout": 600}
POST /sessions/{sid}/interrupt      # 中断当前查询，保留上下文
GET  /sessions/{sid}/history
GET  /skills
GET  /skills/{name}
```

- `/skills` 从 `_resolve_claude_home()/.claude/skills/` 读取
- WORK_DIR 默认为 `_resolve_claude_home()/run/`，自动创建

## 中断机制

`POST /sessions/{sid}/interrupt` 调用 `Session.interrupt()` → `ClaudeSDKClient.interrupt()`。
SDK 向 subprocess 发送中断信号，停止当前查询。

中断后 subprocess 可能留下未完成的 `tool_use` 状态。`send_stream_chunks` 在下次查询前调用
`_apply_tool_fix()` 补全对话：

- **有 tool_use ID**：发送合成 `tool_result`（`is_error=True`）→ SDK 补全 tool_use → tool_result 周期 → 上下文保留
- **无 tool_use ID**：`disconnect + _client = None` → 下次查询创建新 client → 上下文丢失但可靠

`_send_inner_chunks` 的 `asyncio.CancelledError`（TCP 断开）时调用 `gen.aclose()` 确保
SDK client 状态清理干净，允许后续查询复用同一 client。
