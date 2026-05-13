# Jupyter Integration — %%agent Cell Magic

## 文件结构

```
src/jupyter/
├── __init__.py      # load_ipython_extension, 注册 %%agent
├── magic.py         # AgentMagic: streaming, session, logging
├── namespace.py     # Namespace: 变量/单元/上下文管理
├── parser.py        # BlockParser: text/csv/image/file/python
├── render.py        # render_output: DataFrame 注入 + 代码 + 渲染
└── dev.md
```

## 架构

```
%%agent cell
  ↓ AgentMagic.agent()
  ├── Namespace.context()/delta() → 变量上下文
  ├── _stream_output() → 逐 token 输出 + thinking/tool 进度
  ├── BlockParser.parse() → text/csv/image/file/python
  └── render_output() → print + inject DataFrame + next cell code
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
%%agent
1+1=?

%%agent --code
write a function to sort a list

%%agent --timeout 1200
complex analysis task
```

## 会话

- session key = `MD5(notebook_path)[:12]`，同一 `.ipynb` 共享 session
- Kernel 重启时 `atexit` 清理 session
- `SYSTEM_PROMPT` 首次注入，后续仅发用户内容

## 输出格式

| Block | 标记 | 行为 |
|------|------|------|
| 纯文本 | fence 外 | streaming 输出 |
| `python` | ` ```python ` | 填入下一 cell（不执行） |
| `csv:<name>` | ` ```csv:name ` | → DataFrame → `user_ns[name]` |
| `file:<name>.csv` | ` ```file:name.csv ` | → DataFrame（文件系统优先，inline fallback） |
| `file:<name>` | ` ```file:name ` | → `user_ns[name]`（字符串） |
| `image` | ` ```image ` | 内联渲染 |

## Namespace（变量管理）

`Namespace(shell)` 提供统一的 shell 交互：

| 方法 | 功能 |
|------|------|
| `ns.vars()` | 查询用户变量 |
| `ns.inject(name, val)` | 写入变量 |
| `ns.remove(name)` | 删除变量 |
| `ns.context()` | 全量上下文（首次调用） |
| `ns.delta()` | 增量上下文（仅新变量 + 新 cell） |
| `ns.track_cell(code, output)` | 记录 cell 执行 |
| `ns.set_next_input(code)` | 注入下一 cell 代码 |

## 变量上下文

每次 `%%agent` 调用时自动将 shell 中的用户变量信息注入 prompt：

```
Available variables:
  stock_df: DataFrame shape=(30, 6)
  name: str len=5
```

首调用使用 `context()`（全量），后续使用 `delta()`（增量）。非 agent 的普通 cell 执行通过 `post_run_cell` hook 自动追踪。

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
