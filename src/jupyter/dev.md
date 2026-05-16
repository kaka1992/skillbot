# Jupyter Integration — %%agent / %%sql Cell Magic

## 文件结构

```
src/jupyter/
├── __init__.py      # load_ipython_extension, 注册 AgentMagic
├── magic.py         # AgentMagic: %%agent, %%sql, %agent_config, 流式输出
├── sql.py           # SqlRunner: spark SQL 业务编排（analyze→submit→poll→result）
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
  └── render_output(ns, result) → print(text) + display + inject

%%sql cell
  ↓ AgentMagic.sql()
  ├── SqlRunner 通过 ToolRegistry 查找 spark preset
  ├── analyze → submit → poll → result（on_progress 回调流式输出）
  └── ns.inject(var_name, DataFrame) → 变量注入

%sql line
  ↓ AgentMagic.sql() [line_magic]
  └── status / cancel / result 子命令分发
```

## 启动

```bash
bash scripts/jupyter.sh
bash scripts/jupyter.sh lab
bash scripts/jupyter.sh notebook --port 9999
```

新建 notebook 选择 "skillbot (Python 3.12)" kernel。`%%agent` / `%%sql` 自动可用。

## 用法

### Agent

```
%agent_config --agent claude-code --timeout 600
%agent_config --config conf/jupyter_agent.yaml

%%agent
1+1=?

%%agent --code
write a function to sort a list

%%agent --timeout 1200
complex analysis task
```

| Magic | 说明 |
|------|------|
| `%agent_config [--config PATH] [--agent NAME] [--timeout N] [--KEY=VALUE ...]` | 配置 agent、超时、注入 env、加载第三方 tools |
| `%%agent` | 调用 agent 执行 cell 内容 |
| `%%agent --code` | 流式显示文本 + 解析后代码注入下一 cell |
| `%%agent --timeout N` | 本次调用超时秒数（默认 600） |

### Spark SQL

```
# 直接查询（analyze → submit → poll → result）
%%sql --var df1 --timeout 600 --poll 30
select * from table

# 提交任务
%%sql submit
select * from table

# 行魔法（无 SQL body）
%sql status --job_id xxxx
%sql cancel --job_id xxxx
%sql result --job_id xxxx --limit 100
```

| Magic | 说明 |
|------|------|
| `%%sql [--var NAME] [--timeout N] [--poll N]` | 直接查询，结果注入为 DataFrame 变量 |
| `%%sql submit` | 提交异步查询任务 |
| `%sql status --job_id ID` | 查询任务状态 |
| `%sql cancel --job_id ID` | 取消任务 |
| `%sql result --job_id ID [--limit N]` | 取查询结果 |

`%%sql` 依赖 `ToolRegistry` 中的 spark tool preset（由 `_spark_sql_presets.py` 定义），与具体实现解耦。可通过 `%agent_config --config xxx.yaml` 加载第三方实现并设定偏好。

## agent_config 配置

### YAML 格式

```yaml
agent: claude-code
timeout: 600
env:
  SPARK_REMOTE: sc://localhost:15002
tools:
  paths:                          # 第三方 tool 代码目录
    - /path/to/databricks_tools/
  preferences:
    presets:                      # per-preset → set_preferred()
      spark_analyze_query: databricks
    groups:                       # per-group → set_preferred_for_group()
      spark: databricks
```

### 执行流程

```
1. 解析 CLI 参数 (--config / --agent / --timeout / KV env)
2. 加载 YAML
3. 注入 env (YAML env + CLI KV，后者覆盖)
4. 加载第三方 tools: ToolRegistry.discover(path)
5. 设定偏好: set_preferred (presets) + set_preferred_for_group (groups)
6. 重建 agent session
```

### CLI 语法

```
%agent_config --config conf/jupyter_agent.yaml
%agent_config --agent deer-flow --timeout 300
%agent_config --SPARK_REMOTE=sc://host --API_TOKEN=abc
```

`tools` 配置仅通过 YAML 支持，CLI 不支持。

## SqlRunner（sql.py）

```
SqlRunner(poll_interval=30, timeout=600)
  ├── query(sql, on_progress)      # analyze → submit → poll → result
  ├── submit(sql, on_progress)     # 仅提交
  ├── status(job_id)              # 查询状态
  ├── cancel(job_id)              # 取消任务
  └── result(job_id, limit)       # 取结果

on_progress(phase, data):
  phase="analyze" → data: {plan}
  phase="submit"  → data: {job_id}
  phase="poll"    → data: {status, elapsed}  # 每次轮询，\r+flush 实时刷新
  phase="result"  → data: {row_count}
  phase="error"   → data: {stage, message}
```

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
| `text` | 文本输出到 cell |
| `files[]` | 文件路径列表，按扩展名处理：`.csv` → DataFrame，`.png/.jpg/.svg` → 内联图片 |
| `code` | `--code` 模式下填入下一 cell |

## Namespace（变量管理）

`Namespace(shell)` 提供统一的 shell 交互：

| 方法 | 功能 |
|------|------|
| `ns.vars()` | 查询用户变量 |
| `ns.inject(name, val)` | 写入变量 |
| `ns.remove(name)` | 删除变量 |
| `ns.context()` | 全量上下文 |
| `ns.delta()` | 增量上下文（仅新变量 + 新 cell） |
| `ns.track_cell(code, output)` | 记录 cell 执行 |
| `ns.set_next_input(code)` | 注入下一 cell 代码 |

## 变量上下文

`__init__` 时调用 `ns.delta()` 建立 baseline。每次 `%%agent` 调用时用 `ns.delta()` 获取增量上下文：

```
Available variables:
  stock_df: DataFrame shape=(30, 6)
  name: str len=5
```

非 agent 的普通 cell 执行通过 `post_run_cell` hook 自动追踪。

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
