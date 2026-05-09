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
)
```

## SSE 端点

| 端点 | trace 事件 type |
|------|------|
| `POST /sessions/{sid}/chat/stream` | `text`, `done`, `error` |
| `POST /sessions/{sid}/chat/trace` | `text`, `thinking`, `tool_use`, `tool_result`, `subagent`, `usage` |

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
POST /sessions/{sid}/chat         {"message": "...", "timeout": 300}
POST /sessions/{sid}/chat/stream  {"message": "...", "timeout": 300}
POST /sessions/{sid}/chat/trace   {"message": "...", "timeout": 300}
GET  /sessions/{sid}/history
GET  /skills
GET  /skills/{name}
```

- `/skills` 从 `_resolve_claude_home()/.claude/skills/` 读取
- WORK_DIR 默认为 `_resolve_claude_home()/run/`，自动创建
