"""Tests for SessionEventRecorder."""
import json
import tempfile
from pathlib import Path

import pytest
from jupyter.telemetry import SessionEventRecorder, set_recorder, get_recorder


class TestSessionEventRecorder:
    def test_record_buffers_in_memory(self):
        rec = SessionEventRecorder("test-session", "/tmp/test-telemetry.jsonl")
        rec.record("cell_executed", cell_id="abc", code="print(1)")
        rec.record("cell_executed", cell_id="def", code="print(2)")
        assert len(rec._buffer) == 3  # session_start + 2 events

    def test_flush_writes_jsonl(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            rec = SessionEventRecorder("test-session", path)
            rec.record("cell_executed", cell_id="abc", code="print(1)")
            result = rec.flush()
            assert result == path
            assert Path(path).exists()
            lines = Path(path).read_text().strip().split("\n")
            assert len(lines) == 3  # session_start + cell_executed + session_end
            for line in lines:
                obj = json.loads(line)
                assert obj["session_id"] == "test-session"
                assert "event" in obj
                assert "timestamp" in obj
            assert lines[1] != lines[0]
        finally:
            Path(path).unlink(missing_ok=True)

    def test_double_flush_is_noop(self):
        rec = SessionEventRecorder("s", "/tmp/t2.jsonl")
        rec.record("cell_executed", cell_id="x", code="")
        rec.flush()
        result = rec.flush()
        assert result is None

    def test_record_after_flush_is_noop(self):
        rec = SessionEventRecorder("s", "/tmp/t3.jsonl")
        rec.flush()
        rec.record("cell_executed", cell_id="x", code="")
        assert len(rec._buffer) == 2  # session_start + session_end only

    def test_next_exec_order(self):
        rec = SessionEventRecorder("s", "/tmp/t4.jsonl")
        assert rec.next_exec_order() == 1
        assert rec.next_exec_order() == 2
        assert rec.next_exec_order() == 3
