# Eval — Agent 评测框架

## 设计目标

异步优先、JSONL 驱动的 agent 评测框架。通过 `chat` 模块的统一接口，
对任意 agent 运行评测数据集，支持并发控制、自动评分、自定义 grader、结果持久化。

## 文件结构

```
src/eval/
├── __init__.py    # 导出所有公共 API
├── loader.py      # JSONL 数据集加载器（EvalDataset）
├── runner.py      # 异步评测运行器（AsyncEvalRunner + Grader 系统）
├── task.py        # 批量 Task 执行（EvalTask + load_tasks + run_tasks）
└── dev.md
```

## JSONL 数据集格式

```jsonl
{"id": "q1", "question": "1+1=?", "expected": "2", "tags": ["math", "easy"]}
{"id": "q2", "question": "Say hello in one word", "expected": "hello"}
# 注释以 # 开头，空行被跳过
{"id": "q3", "question": "Capital of France?", "expected": "Paris", "tags": ["geo"], "difficulty": 1}
```

| 字段 | 必填 | 说明 |
|------|:---:|------|
| `id` | — | 题目 ID，缺省用行号 |
| `question` | **是** | 发送给 agent 的问题 |
| `expected` | — | 期望答案，传给 grader 用于匹配 |
| `tags` | — | 标签，OR 逻辑过滤 |
| 其他 | — | 存入 `extra`，透传到 grader |

## EvalDataset

```python
from eval import EvalDataset

ds = EvalDataset("questions.jsonl")
ds = EvalDataset("questions.jsonl", tags=["math"], limit=10, shuffle=True, seed=42)

len(ds)          # 过滤后数量
ds.tags          # 所有标签
ds[0].question   # 索引访问

for item in ds:  # 迭代
    print(item.id, item.question, item.tags)
```

过滤顺序：加载全部 → tag 过滤（OR）→ shuffle → limit 截取。

## AsyncEvalRunner

```python
from eval import AsyncEvalRunner
from chat import ChatClient

client = ChatClient("nanobot")
runner = AsyncEvalRunner(
    chat_fn=lambda q: client.async_chat(q, session="eval"),
    concurrency=5,      # 最大并发数（asyncio.Semaphore）
    # grader 默认使用 default_grader（子串匹配），传 None 禁用
)
```

### Grader 系统

每个 item 执行完 chat 后调用 grader。默认使用 `default_grader`（子串匹配），传 `grader=None` 跳过评分。

**GraderFn 签名：** `(expected: str, answer: str, extra: dict) -> GraderOutput`

**GraderOutput 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | `bool \| None` | 通过/失败/未评估 |
| `score` | `float \| None` | 可选评分 |
| `detail` | `dict \| None` | 可选详情 |

**default_grader** — 内置默认：大小写不敏感子串匹配。

**自定义 grader 示例：**

```python
from eval import GraderOutput

# 评分式评估
def score_grader(expected, answer, extra):
    ok = expected.strip().lower() in answer.strip().lower()
    return GraderOutput(success=ok, score=1.0 if ok else 0.0)

# 利用 extra 字段的多参考答案评估
def multi_ref_grader(expected, answer, extra):
    refs = extra.get("references", [expected])
    matched = [r for r in refs if r.lower() in answer.lower()]
    return GraderOutput(
        success=len(matched) > 0,
        detail={"matched": matched},
    )

runner = AsyncEvalRunner(chat_fn, grader=score_grader)
```

### Grader 注册表

通过 `register_grader()` 注册命名 grader，可在 YAML 中通过名字引用：

```python
from eval import register_grader

register_grader("score", score_grader)
register_grader("multi_ref", multi_ref_grader)
```

YAML 中引用：

```yaml
tasks:
  - name: test
    dataset: data.jsonl
    grader: score            # 查找注册表 → score_grader
    # grader: default        # 内置默认（等同于不写）
    # grader: none           # 禁用评分
    # grader: pkg.mod:fn     # 动态 import
```

注册表预置 `"default"` → `default_grader`。

### 运行流程

```
dataset 逐条 → asyncio.Semaphore(concurrency) 限流
  │
  ├── 并发调用 chat_fn(question) → answer
  ├── 异常捕获 → error
  ├── 调用 grader(expected, answer, extra) → GraderOutput
  ├── 计时 elapsed
  ├── 打印进度 [i/total] id (OK/ERR/--) elapsed
  └── yield EvalResult
```

## 并发控制

`asyncio.Semaphore(concurrency)` 限制同时进行的 chat 调用数：

```
concurrency=1  → 串行，一次一个请求
concurrency=3  → 最多 3 个并发
concurrency=10 → 最多 10 个并发（注意 agent 限流）
```

`asyncio.as_completed` 收集结果，先完成先返回（不保证顺序）。

## 结果导出

`save("results.jsonl")` 写入两个文件：

**results.jsonl** — JSONL 数据：
```jsonl
{"id": "q1", "question": "1+1=?", "expected": "2", "answer": "2", "success": true, "score": 1.0, "elapsed": 1.2, "tags": ["math"], "error": "", "eval_date": "2026-05-08 20:00:00"}
```

**results.report.txt** — 可读报告（同时打印到 stdout）：
```
Eval Report (20 items)
  Passed:  18
  Failed:  2
  Errors:  0
  Avg time: 1.5s
  Accuracy: 90.0%
```

`score` 和 `grade_detail` 仅在非空时写入 JSONL。可直接用 `EvalDataset` 重新加载历史结果进行分析。

## 批量执行（Task + CLI）

### YAML 配置文件

```yaml
# tasks.yaml
output_dir: results/

tasks:
  - name: math-smoke
    dataset: tests/eval/data/sample.jsonl
    agent: nanobot
    tags: [math]
    concurrency: 2

  - name: geo-claude
    dataset: tests/eval/data/sample.jsonl
    agent: claude-code
    tags: [geo]
    timeout: 180
```

### CLI 工具（`scripts/eval.sh`）

```bash
# 列出 config 中的 task
bash scripts/eval.sh list tasks.yaml

# 运行所有 task
bash scripts/eval.sh run tasks.yaml

# 运行指定 task
bash scripts/eval.sh run tasks.yaml -t math-smoke

# 指定输出目录
bash scripts/eval.sh run tasks.yaml -o my_results/
```

### Python API

```python
from eval import load_tasks, run_tasks
import asyncio

tasks, out_dir = load_tasks("tasks.yaml")
asyncio.run(run_tasks(tasks, out_dir))
```

输出目录结构：
```
results/
├── math-smoke.jsonl
├── math-smoke.report.txt
├── geo-claude.jsonl
├── geo-claude.report.txt
└── summary.txt            # 跨 task 汇总
```

## 扩展点

- **LLM-as-judge**：在 grader 内调用评估模型做语义判断，代替子串匹配
- **多 agent 对比报告**：同一数据集跑多个 agent，diff 成功率
- **CI 集成**：`--tags smoke --limit 5` 快速冒烟测试，`exit 1` on failure
