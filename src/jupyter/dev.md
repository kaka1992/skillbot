# Jupyter Integration — %%agent Cell Magic

## 文件结构

```
src/jupyter/
├── __init__.py      # load_ipython_extension, 注册 %%agent
├── magic.py         # AgentMagic cell magic + session 管理
├── parser.py        # BlockParser, 提取 text/csv/image/file blocks
├── render.py        # render_output, 注入 DataFrame + 渲染图像
└── dev.md
```

## 架构

```
%%agent cell
  ↓ AgentMagic.agent()
ChatClient.chat(session=notebook_hash)
  ↓ agent 返回
BlockParser.parse() → text / csv / image / file
  ↓
render_output() → print text + inject DataFrame + display image
```

## 启动

`scripts/jupyter.sh` 一键启动 Jupyter，自动注册 "skillbot (Python 3.12)" kernel。

```
bash scripts/jupyter.sh
bash scripts/jupyter.sh lab
bash scripts/jupyter.sh notebook --port 9999
```

Kernel 通过 `bootstrap.py` monkey-patch `IPKernelApp.init_shell` 加载 `%%agent` magic。

## 会话

同一 `.ipynb` 文件共享同一个 agent session（session ID = MD5(notebook_path)[:12]）。Kernel 重启时 `atexit` 自动清理 session。

## 输出格式

Agent 被指导按以下格式返回：

```markdown
Your explanation here.

```csv:stock_df
date,close
2026-01-01,123.45
```

```image
<base64 PNG>
```
```

| Block | 行为 |
|------|------|
| 纯文本（fence 外） | `print()` 到 cell 输出 |
| `csv:<name>` | `pd.DataFrame` → `user_ns[name]` |
| `image` | `IPython.display.Image` 直接渲染 |
| `file:<name>` | 注入为 `user_ns[name]`（字符串） |
