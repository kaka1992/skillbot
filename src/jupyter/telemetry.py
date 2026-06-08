"""Session event recorder — buffered JSONL writer for data analysis."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class SessionEventRecorder:
    """Buffered per-session event recorder. Events accumulate in memory
    and are flushed as a single JSONL file at session end."""

    def __init__(self, session_id: str, path: str) -> None:
        self._session_id = session_id
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._buffer: list[dict] = []
        self._flushed = False
        self._exec_order = 0
        self._record_event("session_start")

    def _record_event(self, event_type: str, **fields) -> None:
        entry = {
            "session_id": self._session_id,
            "event": event_type,
            "timestamp": datetime.now().isoformat(),
            **fields,
        }
        self._buffer.append(entry)

    def record(self, event_type: str, **fields) -> None:
        """Append an event to the in-memory buffer (no I/O)."""
        if self._flushed:
            return
        try:
            json.dumps(fields, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            fields = {"serialization_error": str(fields)[:500]}
        self._record_event(event_type, **fields)

    def next_exec_order(self) -> int:
        self._exec_order += 1
        return self._exec_order

    def flush(self) -> str | None:
        """Write all buffered events to JSONL. Returns the file path."""
        if self._flushed:
            return None
        self._flushed = True
        self._record_event("session_end", total_events=len(self._buffer))
        try:
            lines = []
            for entry in self._buffer:
                try:
                    lines.append(json.dumps(entry, ensure_ascii=False, default=str))
                except (TypeError, ValueError):
                    lines.append(json.dumps(
                        {"session_id": self._session_id, "event": "serialization_failed"}))
            with open(self._path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            return str(self._path)
        except OSError:
            return None


_recorder: SessionEventRecorder | None = None


def set_recorder(rec: SessionEventRecorder) -> None:
    global _recorder
    _recorder = rec


def get_recorder() -> SessionEventRecorder | None:
    return _recorder
