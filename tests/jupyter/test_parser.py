"""Tests for BlockParser."""

import sys
sys.path.insert(0, "src")

from jupyter.parser import parse


class TestBlockParser:
    def test_text_only(self):
        r = parse("Hello world")
        assert r.text == "Hello world"
        assert r.csv == {}
        assert r.images == []
        assert r.files == {}

    def test_csv_block(self):
        r = parse("text\n```csv:df\nx,y\n1,2\n3,4\n```\nmore")
        assert r.csv == {"df": "x,y\n1,2\n3,4"}
        assert "text" in r.text
        assert "more" in r.text

    def test_csv_without_label_defaults_to_df(self):
        r = parse("```csv\na,b\n1,2\n```")
        assert r.csv == {"df": "a,b\n1,2"}

    def test_image_block(self):
        r = parse("```image\ndGVzdA==\n```")
        assert len(r.images) == 1
        assert r.images[0] == b"test"

    def test_file_block(self):
        r = parse("```file:config.json\n{}\n```")
        assert r.files == {"config.json": "{}"}

    def test_multiple_blocks(self):
        r = parse(
            "intro\n"
            "```csv:data\na,b\n1,2\n```\n"
            "middle\n"
            "```csv:more\nc,d\n3,4\n```\n"
            "outro"
        )
        assert list(r.csv.keys()) == ["data", "more"]
        assert "intro" in r.text
        assert "middle" in r.text
        assert "outro" in r.text

    def test_empty_input(self):
        r = parse("")
        assert r.text == ""

    def test_python_block(self):
        r = parse("code:\n```python\nprint(1)\n```\n")
        assert r.code == "print(1)"

    def test_python_block_between_text(self):
        r = parse("before\n```python\nx=1\n```\nafter")
        assert r.code == "x=1"
        assert "before" in r.text
        assert "after" in r.text
