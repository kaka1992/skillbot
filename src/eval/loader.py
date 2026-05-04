"""JSONL dataset loader for agent evaluation."""

import json
import random
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class EvalItem:
    """A single evaluation item."""

    id: str
    question: str
    expected: str = ""
    tags: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


class EvalDataset:
    """Load and filter a JSONL evaluation dataset.

    File format (one JSON object per line, ``#`` for comments)::

        {"id": "q1", "question": "1+1=?", "expected": "2", "tags": ["math"]}
        {"id": "q2", "question": "Say hello", "expected": "hello"}

    Usage::

        ds = EvalDataset("questions.jsonl")
        ds = EvalDataset("questions.jsonl", tags=["math"], limit=10, shuffle=True)
        for item in ds:
            print(item.id, item.question)
    """

    def __init__(
        self,
        path: str | Path,
        *,
        tags: Optional[list[str]] = None,
        limit: Optional[int] = None,
        shuffle: bool = False,
        seed: int = 42,
    ) -> None:
        self._path = Path(path)
        self._items: list[EvalItem] = []
        self._load()

        if tags:
            tag_set = set(tags)
            self._items = [i for i in self._items if tag_set & set(i.tags)]

        if shuffle:
            rng = random.Random(seed)
            rng.shuffle(self._items)

        if limit is not None:
            self._items = self._items[:limit]

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"Dataset not found: {self._path}")
        with open(self._path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Invalid JSON at {self._path}:{lineno}: {e}"
                    ) from e
                self._items.append(
                    EvalItem(
                        id=obj.get("id", str(lineno)),
                        question=obj["question"],
                        expected=obj.get("expected", ""),
                        tags=obj.get("tags", []),
                        extra={
                            k: v
                            for k, v in obj.items()
                            if k not in ("id", "question", "expected", "tags")
                        },
                    )
                )

    @property
    def tags(self) -> list[str]:
        seen: set[str] = set()
        for item in self._items:
            seen.update(item.tags)
        return sorted(seen)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[EvalItem]:
        yield from self._items

    def __getitem__(self, idx: int) -> EvalItem:
        return self._items[idx]

    def __repr__(self) -> str:
        return f"EvalDataset({self._path.name}, {len(self)} items)"
