"""Tests for render_output."""

import sys
sys.path.insert(0, "src")

import pytest
from jupyter.namespace import Namespace
from jupyter.parser import ParsedResult
from jupyter.render import render_output


class FakeShell:
    user_ns: dict = {}
    _next_input: str = ""

    def set_next_input(self, code, replace=False):
        self._next_input = code


class TestRender:
    def test_text_output(self, capsys):
        s = FakeShell()
        r = ParsedResult(text="hello world")
        render_output(s, r)
        assert "hello world" in capsys.readouterr().out

    def test_skip_text(self, capsys):
        s = FakeShell()
        r = ParsedResult(text="hello world")
        render_output(s, r, skip_text=True)
        assert "hello world" not in capsys.readouterr().out

    def test_code_injection(self):
        s = FakeShell()
        r = ParsedResult(code="print(1)")
        render_output(s, r)
        assert s._next_input == "print(1)"

    def test_csv_to_dataframe(self, capsys):
        s = FakeShell()
        ns = Namespace(s)
        r = ParsedResult(csv={"df": "a,b\n1,2\n3,4"})
        render_output(ns, r, skip_text=True)
        assert "df" in s.user_ns
        assert s.user_ns["df"].shape == (2, 2)
        # Backward compat: pass shell directly
        render_output(s, r, skip_text=True)

    def test_file_csv_to_dataframe(self, capsys):
        s = FakeShell()
        ns = Namespace(s)
        r = ParsedResult(files={"data.csv": "x,y\n1,2\n3,4"})
        render_output(ns, r, skip_text=True)
        assert "data" in s.user_ns
        assert s.user_ns["data"].shape == (2, 2)

    def test_file_non_csv(self):
        s = FakeShell()
        ns = Namespace(s)
        r = ParsedResult(files={"notes.txt": "hello"})
        render_output(ns, r, skip_text=True)
        assert s.user_ns["notes.txt"] == "hello"

    def test_python_block_output(self, capsys):
        s = FakeShell()
        r = ParsedResult(text="Here is code.", code="print(1)")
        render_output(s, r, skip_text=True)
        assert s._next_input == "print(1)"

    def test_image_display(self):
        """Image blocks should not crash — display is handled by IPython."""
        import base64
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        s = FakeShell()
        r = ParsedResult(images=[png])
        render_output(s, r, skip_text=True)  # no crash

    def test_multiple_images(self):
        """Multiple images should all be processed."""
        import base64
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        s = FakeShell()
        r = ParsedResult(images=[png, png])
        render_output(s, r, skip_text=True)  # no crash

    def test_invalid_image_handled(self):
        """Malformed base64 images should not crash."""
        s = FakeShell()
        r = ParsedResult(images=[b"not valid image data"])
        render_output(s, r, skip_text=True)  # no crash

    def test_all_blocks_combined(self):
        """Text + code + csv + image + file in one result."""
        import base64
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        s = FakeShell()
        r = ParsedResult(
            text="Analysis complete.",
            code="print('done')",
            csv={"df": "a,b\n1,2\n3,4"},
            images=[png],
            files={"log.txt": "processed 100 rows"},
        )
        render_output(s, r, skip_text=True)
        assert "df" in s.user_ns
        assert s.user_ns["df"].shape == (2, 2)
        assert s.user_ns["log.txt"] == "processed 100 rows"
        assert s._next_input == "print('done')"
