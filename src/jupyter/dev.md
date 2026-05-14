# Jupyter Integration — %%agent Cell Magic

## 文件结构

```
src/jupyter/
├── __init__.py      # load_ipython_extension, 注册 %%agent
├── magic.py         # AgentMagic: streaming, session, logging
├── namespace.py     # Namespace: 变量/单元/上下文管理
├── parser.py        # JSON parser → ParsedResult
├── render.py        # render_output: DataFrame/图片/文件/代码注入
└── dev.md
```

## 架构

```
__init__ (extension 加载时)
  ├── Namespace(shell) → 创建 ns
  ├── _init_session(_agent, _timeout) → ChatClient + seed SYSTEM_PROMPT
  └── ns.delta() → 建立 baseline 快照

%%agent cell
  ↓ AgentMagic.agent()
  ├── ns.delta() → 增量上下文（新变量 + 新 cell）
  ├── _stream_output(show_text) → 流式进度 (--code 模式逐 token 输出)
  ├── parse(raw) → JSON → ParsedResult(text, files, code)
  │   └── 解析失败 → ValueError → 打印错误
  └── render_output(ns, result) → print(text) + display + inject
```

## 启动

```bash
bash scripts/jupyter.sh
bash scripts/jupyter.sh lab
bash scripts/jupyter.sh notebook --port 9999
```

新建 notebook 选择 "skillbot (Python 3.12)" kernel。`%%agent` 自动可用。

## 用法

```
%agent_config nanobot                 # 切换 agent
%agent_config claude-code --timeout 1200

%%agent
1+1=?

%%agent --code
write a function to sort a list

%%agent --timeout 1200
complex analysis task
```

| Magic | 说明 |
|------|------|
| `%agent_config <agent> [--timeout N]` | 配置 agent 类型和超时（持久生效，切换时重建 session） |
| `%%agent` | 调用 agent 执行 cell 内容 |
| `%%agent --code` | 流式显示文本 + 解析后代码注入下一 cell |
| `%%agent --timeout N` | 本次调用超时秒数（默认 600，不影响全局配置） |

## 会话

- session key = `MD5(notebook_path)[:12]`，同一 `.ipynb` 共享 session
- Kernel 重启时 `atexit` 清理 session
- 默认 agent = `claude-code`，可通过 `%agent_config` 切换（自动清理旧 session + 重建新 session）
- `SYSTEM_PROMPT` 在 session 创建时注入（JSON 格式指令）

## Agent 输出格式

Agent 输出 JSON（包裹在 `json` fenced block 中）：

```json
{
  "text": "markdown 解释文本",
  "files": ["/tmp/chart.png", "/tmp/data.csv"],
  "code": "print('hello')"
}
```

| JSON field | 行为 |
|------|------|
| `text` | 文本输出到 cell（普通模式 render 打印，--code 模式流式已显示） |
| `files[]` | 文件路径列表，按扩展名处理：`.csv` → DataFrame，`.png/.jpg/.svg` → 内联图片，其他 → 读文件内容注入变量 |
| `code` | `--code` 模式下填入下一 cell |

解析失败直接 `raise ValueError`，上层 catch 并打印 `Parse error`。

## Namespace（变量管理）

`Namespace(shell)` 提供统一的 shell 交互：

| 方法 | 功能 |
|------|------|
| `ns.vars()` | 查询用户变量 |
| `ns.inject(name, val)` | 写入变量 |
| `ns.remove(name)` | 删除变量 |
| `ns.context()` | 全量上下文（公开 API，返回当前完整快照） |
| `ns.delta()` | 增量上下文（仅新变量 + 新 cell） |
| `ns.track_cell(code, output)` | 记录 cell 执行 |
| `ns.set_next_input(code)` | 注入下一 cell 代码 |

## 变量上下文

`__init__` 时调用 `ns.delta()` 建立 baseline。每次 `%%agent` 调用时用 `ns.delta()` 获取增量上下文（新变量 + 新 cell），注入 prompt：

```
Available variables:
  stock_df: DataFrame shape=(30, 6)
  name: str len=5
```

非 agent 的普通 cell 执行通过 `post_run_cell` hook 自动追踪。

`ns.context()` 保留为公开 API，返回全量上下文（不依赖 baseline）。

## 日志

每次 `%%agent` 调用记录到 `.run/agent-YYYYMMDD.log`：

```
============================================================
  [2026-05-13 17:56:08]  session=f7a464868470  elapsed=2.8s
============================================================
  variables: stock_df
  cell history (1 total):
    › df = pd.DataFrame(...)
  prompt: plot close price
  result (120 chars):
    import matplotlib.pyplot as plt
    ...
```
