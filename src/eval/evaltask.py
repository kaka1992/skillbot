"""Task-based batch eval runner with YAML config support."""

import asyncio
import importlib
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from .runner import AsyncEvalRunner, GraderFn, default_grader

# -- grader registry ---------------------------------------------------

_GRADER_REGISTRY: dict[str, GraderFn] = {
    "default": default_grader,
}


def register_grader(name: str, fn: GraderFn) -> None:
    """Register a named grader for use in YAML config ``grader: <name>``."""
    _GRADER_REGISTRY[name] = fn


def resolve_grader(spec: str) -> GraderFn:
    """Resolve a grader name or ``module.path:fn`` import string."""
    # check registry first
    if spec in _GRADER_REGISTRY:
        return _GRADER_REGISTRY[spec]

    # dynamic import: "pkg.module:func_name"
    if ":" in spec:
        mod_path, fn_name = spec.rsplit(":", 1)
        try:
            mod = importlib.import_module(mod_path)
        except ImportError as e:
            raise ValueError(f"Cannot import '{mod_path}': {e}") from e
        fn = getattr(mod, fn_name, None)
        if fn is None:
            raise ValueError(
                f"Function '{fn_name}' not found in module '{mod_path}'"
            )
        if not callable(fn):
            raise ValueError(f"'{spec}' is not callable")
        return fn

    raise ValueError(
        f"Unknown grader '{spec}'. "
        f"Use register_grader('{spec}', fn) or 'module.path:fn' import syntax."
    )


# -- EvalTask ----------------------------------------------------------


@dataclass
class EvalTask:
    """Configuration for a single eval run."""

    name: str
    dataset: str
    agent: str = "nanobot"
    model: str | None = None
    tags: list[str] | None = None
    limit: int | None = None
    shuffle: bool = False
    concurrency: int = 5
    timeout: int = 120
    output: str | None = None
    grader: str | None = None  # grader name or module.path:fn
    trace: bool = False  # enable trace collection (thinking + tool_use + subagent + usage)

    def output_path(self, output_dir: str) -> Path:
        return Path(output_dir) / f"{self.name}.jsonl"

    def get_grader(self) -> GraderFn | None:
        """Resolve grader from name, or None to disable."""
        if self.grader is None:
            return default_grader
        if self.grader == "none":
            return None
        return resolve_grader(self.grader)


# -- load / run --------------------------------------------------------


def load_tasks(path: str) -> tuple[list[EvalTask], str]:
    """Load task list and output_dir from a YAML config file.

    Returns (tasks, output_dir).
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "tasks" not in data:
        raise ValueError(f"No 'tasks' key found in {path}")

    output_dir = data.get("output_dir", "results")
    tasks = []
    for entry in data["tasks"]:
        tasks.append(
            EvalTask(
                name=entry["name"],
                dataset=entry["dataset"],
                agent=entry.get("agent", "nanobot"),
                model=entry.get("model"),
                tags=entry.get("tags"),
                limit=entry.get("limit"),
                shuffle=entry.get("shuffle", False),
                concurrency=entry.get("concurrency", 5),
                timeout=entry.get("timeout", 120),
                output=entry.get("output"),
                grader=entry.get("grader"),
                trace=entry.get("trace", False),
            )
        )
    return tasks, output_dir


async def run_tasks(tasks: list[EvalTask], output_dir: str = "results") -> None:
    """Run a list of EvalTasks sequentially, saving results per task."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for task in tasks:
        print(f"\n{'='*60}")
        print(f"  Task: {task.name}")
        print(f"  Agent: {task.agent} | Dataset: {task.dataset}")
        grader_name = task.grader or "default"
        print(f"  Grader: {grader_name}")
        print(f"{'='*60}")

        # build chat_fn
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from chat import ChatClient  # noqa: E402

        client = ChatClient(task.agent, model=task.model, timeout=task.timeout)

        if task.trace:
            from .trace import TraceCollector  # noqa: E402

            async def _chat(q: str):
                collector = TraceCollector()
                parts: list[str] = []
                for chunk in client._backend.stream_chunks(
                    q, session=f"eval-{task.name}"
                ):
                    collector.feed(chunk)
                    if chunk.text:
                        parts.append(chunk.text)
                trace_data = collector.to_dict()
                return "".join(parts), (trace_data if trace_data else None)
        else:
            async def _chat(q: str) -> str:
                return await client.async_chat(q, session=f"eval-{task.name}")

        # build dataset
        from .loader import EvalDataset  # noqa: E402

        ds = EvalDataset(
            task.dataset,
            tags=task.tags,
            limit=task.limit,
            shuffle=task.shuffle,
        )

        # run
        grader = task.get_grader()
        runner = AsyncEvalRunner(
            _chat,
            concurrency=task.concurrency,
            grader=grader,
            trace=task.trace,
        )
        async for _result in runner.run(ds):
            pass  # progress printed by runner

        # save
        output_path = task.output_path(output_dir)
        runner.save(str(output_path))

    # write summary
    _write_summary(out)


def _write_summary(output_dir: Path) -> None:
    lines = [
        f"Eval Summary — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]
    for report_file in sorted(output_dir.glob("*.report.txt")):
        lines.append(report_file.read_text(encoding="utf-8"))
        lines.append("")

    summary_text = "\n".join(lines)
    summary_path = output_dir / "summary.txt"
    summary_path.write_text(summary_text, encoding="utf-8")
    print(f"\n{summary_text}")


def load_and_run(path: str, output_dir: str | None = None) -> None:
    """Load tasks from YAML and run them. Called by eval.sh CLI."""
    tasks, cfg_out = load_tasks(path)
    out = output_dir or cfg_out
    asyncio.run(run_tasks(tasks, out))
