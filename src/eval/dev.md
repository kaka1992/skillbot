# Eval — Agent 评测框架

## 设计目标

异步优先、JSONL 驱动的 agent 评测框架。通过 `chat` 模块的统一接口，
对任意 agent 运行评测数据集，支持并发控制、自动评分、结果持久化。

## 文件结构

```
src/eval/
├── __init__.py    # AsyncEvalRunner, EvalDataset, EvalResult
├── loader.py      # JSONL 数据集加载器
├── runner.py      # 异步评测运行器（asyncio.Semaphore 并发）
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
| `expected` | — | 期望答案，auto_grade 时子串匹配 |
| `tags` | — | 标签，OR 逻辑过滤 |
| 其他 | — | 存入 `extra`，透传到结果 |

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
    auto_grade=True,    # expected 子串匹配 answer
)

async for result in runner.run(ds):
    ...
```

### 运行流程

```
dataset 逐条 → asyncio.Semaphore(concurrency) 限流
  │
  ├── 并发调用 chat_fn(question) → answer
  ├── 异常捕获 → error
  ├── auto_grade → expected in answer.lower()
  ├── 计时 elapsed
  ├── 打印进度 [i/total] id (OK/ERR/--) elapsed
  └── yield EvalResult
```

## 使用示例

```python
import asyncio
from eval import EvalDataset, AsyncEvalRunner
from chat import ChatClient

async def main():
    c = ChatClient("nanobot")
    ds = EvalDataset("questions.jsonl", tags=["easy"], limit=20)

    runner = AsyncEvalRunner(
        lambda q: c.async_chat(q, session="eval"),
        concurrency=5,
        auto_grade=True,
    )

    async for r in runner.run(ds):
        pass  # 进度已在 runner 内打印

    print(runner.report())
    # Eval Report (20 items)
    #   Passed:  18
    #   Failed:  2
    #   Errors:  0
    #   Avg time: 1.5s
    #   Accuracy: 90.0%

    runner.save("results.jsonl")

asyncio.run(main())
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

```jsonl
{"id": "q1", "question": "1+1=?", "expected": "2", "answer": "2", "success": true, "elapsed": 1.2, "tags": ["math"], "error": "", "eval_date": "2026-05-04 20:00:00"}
```

可直接用 `EvalDataset` 重新加载历史结果进行分析。

## 扩展点

- **自定义评分**：传入 `grade_fn(answer, expected) -> bool` 替代子串匹配
- **多 agent 对比**：同一数据集跑多个 runner，对比 stats
- **CI 集成**：`--tags smoke --limit 5` 快速冒烟测试
