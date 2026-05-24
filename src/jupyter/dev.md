# Jupyter Integration — %%agent / %%sql Cell Magic

## 文件结构

```
src/agent/
├── __init__.py              # AgentSession, SubAgentConfig, SubAgentSession, SYSTEM_PROMPT
├── prompt.py                # 通用 SYSTEM_PROMPT（JSON 输出 + code 字段 + 不自行执行）
└── session.py               # AgentSession + SubAgentSession + _stream()

src/task/
├── __init__.py              # Task, TaskManager
├── manager.py               # TaskManager: CRUD + 依赖解析
└── task.py                  # Task (dataclass)

src/jupyter/
├── __init__.py              # extension 加载 + logging 初始化 + magics 注册
├── comm.py                  # Comm 通知前端扩展（fire-and-forget）
├── config.py                # agent_config: CLI/YAML 解析、tools 加载、debug
├── feedback.py              # %feedback / %fb 行魔法（yes/no + --comment）
├── magic.py                 # 调度层: AgentMagic + MAGIC_PROMPT + session helpers
├── namespace.py             # Namespace: vars / context / delta / cell tracking
├── parser.py                # Parser: JSON→code fence→raw + parse_review_result + md 检测
├── render.py                # 统一输出层 + SQL 自动检测（sqlparse）
├── telemetry.py             # TelemetryRecorder: JSONL session 事件采集
├── dsl/
│   └── sql/
└── extension/

src/hook/
├── __init__.py
├── base.py                  # Hook (ABC), HookGroup, HookRegistry
├── events.py                # HookEvent, HookStatus, HookResult
└── impl/
    ├── code_review.py       # AgentCodeReviewHook（通过 SubAgentSession 执行）
    └── cell_review.py       # AgentCellReviewHook（通过 SubAgentSession 执行）
```

## 架构

```
__init__ (extension 加载时)
  ├── logging 初始化 + Namespace(shell)
  ├── AgentSession(agent, timeout) → configure_subs + init_session
  │   └── SYSTEM_PROMPT + MAGIC_PROMPT 合并 → seed prompt
  │   └── _register_hooks → CODE_REVIEW + AGENT_CELL_REVIEW
  └── TelemetryRecorder + ns.delta() baseline

%%agent cell
  ↓ AgentMagic.agent_func()
  ├── ns.delta() → 增量上下文
  ├── session.stream(prompt, timeout) → 流式进度
  ├── parse(raw) → ParsedResult
  ├── render_output(ns, result) → render 层
  │   ├── is_markdown → render_markdown / render_text
  │   ├── code_list → render_code (SQL 自动检测 %%sql) → comm → 新 cell
  │   └── files → _load_csv / _display_image_file / ns.inject
  └── telemetry: record("agent_call", ...) + (--trace) → dispatch AGENT_CELL_REVIEW

Hook 执行
  ↓ dispatch(event, context, session=self._session)
  ├── hook.on_event(event, context, session)
  │   └── session.get_sub("code_review|cell_review").execute(task)
  │       └── SubAgentSession: 独立 client + session + seed prompt
  └── telemetry: record("hook_event", ...)
```

## 输出分层 (render.py)

| 方法 | 用途 | 输出目标 |
|------|------|---------|
| `render_text(text)` | 结果内容 | stdout |
| `render_markdown(text)` | markdown 渲染 | IPython.display.Markdown |
| `render_info(text)` | 状态/进度/提示 | stdout |
| `render_error(text)` | 错误 | stderr (红) |
| `render_debug(text)` | 诊断（需 --debug） | stdout |
| `render_code(ns, code, auto, trace)` | 创建新 cell | comm → 前端 |
| `render_variables(ns)` | 变量上下文 | stdout |
| `render_image(data)` | 内联图片 | IPython.display.Image |
| `render_sql_dataframe(ns, data, name)` | SQL 结果注入 | CSV→DataFrame + preview |
| `render_output(ns, result, skip_text, auto, trace)` | 调度所有 render 方法 | — |

render 函数**只做显示**，不写 log。

## 启动

```bash
bash scripts/jupyter.sh
bash scripts/jupyter.sh lab
bash scripts/jupyter.sh notebook --port 9999
```

新建 notebook 选择 "skillbot (Python 3.12)" kernel。

## 用法

### Agent

```
%agent_config --agent claude-code --timeout 600 --debug

%%agent
1+1=?

%%agent --trace
fix the bug in the cell above
```

| Flag | 说明 |
|------|------|
| `--trace` | 执行后触发 AgentCellReviewHook |
| `--auto` | 自动执行生成的 cell |
| `--timeout N` | 超时秒数（默认 600） |

### Feedback

```
%fb yes / %fb no
%fb yes --comment "图表正确"
```

### SQL / Spark

```
%%sql --var df1 --timeout 600 --poll 30
select * from table

%%sql submit
select * from table
```

## Agent 输出

Agent 输出 JSON（code 字段统一由用户 cell 执行，不在 Bash 中运行）：

```json
{
  "text": "markdown 解释文本",
  "files": ["/tmp/chart.png", "/tmp/data.csv"],
  "code": ["print('hello')"]
}
```

`render_code` 自动 SQL 检测（sqlparse），对 SQL 代码自动添加 `%%sql` magic。

## Session

### AgentSession（主 agent）

`src/agent/session.py`。`init_session()` seed prompt + on_init 回调。`stream()` 流式调用。`_stream()` 静态方法被 SubAgentSession 复用。

### SubAgentSession（子 agent）

独立 client + session。`execute(task)` 从 task.metadata 读 prompt/context，调用 `_stream()`。persistent 模式跨 task 复用 session。

### 配置

```python
SUB_AGENT_DEFAULTS = {
    "code_review": SubAgentConfig(name="code_review", tools=["Read", "Grep", "Glob"]),
    "cell_review": SubAgentConfig(name="cell_review", tools=["Read", "Bash"]),
}
```

### Task

`Task(task_id, subject, metadata)` —— 通用任务模型。metadata 承载 `prompt`/`context`/`results`。

## Hook 体系

`dispatch(event, context, session=session)` 显式传入 session。Hook 通过 `session.get_sub(name).execute(task)` 委托子 agent：

### AgentCellReviewHook

SOLVED/NOT_SOLVED/SOLVING 三态。用 `ns.context()` 获取完整上下文。SOLVED 时生成 markdown 总结。

## Telemetry

| 事件 | 采集点 |
|------|------|
| `cell_executed` | `_on_cell_run` |
| `agent_call` | `agent_func` |
| `hook_event` | `HookRegistry.dispatch` |
| `feedback` | `%feedback` |

## 前端扩展

| 插件 | 功能 |
|------|------|
| comm.ts | 接收 comm → 创建 cell + 可选执行 |
| sql.ts | SQL 格式化 (Ctrl+Shift+F) + SQL 高亮 (@codemirror/lang-sql) |

构建：`jlpm install && jlpm run build`
