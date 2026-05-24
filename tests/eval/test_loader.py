"""Tests for EvalDataset."""

import os
import tempfile

import pytest

_DATA = os.path.join(os.path.dirname(__file__), "data", "sample.jsonl")


class TestEvalDataset:
    def test_load_count(self):
        from eval import EvalDataset

        ds = EvalDataset(_DATA)
        assert len(ds) == 10  # 10 entries, comment + blank lines skipped

    def test_fields(self):
        from eval import EvalDataset

        ds = EvalDataset(_DATA)
        assert ds[0].id == "math-1"
        assert ds[0].question.startswith("What is 1+1?")
        assert ds[0].expected == "2"
        assert "math" in ds[0].tags

    def test_extra_field(self):
        """Extra keys beyond id/question/expected/tags go to EvalItem.extra."""
        from eval import EvalDataset

        ds = EvalDataset(_DATA, tags=["geo", "medium"])
        geo = [i for i in ds if i.id == "geo-1"][0]
        assert geo.extra == {"min_score": 0.8, "references": ["Paris", "paris"]}

    def test_tags(self):
        from eval import EvalDataset

        ds = EvalDataset(_DATA)
        assert set(ds.tags) >= {"math", "lang", "geo", "trick", "tool",
                                "easy", "medium", "hard"}

    def test_filter_by_tags(self):
        from eval import EvalDataset

        ds = EvalDataset(_DATA, tags=["math"])
        assert len(ds) == 2
        assert all("math" in i.tags for i in ds)

    def test_filter_or(self):
        from eval import EvalDataset

        ds = EvalDataset(_DATA, tags=["math", "geo"])
        assert len(ds) == 4

    def test_limit(self):
        from eval import EvalDataset

        ds = EvalDataset(_DATA, limit=3)
        assert len(ds) == 3

    def test_limit_with_tags(self):
        from eval import EvalDataset

        ds = EvalDataset(_DATA, tags=["tool"], limit=2)
        assert len(ds) == 2
        assert all("tool" in i.tags for i in ds)

    def test_shuffle_reproducible(self):
        from eval import EvalDataset

        a = [i.id for i in EvalDataset(_DATA, shuffle=True, seed=42)]
        b = [i.id for i in EvalDataset(_DATA, shuffle=True, seed=42)]
        assert a == b

    def test_shuffle_different(self):
        from eval import EvalDataset

        a = [i.id for i in EvalDataset(_DATA, shuffle=True, seed=1)]
        b = [i.id for i in EvalDataset(_DATA, shuffle=True, seed=99)]
        assert a != b

    def test_shuffle_limit_samples(self):
        from eval import EvalDataset

        ds = EvalDataset(_DATA, shuffle=True, limit=3, seed=42)
        assert len(ds) == 3

    def test_file_not_found(self):
        from eval import EvalDataset

        with pytest.raises(FileNotFoundError):
            EvalDataset("/nonexistent/path.jsonl")

    def test_missing_question_key_raises(self):
        from eval import EvalDataset

        with tempfile.NamedTemporaryFile(
            suffix=".jsonl", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write('{"id": "bad", "expected": "x"}\n')
            tmp = f.name
        try:
            with pytest.raises(KeyError):
                EvalDataset(tmp)
        finally:
            os.unlink(tmp)

    def test_invalid_json_raises(self):
        from eval import EvalDataset

        with tempfile.NamedTemporaryFile(
            suffix=".jsonl", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write("not valid json!!!\n")
            tmp = f.name
        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                EvalDataset(tmp)
        finally:
            os.unlink(tmp)

    def test_repr(self):
        from eval import EvalDataset

        ds = EvalDataset(_DATA, tags=["math"])
        r = repr(ds)
        assert "EvalDataset" in r
        assert "2 items" in r

    def test_getitem_out_of_bounds(self):
        from eval import EvalDataset

        ds = EvalDataset(_DATA)
        with pytest.raises(IndexError):
            _ = ds[len(ds)]
