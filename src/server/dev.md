# Claude Code HTTP Server

## 设计目标

通过 HTTP 接口包装 `claude -p` CLI，提供多 session 的对话服务。每个 session 维护独立的对话历史，Claude Code 运行在与 `~/.claude/` 隔离的独立 home 目录中。

## 架构

```
HTTP Client (curl / ChatClient / WebUI)
       │
       ▼
  FastAPI (port 9000)
       │
       ├── SessionManager ── dict[session_id → Session]
       │     ├── 创建 / 销毁 session
       │     ├── 对话历史追踪（仅客户端侧，Claude 不持久化）
       │     └── asyncio.Lock（单 session 内串行）
       │
       └── run_claude() ── subprocess claude -p --dangerously-skip-permissions
              │
              ├── env: HOME = agents/claude-code/（隔离目录）
              └── settings.json 从 conf/agent_conf/claude-code/ 加载
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/sessions` | 创建会话 → `{"session_id": "uuid12"}` |
| GET | `/sessions` | 列出所有会话 |
| GET | `/sessions/{id}` | 获取会话详情 |
| DELETE | `/sessions/{id}` | 删除会话 |
| POST | `/sessions/{id}/chat` | 发送消息 → `claude -p` |
| GET | `/sessions/{id}/history` | 获取对话历史 |

### Chat 请求

```json
{
  "message": "hello",
  "timeout": 300,
  "allowed_tools": "Read,Write"
}
```

### Chat 响应

```json
{
  "session_id": "abc123",
  "reply": "Hi there!",
  "elapsed": 3.5
}
```

## 文件结构

```
src/server/
├── __init__.py
├── app.py           # FastAPI app + 路由
├── session.py       # SessionManager + run_claude()
└── dev.md           # 本文件
```

## Session 管理

- `Session` 维护 `claude_sid`（未使用，Claude v2.x `-p` 模式不支持 `--resume`）、`history: list[Message]`、`lock: asyncio.Lock`
- 多轮对话通过将历史作为 prompt 上下文注入，而非 Claude 原生 session 持久化
- session 存储在内存中，服务重启后丢失

## 并发模型

```
同一 session:  asyncio.Lock 串行
不同 session:  独立 claude 子进程，并发执行（受 Semaphore 限流）
```

## Claude Home 隔离

Claude Code 的 home 目录由 `_resolve_claude_home()` 解析：

1. `SKILL_BOT_AGENT_INSTALL_DIR/claude-code`（如果设置）
2. 否则 `PROJECT_DIR/agents/claude-code/`

通过 `HOME` 环境变量注入子进程，与 `~/.claude/` 完全隔离。每次启动自动验证 `.claude/settings.json` 存在。

## 自动审批

`claude -p` 默认需要用户审批工具调用。Server 模式通过 `--dangerously-skip-permissions` 跳过所有权限检查，使 Claude 全自动执行。

## 配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `CLAUDE_SERVER_HOST` | 127.0.0.1 | 绑定地址 |
| `CLAUDE_SERVER_PORT` | 9000 | 监听端口 |
| `CLAUDE_SERVER_TIMEOUT` | 300 | Claude 调用超时（秒） |
| `CLAUDE_SERVER_ALLOWED_TOOLS` | (空=全部) | 工具白名单 |
| `CLAUDE_SERVER_WORK_DIR` | . | Claude 工作目录 |

## 启动

```bash
# 直接启动
PYTHONPATH="src" .venv/bin/python3 -c "from server.app import main; main()"

# 通过 run.sh
run.sh start claude-code
```

## 限制

- Claude Code v2.x `-p` 不支持 `--resume`，多轮上下文通过 prompt 注入
- 无 SSE 流式输出（`-p` 只支持全文返回）
- session 存储在内存中，重启丢失
