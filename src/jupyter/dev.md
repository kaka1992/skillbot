# Jupyter Integration — Agent Panel + %%sql Cell Magic

## 文件结构

```
src/agent/
├── __init__.py              # AgentSession, SubAgentConfig, SubAgentSession, SYSTEM_PROMPT
├── prompt.py                # 通用 SYSTEM_PROMPT（JSON 输出 + code 字段 + 不自行执行）
└── session.py               # AgentSession + SubAgentSession + _stream()

src/chat/
├── __init__.py              # ChatClient + _AGENTS 注册表
└── skill.py                 # SkillManager: install/uninstall/enable/disable/inject_prompt
                             #   持久化到 .skill_state.json，大小写不敏感 SKILL.md 查找
                             #   自动过滤 macOS zip __MACOSX / ._* 垃圾文件

src/task/
├── __init__.py              # Task, TaskManager
├── manager.py               # TaskManager: CRUD + 依赖解析
└── task.py                  # Task (dataclass)

src/jupyter/
├── __init__.py              # extension 加载 + logging 初始化 + magics 注册 + panel bridge
├── cell_snapshot.py         # Cell 级别版本快照（auto-save，50 版本 ring buffer）
├── comm.py                  # Comm 通知前端扩展（fire-and-forget，无阻塞）
├── config.py                # agent_config: CLI/YAML 解析、tools 加载、debug
├── magic.py                 # 调度层: AgentMagic + AgentState 状态机（prompt/confirm/continue/auto-fix/snapshot/optimize）
├── namespace.py             # Namespace: vars / context / delta / cell tracking / remove_cell_by_id / track_context
├── notebook_snapshot.py     # Notebook 级别完整快照（take/list/restore，50 版本 ring buffer）
├── panel.py                 # 前端 panel comm bridge（send_to_panel + init_panel_comm + skill_list/info）
├── parser.py                # Parser: JSON→code fence→raw + parse_review_result + md 检测
├── render.py                # 统一输出层 + SQL 自动检测（sqlparse）
├── snapshot_utils.py        # 共享 notebook 识别（notebook_id + dir_for + 前端路径注入）
├── telemetry.py             # SessionEventRecorder: buffer + session-end JSONL flush
├── dsl/
│   └── sql/
└── extension/
    ├── src/
    │   ├── index.ts          # 插件注册（panel + sql）
    │   ├── panel.ts          # AgentPanel 主组件（widget、kernel/comm、keyboard、send）
    │   ├── panelStyles.ts    # CC 色板 + Shadow DOM CSS（隔离 JupyterLab 样式）
    │   ├── panelRenderer.ts  # 输出渲染（text/tool/thinking/code/plan/result）
    │   ├── panelPlanConfirm.ts # 计划确认 UI（3 选项 + 反馈文本域）
    │   └── sql.ts            # SQL 格式化 (Ctrl+Shift+F) + SQL 高亮 (@codemirror/lang-sql)
    └── lib/                  # 编译输出

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
  │   └── SYSTEM_PROMPT + project prompt 合并 → seed prompt
  │   └── _register_hooks → CODE_REVIEW + AGENT_CELL_REVIEW
  ├── SessionEventRecorder + ns.delta() baseline
  └── init_panel_comm(shell) → 注册 comm target（前端主动创建）

Panel 交互流
  ↓ 用户在右侧 panel 输入 prompt
  ├── panel.ts _sendPrompt() → kernel.requestExecute → magic.py _panel_input()
  ├── _handle_panel_prompt(prompt, mode) → _stream_with_interrupt() → 流式输出到 panel
  │   ├── mode="default" → _ask_confirm(pending=result) → 前端 Yes/No 确认
  │   │   ├── Yes → 注入 cell + 自动执行 → _on_cell_run → _finish_agent_run
  │   │   └── No → _finish_agent_run
  │   ├── mode="plan" → 注入 plan 指令前缀 → 仅显示 plan → plan_confirm
  │   │   └── plan_confirm → 前端显示计划确认 UI（3 选项 + 反馈）
  │   │       ├── Yes (auto-execute) → _implement_plan(auto=True) → cell 注入+执行
  │   │       ├── Yes (accept_edits) → _implement_plan(auto=False) → _ask_confirm
  │   │       └── No, revise → 反馈文本域 → 修订 plan → 重新确认
  │   └── mode="auto" → render_output(auto=True) → 自动执行
  │       └── cell 错误 → _on_cell_run → _auto_fix_cell → AI 修复 → 替换 cell
  ├── /continue yes|no → _handle_continue → 下一轮 / 停止
  └── /cell-optimize → _handle_cell_optimize → Agent 优化指定 cell → replace_cell_id

AgentState 状态机（`magic.py:AgentState`）：
  IDLE → STREAMING → WAITING_CONFIRM → /continue yes → STREAMING (loop)
                   → PLAN_REVIEW → /confirm → STREAMING / WAITING_CONFIRM
                   → AUTO_FIXING (auto mode error) → STREAMING
  任意状态 + KeyboardInterrupt → _interrupt_cleanup() → IDLE

%agent_config (行魔法)
  ↓ AgentMagic.agent_config_func()
  ├── 解析 CLI/YAML 参数 → configure_agent
  ├── session_rebuild → _init_session（切换 agent / 更新 system prompt）
  └── timeout 更新 → 热更新 client timeout

Hook 执行
  ↓ dispatch(event, context, session=self._session)
  ├── hook.on_event(event, context, session)
  │   └── session.get_sub("code_review|cell_review").execute(task)
  │       └── SubAgentSession: 独立 client + session + seed prompt
  └── telemetry: record("hook_event", ...)
```

## 前端 Panel 架构

### 模式系统（cc-haha 风格）

| 模式 | 标记 | 颜色 | 行为 |
|------|:---:|------|------|
| default | ❯ | — | cell 注入，手动执行 |
| plan | ⏸ | cyan | 先调研出方案，确认后执行 |
| auto | ⏵⏵ | purple | cell 注入 + 自动执行 + 错误自动修复 |

Shift+Tab 循环切换模式。模式切换时 info bar 显示随机提示（4s 后回退到持久指示符）。

### 输入框能力（对齐 cc-haha TUI）

| 类别 | 快捷键 | 功能 |
|------|--------|------|
| 光标 | Ctrl+A/E | 行首/行尾 |
| 光标 | Ctrl+B/F | 字符左/右 |
| 光标 | Alt+B/F | 单词左/右 |
| 编辑 | Ctrl+H | 退格 |
| 编辑 | Ctrl+D | 前向删除 / 空输入清空 |
| 编辑 | Ctrl+K | 剪切到行尾 |
| 编辑 | Ctrl+U | 剪切到行首 |
| 编辑 | Ctrl+W | 剪切前一个词 |
| 编辑 | Ctrl+Y | 粘贴（kill ring） |
| 编辑 | Ctrl+C | 清空输入（无选中时） |
| 提交 | Enter | 发送 prompt |
| 提交 | Shift/Meta/Enter | 插入换行 |
| 历史 | ↑/↓（首/末行） | 历史导航 |
| 历史 | Ctrl+P/N | 历史导航 |
| 模式 | Shift+Tab | 循环模式 |
| 模式 | Tab | 补全 / 命令 |
| 面板 | Ctrl+L | 清空面板 |

### 计划确认 UI

计划生成后，输入区替换为确认界面：
- **计划预览** — 可滚动（max 200px），深色背景 + 青色左边框
- **3 个选项** — Tab/↑↓ 选择，Enter 确认：
  1. Yes (accept edits) — 注入 cell，手动审查
  2. Yes (auto-execute) — 注入 cell + 自动执行
  3. No, revise — 显示反馈文本域
- **反馈模式** — 输入修订意见，Enter 提交，Esc 返回选项
- Esc 取消，Ctrl+C 放弃计划

### Skill 管理面板（`/skills` 命令）

输入 `/skills` 进入独立的 skill 管理视图，输入框隐藏，所有操作在面板内完成：

| 层级 | 操作 | 说明 |
|------|------|------|
| 列表 | ↑↓ | 选择 skill |
| 列表 | Enter | 进入详情（描述 + 截断 body） |
| 列表 | Space | 启用/禁用（即时生效，下一条 query 注入变更通知） |
| 列表 | d | 卸载（二次确认，3s 超时取消） |
| 列表 | i | 安装（弹出路径输入框，Enter 提交，自动识别 SKILL.md 大小写） |
| 列表 | Esc | 退出 skills 模式，恢复 Agent 输入框 |
| 详情 | Enter | 查看完整 SKILL.md body（350px 可滚动） |
| 详情 | Esc | 返回列表 |
| 安装框 | Enter | 提交安装，自动关闭输入框 |
| 安装框 | Esc | 取消安装 |

- 后端通过 `SkillManager`（`src/chat/skill.py`）操作，不经过 agent
- 前端 `panel.ts` 中 `_enterSkillsMode()` / `_exitSkillsMode()` 控制视图切换
- Comm 协议：`skill_list`（列表数据）、`skill_info`（详情）
- macOS zip 的 `__MACOSX` / `._*` 垃圾文件自动过滤

### Cell / Notebook 快照系统

每次 cell 执行时自动保存版本快照，支持回滚到任意历史版本。存储目录：

```
.run/
├── cell_snapshots/<notebook_hash>/<cell_id>/v0001.json ... v0050.json
└── notebook_snapshots/<notebook_hash>/<timestamp>.json
```

**Cell 快照** (`cell_snapshot.py`)：
- `save(cell_id, code, output, error, nb_path)` — auto-save 每次 cell 执行后，最多保留 50 版本
- `list_versions(cell_id, nb_path)` — 列出某 cell 的所有版本，最新在前
- `restore(cell_id, version, nb_path)` — 返回指定版本的 code

**Notebook 快照** (`notebook_snapshot.py`)：
- `take(cells, nb_path)` — 保存所有 cell 的完整快照，最多 50 个
- `list_snapshots_for(nb_path)` — 列出快照列表（含 preview）
- `restore(snapshot_id, nb_path)` — 回滚整个 notebook
- 自动触发：cell 执行后 → `_on_cell_run` → `take_snapshot()`
- 手动触发：panel `/snapshot` 命令

**文件隔离** (`snapshot_utils.py`)：
- 前端通过 `_set_active_notebook_path(path)` 注入当前 notebook 路径（最可靠）
- 后端通过 `dir_for(path)` → `md5(path)[:12]` 生成目录名
- 保存和查询使用同一路径源，确保 hash 一致
- `notebook_id()` 提供多级 fallback（前端路径→parent_header→ip._notebook_path→CWD）

**快照恢复**：
- Cell 恢复：`send_cell_via_comm(code, replace_cell_id=cell_id)` → 前端替换并执行
  - `_restoring_cells` set 追踪恢复中的 cell_id，跳过 snapshot 防止循环
- Notebook 恢复：前端直接操作 `sharedModel`，清空所有 cell 后重新插入（不触发执行）
- `store_history: false` 过滤：前端查询代码不触发 `_on_cell_run`，避免污染快照

**右键菜单** (panel.ts)：
- `.jp-Notebook` 添加 "Snapshots" 子菜单
- **Cell Snapshots** — 查看当前 cell 的版本历史，预览 code + output，一键恢复
- **Notebook Snapshots** — 查看整个 notebook 的快照时间线，预览 cell 摘要，一键回滚

### Cell 优化（右键 → Agent → Optimize with Agent）

右键 cell → "Agent" → "Optimize with Agent" → 弹出对话框：
- 输入优化意图（e.g. optimize query, fix bug, improve readability）
- Enter → Optimize（替换 cell，不自动执行）
- Shift+Enter → Optimize & Run（替换 cell + 自动执行）

- 前端收集 cell code + output + errors → `/cell-optimize` → `_handle_cell_optimize`
- 自动检测 SQL（`%%sql`）vs Python，构建对应优化 prompt
- Agent 返回优化后代码 → `render_code(replace_cell_id=cell_id)` 替换原 cell
- Namespace 更新：`remove_cell_by_id` 移除旧 cell 记录，`track_context` 注入 `[system]` 优化记录

### 任务循环（/continue + /stop）

Default 模式下 Agent 生成 cell 后弹出 Yes/No 确认按钮：
- **Yes** → cell 注入 + 自动执行 → `_finish_agent_run`
- **No** → 结束
- Text-only 响应 → "Continue?" → Yes 继续对话，No 结束

Plan 模式 confirm 后同 default 流程。
Auto 模式跳过确认，直接注入+执行+自动修复。

### 斜杠命令自动补全

输入 `/` 时自动显示命令下拉列表，Tab/Enter 提交，Esc 关闭：

| 命令 | 功能 |
|------|------|
| `/confirm` | 计划确认（内部使用） |
| `/clear` | 清空 panel 输出 |
| `/mode <name>` | 切换模式 |
| `/skills ...` | Skill 管理面板 |
| `/config ...` | Agent 配置管理 |
| `/snapshot` | 手动创建 notebook 快照 |
| `/continue yes\|no` | 继续/停止当前任务循环 |
| `/stop` | 立即退出当前任务 |
| `/cell-optimize` | Agent 优化指定 cell（内部使用，右键菜单触发） |

### Ctrl+C 中断机制

```
Ctrl+C (kernel.interrupt) → KeyboardInterrupt 在 AgentSession._stream() 中抛出
  → _stream handler: ChatClient.interrupt(session) → POST /sessions/{sid}/interrupt
    → Server: Session.interrupt() → ClaudeSDKClient.interrupt() → subprocess 停止
  → gen.close() → finally: resp.close() → TCP 关闭 → Server CancelledError
  → KeyboardInterrupt 传播到 magic 层 handler
  → 清理 _busy / _auto_pending / _session_dirty
  → send_to_panel("ready") → 前端 dequeue 下一个 query
  → handler 不再 raise（避免堵塞 IPython Shell channel）
```

- `_session.py` 的 `_stream()` 负责调用 `interrupt()` + `gen.close()`
- magic 层 handler 只做状态清理 + 发送 `ready`，**不 propagate KeyboardInterrupt**
- 服务端 `_apply_tool_fix()` 在下次查询前补全中断留下的未完成 tool_use
- plan / auto / auto-fix 三种模式下中断均适用

### 自动错误修复（auto 模式）

```
cell 执行失败 → _on_cell_run 检测 "# %%agent generate code" 标记
  → _auto_fix_cell → AI 分析错误 + 生成修复
  → render_code(auto=True, replace_cell_id=...) → 替换原 cell + 自动执行
  → 最多重试 3 次，递归保护防止无限循环
```

### 文件职责

| 文件 | 内容 |
|------|------|
| `panel.ts` | AgentPanel 主组件（widget、构造器、kernel/comm、_sendPrompt、block 管理、清理、状态栏、模式循环、cell comm handler、插件注册） |
| `panelStyles.ts` | CC 色板 + Shadow DOM CSS（约 280 行） |
| `panelRenderer.ts` | 输出渲染：text/tool/thinking/code_block/plan_block/result |
| `panelPlanConfirm.ts` | 计划确认 UI：渲染选项、提交/取消、反馈处理 |

## 输出分层 (render.py)

| 方法 | 用途 | 输出目标 |
|------|------|---------|
| `render_text(text)` | 结果内容 | stdout |
| `render_markdown(text)` | markdown 渲染 | IPython.display.Markdown |
| `render_info(text)` | 状态/进度/提示 | stdout |
| `render_error(text)` | 错误 | stderr (红) |
| `render_debug(text)` | 诊断（需 --debug） | stdout |
| `render_code(ns, code, auto, trace, replace_cell_id, on_cell_id)` | 创建/替换 cell | comm → 前端 |
| `render_variables(ns)` | 变量上下文 | stdout |
| `render_image(data)` | 内联图片 | IPython.display.Image |
| `render_sql_dataframe(ns, data, name)` | SQL 结果注入 | CSV→DataFrame + preview |
| `render_output(ns, result, ..., on_cell_id)` | 调度所有 render + 追踪 cell ID | — |

render 函数**只做显示**，不写 log。

## 启动

```bash
bash scripts/jupyter.sh
bash scripts/jupyter.sh lab
bash scripts/jupyter.sh notebook --port 9999

# 仅重建前端（不改 Python 时）
bash scripts/jupyter.sh --rebuild
```

新建 notebook 选择 "skillbot (Python 3.12)" kernel。

## 用法

### Agent Panel（右侧面板）

所有 agent 交互通过右侧 "Agent" 面板进行：
- 输入 prompt → Enter 发送
- Shift+Tab 切换模式（default/plan/auto）
- ↑↓ 历史导航（首/末行时）
- Ctrl+L 清空面板

### Agent 配置

```
%agent_config --agent claude-code --timeout 600 --debug
%agent_config --config /absolute/path/to/jupyter_agent.yaml
%agent_config --claude-md /absolute/path/to/claude-md.example
```

| Flag | 说明 |
|------|------|
| `--config PATH` | YAML 配置路径（需绝对路径） |
| `--agent NAME` | agent 名称（claude-code / nanobot / hermes-agent） |
| `--timeout N` | 超时秒数（默认 600） |
| `--claude-md PATH` | CLAUDE.md 项目约束（需绝对路径） |
| `--debug` | 开启 debug 日志 |

### `/config` 命令（Panel 交互）

Panel 中输入 `/config` 管理 agent 配置：

| 命令 | 说明 |
|------|------|
| `/config` | 显示当前配置详情（path、agent、timeout、claude-md） |
| `/config <path>` | 加载新配置：首次直接生效，已有配置时显示新旧对比 |
| `y` / `n` | 配置对比后键盘确认/取消（不需 Enter，IME 自动兼容） |
| `Esc` | 取消 pending 变更 |

```
──────────────────────────────────────────────────
  Config Status
  ──────────────────────────────────────
  path    : /path/to/config.yaml
  agent   : hermes-agent
  timeout : 600s
  claude-md: (none)
  ──────────────────────────────────────
```

**配置自动加载**：kernel 启动时从 `JUPYTER_CONFIG_PATH` 环境变量（`conf/.env` 中配置）自动加载。
| `--KEY=VALUE` | 注入环境变量 |

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

`SessionEventRecorder` — 内存缓冲 + session 结束时批量写入 JSONL。存储于 `.run/sessions/{session_id}.jsonl`。

| 事件 | 采集点 | 触发时机 |
|------|------|------|
| `session_start` / `session_end` | `SessionEventRecorder.__init__` / `flush()` | Session 生命周期 |
| `cell_executed` | `_on_cell_run` | 每个 cell 执行后（含 cell_id、exec_order、elapsed_ms） |
| `agent_prompt` | `_handle_panel_prompt` / `_handle_continue` | Agent 调用前 |
| `agent_response` | `_stream_with_interrupt` | Agent 返回后（含 tool_names、thinking_chars、elapsed_ms） |
| `agent_continue` | `_handle_continue` | 用户 /continue yes|no |
| `workflow_state` | 状态机各转换点 | confirm_shown / user_continue / user_stop / interrupt / agent_done / plan_confirm / auto_fix |
| `hook_event` | `HookRegistry.dispatch` | Hook 执行后 |

Flush 触发：kernel shutdown 时通过 `atexit` 注册自动写入。

## 前端扩展

### 构建

```bash
cd src/jupyter/extension
jlpm install && jlpm run build
# 或通过脚本一键重建：
bash scripts/jupyter.sh --rebuild
```

### 插件

| 插件 | 文件 | 功能 |
|------|------|------|
| panel | panel.ts + panelStyles.ts + panelRenderer.ts + panelPlanConfirm.ts | Agent TUI panel（Shadow DOM 隔离 CSS） |
| sql | sql.ts | SQL 格式化 (Ctrl+Shift+F) + SQL 高亮 |
