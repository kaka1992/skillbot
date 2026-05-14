"""Tests for BlockParser — JSON format."""

import sys
sys.path.insert(0, "src")

import pytest
from jupyter.parser import parse, ParsedResult


class TestJsonParser:
    def test_all_fields(self):
        r = parse("""```json
{"text": "Here is the result", "files": ["/tmp/chart.png", "/tmp/data.csv"], "code": "print(1)"}
```""")
        assert r.text == "Here is the result"
        assert r.files == {"/tmp/chart.png": "/tmp/chart.png", "/tmp/data.csv": "/tmp/data.csv"}
        assert r.code == "print(1)"

    def test_text_only(self):
        r = parse("""```json
{"text": "hello world"}
```""")
        assert r.text == "hello world"
        assert r.files == {}
        assert r.code == ""

    def test_files_only(self):
        r = parse("""```json
{"files": ["/tmp/data.csv"]}
```""")
        assert r.text == ""
        assert r.files == {"/tmp/data.csv": "/tmp/data.csv"}
        assert r.code == ""

    def test_code_only(self):
        r = parse("""```json
{"code": "x = 1 + 1"}
```""")
        assert r.text == ""
        assert r.files == {}
        assert r.code == "x = 1 + 1"

    def test_empty_json(self):
        r = parse("""```json
{}
```""")
        assert r.text == ""
        assert r.files == {}
        assert r.code == ""

    def test_no_json_block(self):
        with pytest.raises(ValueError, match="No JSON block found"):
            parse("hello world, no json here")

    def test_invalid_json(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse("""```json
{broken json!!!
```""")

    def test_empty_input(self):
        with pytest.raises(ValueError, match="No JSON block found"):
            parse("")

    def test_text_outside_block_is_ignored(self):
        """Only JSON block content is used; surrounding text is ignored."""
        r = parse("""some preamble
```json
{"text": "the real answer"}
```
some trailing text""")
        assert r.text == "the real answer"

    def test_multiple_files(self):
        r = parse("""```json
{"files": ["/tmp/a.png", "/tmp/b.csv", "/tmp/c.txt"]}
```""")
        assert len(r.files) == 3
        assert r.files["/tmp/a.png"] == "/tmp/a.png"

    def test_text_with_newlines(self):
        r = parse("""```json
{"text": "line 1\\n\\nline 2"}
```""")
        assert r.text == "line 1\n\nline 2"
