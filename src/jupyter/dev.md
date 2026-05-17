# Jupyter Integration — %%agent / %%sql Cell Magic

## 文件结构

```
src/jupyter/
├── __init__.py           # extension 加载 + logging 初始化 + completer 注册
├── agent_session.py      # session 生命周期 + stream + prompts (SYSTEM_PROMPT/REVIEW_PROMPT)
├── config.py             # agent_config 解析/加载 + tools + debug toggle
├── review.py             # trace review 机制 (review_task / review_line_trace)
├── magic.py              # 薄调度层: AgentMagic (cell/line magic decorator)
├── namespace.py          # Namespace: 变量/单元/上下文 + flush_current_cell
├── parser.py             # JSON parser → ParsedResult
├── render.py             # render_output: DataFrame/图片/文件/代码注入
├── dsl/
│   └── sql/
│       ├── __init__.py       # 导出: SqlRunner, format_sql, register_table
│       ├── sql_runner.py     # SqlRunner: spark SQL 业务编排
│       ├── completer.py      # SQL 关键字补全 + 表/字段缓存
│       └── static/
│           └── sql-cell.js   # CodeMirror 高亮 + Ctrl+Shift+F 格式化
└── dev.md
```

## 架构

```
__init__ (extension 加载时)
  ├── logging 初始化 (.run/jupyter.log, INFO 级别, debug 模式切 DEBUG)
  ├── Namespace(shell) → 创建 ns
  ├── init_session(agent, timeout) → ChatClient + seed merged prompt
  │   └── build_system_prompt(claude_md) → CLAUDE.md + SYSTEM_PROMPT 合并
  ├── ns.delta() → 建立 baseline 快照
  └── load_sql_completer(ipython) → 注册 %%sql 补全

%%agent cell
  ↓ AgentMagic.agent()
  ├── ns.delta() → 增量上下文
  ├── stream_output(prompt, timeout) → 流式进度
  ├── parse(raw) → JSON → ParsedResult(text, files, code)
  ├── render_output(ns, result) → print + display + inject
  └── (--trace) → review_task() → SOLVED? NOT_SOLVED → ns.set_next_input()

%%sql cell
  ↓ AgentMagic.sql()
  ├── SqlRunner.query() → analyze → submit → poll → result
  │   └── on_progress 回调 → sql_progress() 打印进度（\r+flush）
  └── ns.inject(var_name, DataFrame) → CSV 加载 + sample 预览

%agent --trace
  ↓ ns.flush_current_cell() → 追踪 partial cell
  ↓ ns.delta() → review_line_trace() → SOLVED / NOT_SOLVED
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
%agent_config --claude-md conf/claude-md.example

%%agent
1+1=?

%%agent --code
write a function to sort a list

%%agent --trace
fix the bug in the cell above

%%agent --trace --auto
auto-fix all test failures
```

| Magic | 说明 |
|------|------|
| `%agent_config [--config PATH] [--agent NAME] [--timeout N] [--claude-md PATH] [--debug] [--KEY=VALUE ...]` | 配置 agent、CLAUDE.md、超时、注入 env、加载第三方 tools |
| `%%agent` | 调用 agent 执行 cell 内容 |
| `%%agent --code` | 流式显示文本 + 解析后代码注入下一 cell |
| `%%agent --timeout N` | 本次调用超时秒数（默认 600） |
| `%%agent --trace` | 迭代 trace 模式：执行后 review，未解决自动生成重试 cell |
| `%%agent --trace --auto` | 自动模式：review agent 自判断 + 自动执行新 cell |
| `%agent --trace [--auto]` | line magic：flush partial cell → delta → review → 生成重试 cell |

### Agent Trace 流程

```
%%agent --trace
  ↓ agent 执行 → 是否有新 cell？
  ├── 是 → 新 cell 末行注入 %agent --trace → 人工执行
  └── 否 → review_task() 判断 SOLVED / NOT_SOLVED
            └── NOT_SOLVED → ns.set_next_input(%%agent --trace + 修复指令)
```

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
%sql result --job_id xxxx --var df1 --limit 100
```

| Magic | 说明 |
|------|------|
| `%%sql [--var NAME] [--timeout N] [--poll N]` | 直接查询，DataFrame 从 CSV 加载，sample 预览 |
| `%%sql submit` | 提交异步查询任务 |
| `%sql status --job_id ID` | 查询任务状态 |
| `%sql cancel --job_id ID` | 取消任务 |
| `%sql result --job_id ID [--var NAME] [--limit N]` | 取查询结果（CSV → DataFrame） |

`%%sql` 依赖 `ToolRegistry` 中的 spark tool preset。可通过 `%agent_config --config xxx.yaml` 加载第三方实现并设定偏好。Agent 在 `--code` 模式下可生成 `%%sql` cell。

### SQL 语法高亮 + 格式化 + 补全

- `%%sql` cell → 自动 SQL 语法高亮（CodeMirror `text/x-sql`）
- `Ctrl+Shift+F` → 格式化 SQL（`sqlparse`，通过 kernel `format_sql()` 完成）
- Tab 补全：SQL 关键字（~50 个）+ 表/字段缓存（`register_table()` 注册）

## agent_config 配置

### YAML 格式

```yaml
agent: claude-code
timeout: 600
claude_md: conf/claude-md.example    # CLAUDE.md 项目约束
debug: false                          # debug 日志开关
env:
  SPARK_REMOTE: sc://localhost:15002
tools:
  paths:
    - /path/to/databricks_tools/
  preferences:
    presets:                          # per-preset → set_preferred()
      spark_analyze_query: databricks
    groups:                           # per-group → set_preferred_for_group()
      spark: databricks
```

### 执行流程

```
1. 解析 CLI (--config / --agent / --timeout / --claude-md / --debug / KV env)
2. 加载 YAML
3. debug toggle
4. 注入 env (YAML env + CLI KV)
5. 加载第三方 tools: ToolRegistry.discover(path)
6. 设定偏好: set_preferred (presets) + set_preferred_for_group (groups)
7. session 重建判断 → init_session(agent, timeout, claude_md_path)
```

### session 重建规则

| 变更 | 行为 |
|------|------|
| agent 类型变化 | 重建 session |
| CLAUDE.md 路径变化 | 重建 session |
| timeout / env / debug 变化 | 仅更新运行时参数 |
| tools paths / preferences 变化 | 仅增量 discover + set_preferred（不触发重建） |

### CLI 语法

```
%agent_config --config conf/jupyter_agent.yaml
%agent_config --agent deer-flow --timeout 300
%agent_config --claude-md conf/claude-md.example
%agent_config --debug
%agent_config --SPARK_REMOTE=sc://host --API_TOKEN=abc
```

`tools` 配置仅通过 YAML 支持。

## SqlRunner（dsl/sql/sql_runner.py）

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

## AgentSession（agent_session.py）

```
build_system_prompt(claude_md_path) → CLAUDE.md + SYSTEM_PROMPT 合并
init_session(agent, timeout, claude_md_path) → ChatClient + seed merged prompt
stream_output(prompt, timeout, show_text) → 流式输出 + 工具调用显示
get_client() / get_session_id() → 当前 session 状态
```

## Review（review.py）

```
review_task(task, agent_output, variables, cells, timeout, auto) → SOLVED/NOT_SOLVED/None
review_line_trace(delta, variables, timeout) → raw agent response
parse_review_result(raw) → SOLVED/NOT_SOLVED/None
```

## 会话

- session key = `MD5(notebook_path)[:12]`，同一 `.ipynb` 共享 session
- Kernel 重启时 `atexit` 清理 session
- 默认 agent = `claude-code`，可通过 `%agent_config` 切换
- Seed prompt = `CLAUDE.md（项目约束）` + `SYSTEM_PROMPT（输出格式）`

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
| `files[]` | 文件路径列表，按扩展名处理 |
| `code` | Python 代码或 `%%sql` magic → `--code` 模式注入下一 cell |

## Namespace（变量管理）

`Namespace(shell)` 提供统一的 shell 交互：

| 方法 | 功能 |
|------|------|
| `ns.vars()` | 查询用户变量 |
| `ns.inject(name, val)` | 写入变量（重名时 stderr warning） |
| `ns.remove(name)` | 删除变量 |
| `ns.context()` | 全量上下文 |
| `ns.delta()` | 增量上下文（仅新变量 + 新 cell） |
| `ns.track_cell(code, output)` | 记录 cell 执行 |
| `ns.set_next_input(code)` | 注入下一 cell 代码 |
| `ns.flush_current_cell(marker)` | 追踪当前 cell 中 marker 之前的代码 |

## 日志

标准 Python `logging` 模块，每个模块 `_log = logging.getLogger(__name__)`。

- 默认 `INFO` 级别 → `.run/jupyter.log`
- `%agent_config --debug` → `DEBUG` 级别（显示完整 agent 输出、SQL 详情等）
- `%agent_config --no-debug` → 恢复 `INFO`
