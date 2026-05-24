"""Session event recorder — writes structured JSONL for data analysis."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class TelemetryRecorder:
    def __init__(self, session_id: str, path: str) -> None:
        self._session_id = session_id
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event_type: str, **fields) -> None:
        entry = {"session_id": self._session_id, "event": event_type,
                 "timestamp": datetime.now().isoformat(), **fields}
        try:
            payload = json.dumps(entry, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            payload = json.dumps({"error": "serialization_failed", "event": event_type})
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(payload + "\n")


_recorder: TelemetryRecorder | None = None

def set_recorder(rec: TelemetryRecorder) -> None:
    global _recorder
    _recorder = rec

def get_recorder() -> TelemetryRecorder | None:
    return _recorder
