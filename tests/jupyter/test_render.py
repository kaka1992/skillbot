"""Tests for render_output / render_code."""

import sys
sys.path.insert(0, "src")

from unittest.mock import patch

import pytest
from jupyter.namespace import Namespace
from jupyter.parser import ParsedResult
from jupyter.render import render_code, render_output


class FakeKernel:
    comm_manager = True


class FakeShell:
    user_ns: dict = {}
    kernel = FakeKernel()
    parent_header = {}


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

    def test_code_sent_via_comm(self):
        ns = Namespace(FakeShell())
        with patch("jupyter.comm.send_cell_via_comm") as mock:
            mock.return_value = True
            render_code(ns, "print(1)", auto=True)
            mock.assert_called_once()
            assert "print(1)" in mock.call_args[0][1]
            assert mock.call_args[1]["auto"] is True

    def test_code_auto_false(self):
        ns = Namespace(FakeShell())
        with patch("jupyter.comm.send_cell_via_comm") as mock:
            mock.return_value = True
            render_code(ns, "print(1)", auto=False)
            assert mock.call_args[1]["auto"] is False

    def test_code_trace(self):
        ns = Namespace(FakeShell())
        with patch("jupyter.comm.send_cell_via_comm") as mock:
            mock.return_value = True
            render_code(ns, "print(1)", trace=True)
            code = mock.call_args[0][1]
            assert "%agent --trace" in code

    def test_code_trace_auto(self):
        ns = Namespace(FakeShell())
        with patch("jupyter.comm.send_cell_via_comm") as mock:
            mock.return_value = True
            render_code(ns, "print(1)", auto=True, trace=True)
            assert "%agent --trace --auto" in mock.call_args[0][1]

    def test_code_format_magic_prefix(self):
        ns = Namespace(FakeShell())
        with patch("jupyter.comm.send_cell_via_comm") as mock:
            mock.return_value = True
            render_code(ns, "x = 1")
            assert "# %%agent generate code" in mock.call_args[0][1]

    def test_empty_code_skipped(self):
        ns = Namespace(FakeShell())
        with patch("jupyter.comm.send_cell_via_comm") as mock:
            render_code(ns, "")
            mock.assert_not_called()

    def test_csv_to_dataframe(self, capsys):
        s = FakeShell()
        ns = Namespace(s)
        r = ParsedResult(csv={"df": "a,b\n1,2\n3,4"})
        render_output(ns, r)
        assert "df" in s.user_ns
        assert s.user_ns["df"].shape == (2, 2)

    def test_file_csv_to_dataframe(self, capsys):
        s = FakeShell()
        ns = Namespace(s)
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("x,y\n1,2\n3,4")
            tmp = f.name
        try:
            r = ParsedResult(files=[tmp])
            render_output(ns, r)
            stem = os.path.basename(tmp).rsplit(".", 1)[0]
            assert stem in s.user_ns
            assert s.user_ns[stem].shape == (2, 2)
        finally:
            os.unlink(tmp)

    def test_file_non_csv(self):
        import tempfile, os
        s = FakeShell()
        ns = Namespace(s)
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("hello")
            tmp = f.name
        try:
            r = ParsedResult(files=[tmp])
            render_output(ns, r)
            assert tmp in s.user_ns
            assert s.user_ns[tmp] == "hello"
        finally:
            os.unlink(tmp)

    def test_multi_code_sends_multiple_comms(self):
        ns = Namespace(FakeShell())
        with patch("jupyter.comm.send_cell_via_comm") as mock:
            mock.return_value = True
            render_output(ns, ParsedResult(code_list=["a=1", "b=2"]))
            assert mock.call_count == 2

    def test_multi_code_trace_last_only(self):
        ns = Namespace(FakeShell())
        with patch("jupyter.comm.send_cell_via_comm") as mock:
            mock.return_value = True
            render_output(ns, ParsedResult(code_list=["a=1", "b=2"]), trace=True)
            # First call: no trace
            assert "%agent --trace" not in mock.call_args_list[0][0][1]
            # Second call: trace appended
            assert "%agent --trace" in mock.call_args_list[1][0][1]

    def test_image_display(self):
        import base64
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        s = FakeShell()
        r = ParsedResult(images=[png])
        render_output(Namespace(s), r)  # no crash

    def test_multiple_images(self):
        import base64
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        s = FakeShell()
        r = ParsedResult(images=[png, png])
        render_output(Namespace(s), r)  # no crash

    def test_invalid_image_handled(self):
        s = FakeShell()
        r = ParsedResult(images=[b"not valid image data"])
        render_output(Namespace(s), r)  # no crash

    def test_image_file_not_injected(self):
        s = FakeShell()
        r = ParsedResult(files=['chart.png'])
        render_output(Namespace(s), r)
        assert "chart.png" not in s.user_ns

    def test_image_file_inline_fallback(self):
        s = FakeShell()
        r = ParsedResult(files=['chart.png'])
        render_output(Namespace(s), r)  # no crash

    def test_csv_file_label_path(self):
        import tempfile, os
        s = FakeShell()
        ns = Namespace(s)
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("x,y\n1,2\n3,4")
            tmp = f.name
        try:
            r = ParsedResult(files=[tmp])
            render_output(ns, r)
            stem = os.path.basename(tmp).rsplit(".", 1)[0]
            assert stem in s.user_ns
            assert s.user_ns[stem].shape == (2, 2)
        finally:
            os.unlink(tmp)

    def test_generic_file_label_path(self):
        import tempfile, os
        s = FakeShell()
        ns = Namespace(s)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello from disk")
            tmp = f.name
        try:
            r = ParsedResult(files=[tmp])
            render_output(ns, r)
            assert tmp in s.user_ns
            assert s.user_ns[tmp] == "hello from disk"
        finally:
            os.unlink(tmp)


class TestDisplayImage:
    """Unit tests for _display_image_file."""

    def test_disk_path(self):
        import tempfile, os, base64
        from jupyter.render import _display_image_file
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png)
            tmp = f.name
        try:
            _display_image_file("chart.png", tmp)
        finally:
            os.unlink(tmp)

    def test_inline_base64(self):
        from jupyter.render import _display_image_file
        _display_image_file("chart.png", "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")  # no crash

    def test_invalid_path_fallback_to_base64(self):
        from jupyter.render import _display_image_file
        _display_image_file("chart.png", "/nonexistent/path.png")  # no crash

    def test_empty_content(self):
        from jupyter.render import _display_image_file
        _display_image_file("chart.png", "")  # no crash

class TestRenderMarkdown:
    def test_render_markdown_output(self, capsys):
        """render_markdown generates no stdout — uses IPython display."""
        from jupyter.render import render_markdown

        render_markdown("## Hello\ncontent")  # no crash
        out = capsys.readouterr().out
        assert "## Hello" not in out  # goes to display, not stdout

    def test_render_markdown_empty(self, capsys):
        from jupyter.render import render_markdown

        render_markdown("")  # no crash
        render_markdown("   ")  # no crash


class TestRenderOutputMarkdown:
    def test_is_markdown_true_routes_to_markdown(self, capsys):
        from jupyter.namespace import Namespace
        from jupyter.parser import ParsedResult
        from jupyter.render import render_output

        s = type("Shell", (), {"user_ns": {}, "set_next_input": lambda *a: None})()
        r = ParsedResult(text="## Hello\nworld", is_markdown=True)
        render_output(Namespace(s), r)
        out = capsys.readouterr().out
        assert "## Hello" not in out  # routed to display, not stdout

    def test_is_markdown_false_routes_to_text(self, capsys):
        from jupyter.namespace import Namespace
        from jupyter.parser import ParsedResult
        from jupyter.render import render_output

        s = type("Shell", (), {"user_ns": {}, "set_next_input": lambda *a: None})()
        r = ParsedResult(text="hello world", is_markdown=False)
        render_output(Namespace(s), r)
        out = capsys.readouterr().out
        assert "hello world" in out  # routed to print


    def test_label_as_path(self, capsys):
        import tempfile, os, base64
        from jupyter.render import _display_image_file
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png)
            tmp = f.name
        try:
            _display_image_file(tmp, "")
            out = capsys.readouterr().out
            assert "image displayed" in out
        finally:
            os.unlink(tmp)
