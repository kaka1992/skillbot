import json, sys, tempfile, os
sys.path.insert(0, "src")

from jupyter.telemetry import TelemetryRecorder, set_recorder, get_recorder


class TestTelemetryRecorder:
    def test_record_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.jsonl")
            rec = TelemetryRecorder("abc123", path)
            rec.record("cell_executed", cell_id="c1", type="plain", code="1+1",
                       output="2", error=None, elapsed=0.1)
            with open(path) as f:
                line = f.readline()
            data = json.loads(line)
            assert data["event"] == "cell_executed"
            assert data["session_id"] == "abc123"
            assert "timestamp" in data

    def test_multiple_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.jsonl")
            rec = TelemetryRecorder("s1", path)
            rec.record("cell_executed", cell_id="c1")
            rec.record("feedback", result="yes")
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 2

    def test_non_serializable_handled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.jsonl")
            rec = TelemetryRecorder("s1", path)
            rec.record("cell_executed", cell_id="c1", extra=set([1,2,3]))  # no crash


class TestRecorderGlobal:
    def test_set_and_get(self):
        rec = TelemetryRecorder("x", "/tmp/x.jsonl")
        set_recorder(rec)
        assert get_recorder() is rec

    def test_get_none(self):
        import jupyter.telemetry as t
        t._recorder = None
        assert get_recorder() is None
