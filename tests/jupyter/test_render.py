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
        render_output(Namespace(s), r)
        assert "hello world" in capsys.readouterr().out

    def test_skip_text(self, capsys):
        s = FakeShell()
        r = ParsedResult(text="hello world")
        render_output(Namespace(s), r, skip_text=True)
        assert "hello world" not in capsys.readouterr().out

    def test_code_injection(self):
        s = FakeShell()
        r = ParsedResult(code="print(1)")
        render_output(Namespace(s), r, inject_code=True)
        assert "print(1)" in s._next_input

    def test_code_not_injected_without_flag(self):
        s = FakeShell()
        r = ParsedResult(code="print(1)")
        render_output(Namespace(s), r)
        assert s._next_input == ""  # not injected

    def test_csv_to_dataframe(self, capsys):
        s = FakeShell()
        ns = Namespace(s)
        r = ParsedResult(csv={"df": "a,b\n1,2\n3,4"})
        render_output(ns, r, skip_text=True)
        assert "df" in s.user_ns
        assert s.user_ns["df"].shape == (2, 2)

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
        render_output(Namespace(s), r, skip_text=True, inject_code=True)
        assert "print(1)" in s._next_input

    def test_image_display(self):
        """Image blocks should not crash — display is handled by IPython."""
        import base64
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        s = FakeShell()
        r = ParsedResult(images=[png])
        render_output(Namespace(s), r, skip_text=True)  # no crash

    def test_multiple_images(self):
        """Multiple images should all be processed."""
        import base64
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        s = FakeShell()
        r = ParsedResult(images=[png, png])
        render_output(Namespace(s), r, skip_text=True)  # no crash

    def test_invalid_image_handled(self):
        """Malformed base64 images should not crash."""
        s = FakeShell()
        r = ParsedResult(images=[b"not valid image data"])
        render_output(Namespace(s), r, skip_text=True)  # no crash

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
        render_output(Namespace(s), r, skip_text=True, inject_code=True)
        assert "df" in s.user_ns
        assert s.user_ns["df"].shape == (2, 2)
        assert s.user_ns["log.txt"] == "processed 100 rows"
        assert "# %%agent code" in s._next_input
        assert "print('done')" in s._next_input

    def test_image_file_not_injected(self):
        """Image files (.png) are displayed, not injected into namespace."""
        import tempfile, os
        s = FakeShell()
        # Create a real temp PNG file
        import base64
        png_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png_data)
            tmp = f.name
        try:
            r = ParsedResult(files={"chart.png": tmp})
            render_output(Namespace(s), r, skip_text=True)
            assert "chart.png" not in s.user_ns  # displayed, not injected
            assert "chart" not in s.user_ns      # no stripped name either
        finally:
            os.unlink(tmp)

    def test_image_file_inline_fallback(self):
        """Image files with inline base64 content fall back to display."""
        s = FakeShell()
        r = ParsedResult(files={"chart.png": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="})
        render_output(Namespace(s), r, skip_text=True)  # no crash
        assert "chart.png" not in s.user_ns
        assert "chart" not in s.user_ns

    def test_csv_file_label_path(self, capsys):
        """CSV file block: path in label, body empty — load from name path."""
        import tempfile, os
        s = FakeShell()
        ns = Namespace(s)
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("x,y\n1,2\n3,4")
            tmp = f.name
        try:
            r = ParsedResult(files={tmp: ""})  # name=real path, content=""
            render_output(ns, r, skip_text=True)
            # var_name = path.stem, injected into namespace
            stem = os.path.basename(tmp).rsplit(".", 1)[0]
            assert stem in s.user_ns
            assert s.user_ns[stem].shape == (2, 2)
        finally:
            os.unlink(tmp)

    def test_generic_file_label_path(self, capsys):
        """Generic file block: path in label, body empty — read from name path."""
        import tempfile, os
        s = FakeShell()
        ns = Namespace(s)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello from disk")
            tmp = f.name
        try:
            r = ParsedResult(files={tmp: ""})  # name=real path, content=""
            render_output(ns, r, skip_text=True)
            assert tmp in s.user_ns
            assert s.user_ns[tmp] == "hello from disk"
        finally:
            os.unlink(tmp)


class TestDisplayImage:
    """Unit tests for _display_image."""

    def test_disk_path(self):
        import tempfile, os, base64
        from jupyter.render import _display_image
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png)
            tmp = f.name
        try:
            _display_image("chart.png", tmp)  # should not crash
        finally:
            os.unlink(tmp)

    def test_inline_base64(self):
        from jupyter.render import _display_image
        _display_image("chart.png", "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")  # no crash

    def test_invalid_path_fallback_to_base64(self):
        from jupyter.render import _display_image
        _display_image("chart.png", "/nonexistent/path.png")  # no crash, tries inline

    def test_empty_content(self):
        from jupyter.render import _display_image
        _display_image("chart.png", "")  # no crash

    def test_label_as_path(self, capsys):
        """When content is empty, use name (label) as file path."""
        import tempfile, os, base64
        from jupyter.render import _display_image
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png)
            tmp = f.name
        try:
            _display_image(tmp, "")  # name=tmp (real path), content=""
            out = capsys.readouterr().out
            assert "image displayed" in out
        finally:
            os.unlink(tmp)
