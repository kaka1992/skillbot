"""Tests for parser — cascading fallback: JSON fenced → raw JSON → code fenced → raw text."""

import sys
sys.path.insert(0, "src")

import pytest
from jupyter.parser import parse


def _p(text):
    return parse(text)


# ============================================================
# JSON fenced
# ============================================================

class TestJsonFenced:
    def test_all_fields(self):
        r = _p('```json\n{"text": "ok", "files": ["a.csv"], "code": "print(1)"}\n```')
        assert r.text == "ok"
        assert r.files == ["a.csv"]
        assert r.code_list == ["print(1)"]

    def test_code_array(self):
        r = _p('```json\n{"code": ["a=1", "b=2"]}\n```')
        assert r.code_list == ["a=1", "b=2"]

    def test_code_array_skips_empties(self):
        r = _p('```json\n{"code": ["a=1", "", "  ", "b=2"]}\n```')
        assert r.code_list == ["a=1", "b=2"]

    def test_surrounding_ignored(self):
        r = _p('preamble\n```json\n{"text": "inner"}\n```\npost')
        assert r.text == "inner"

    def test_fenced_over_raw(self):
        r = _p('```json\n{"text": "fenced"}\n```\n{"text": "raw"}')
        assert r.text == "fenced"

    def test_newlines_in_text(self):
        r = _p('```json\n{"text": "line 1\\n\\nline 2"}\n```')
        assert r.text == "line 1\n\nline 2"

    def test_escaped_quotes(self):
        r = _p('```json\n{"text": "say \\"hi\\""}\n```')
        assert r.text == 'say "hi"'

    def test_unicode(self):
        r = _p('```json\n{"text": "你好世界"}\n```')
        assert r.text == "你好世界"

    @pytest.mark.parametrize("content,field,expected", [
        ('{"text": "hi"}', "text", "hi"),
        ('{"files": ["a.csv"]}', "files", ["a.csv"]),
        ('{"code": "x = 1"}', "code_list", ["x = 1"]),
        ('{}', "text", ""),
    ])
    def test_field_variants(self, content, field, expected):
        r = _p('```json\n' + content + '\n```')
        if field == "code_list":
            assert r.code_list == expected
        else:
            assert getattr(r, field) == expected


# ============================================================
# Raw JSON
# ============================================================

class TestRawJson:
    def test_basic(self):
        r = _p('{"text": "hi", "code": "x = 1"}')
        assert r.text == "hi"
        assert r.code_list == ["x = 1"]

    def test_surrounding_whitespace(self):
        r = _p('\n\n  {"code": "x = 1"}  \n')
        assert r.code_list == ["x = 1"]

    def test_array_not_parsed(self):
        r = _p('[{"text": "nope"}]')
        assert r.text == '[{"text": "nope"}]'


# ============================================================
# Code fence
# ============================================================

class TestCodeFence:
    def test_python_fence(self):
        r = _p("explain:\n\n```python\nprint(1)\n```")
        assert r.code_list == ["print(1)"]
        assert "explain" in r.text

    def test_bare_fence(self):
        r = _p("```\nx = 1\n```")
        assert r.code_list == ["x = 1"]

    def test_multiple(self):
        r = _p("before\n```python\na = 1\n```\nmiddle\n```\nb = 2\n```\nafter")
        assert r.code_list == ["a = 1", "b = 2"]
        assert "before" in r.text
        assert "middle" in r.text
        assert "after" in r.text

    def test_json_fence_not_captured(self):
        r = _p('```json\n{"text": "hi"}\n```')
        assert r.text == "hi"
        assert r.code_list == []

    def test_bare_fence_after_lang_fence(self):
        """Closing ``` of bash block acts as bare opening fence for next block."""
        r = _p("```bash\necho hi\n```\n```sql\nselect 1\n```")
        # closing ``` of bash block → bare fence opening; captures ```sql + content
        assert len(r.code_list) == 1

    def test_empty_block(self):
        r = _p("```python\n\n```")
        assert r.code_list == [""]

    def test_unclosed_ignored(self):
        r = _p("```python\nprint(1)")
        assert r.code_list == []
        assert "```python" in r.text

    def test_indented_is_text(self):
        r = _p("  ```python\n  print(1)\n  ```")
        assert r.code_list == []

    def test_only_text_between_fences(self):
        r = _p("```python\na = 1\n```\njust text, no second fence")
        assert r.code_list == ["a = 1"]
        assert "just text" in r.text


# ============================================================
# Invalid JSON → fallback
# ============================================================

class TestInvalidJsonFallback:
    def test_invalid_fenced_to_raw(self):
        r = _p("```json\n{broken\n```")
        assert r.code_list == []

    def test_invalid_fenced_with_code(self):
        """Invalid JSON → fallback; closing ``` of json block acts as bare fence."""
        r = _p("```json\n{broken\n```\n\n```python\nx = 1\n```")
        assert len(r.code_list) > 0  # finds at least one code block

    def test_invalid_raw_to_raw(self):
        r = _p("{broken json")
        assert len(r.text) > 0


# ============================================================
# Raw text
# ============================================================

class TestRawText:
    def test_plain(self):
        assert _p("hello world").text == "hello world"

    def test_empty(self):
        assert _p("").text == ""

    def test_markdown(self):
        r = _p("# Title\n\n**bold**\n\n- item")
        assert r.text == "# Title\n\n**bold**\n\n- item"

    def test_realistic_agent_output(self):
        r = _p("""Analysis:

```python
import pandas as pd
df = pd.read_csv('data.csv')
print(df.describe())
```

Summary statistics above.""")
        assert len(r.code_list) == 1
        assert "import pandas" in r.code_list[0]
        assert "Analysis" in r.text
        assert "Summary" in r.text


# ============================================================
# Regression
# ============================================================

class TestRegression:
    @pytest.mark.parametrize("text", ["", "hi", "```json\n{}\n```", "```python\nx=1\n```"])
    def test_code_list_always_list(self, text):
        assert isinstance(_p(text).code_list, list)

    @pytest.mark.parametrize("text", ["", "hi", "```json\n{}\n```"])
    def test_files_always_list(self, text):
        assert isinstance(_p(text).files, list)

    @pytest.mark.parametrize("text", ["", "hi", "```json\n{'code':'x=1'}\n```"])
    def test_text_always_str(self, text):
        assert isinstance(_p(text).text, str)


class TestMarkdownDetection:
    def test_heading_detected(self):
        r = _p('```json\n{"text": "## Title\\ncontent"}\n```')
        assert r.is_markdown is True

    def test_bold_detected(self):
        r = _p('```json\n{"text": "Hello **world**"}\n```')
        assert r.is_markdown is True

    def test_list_detected(self):
        r = _p('```json\n{"text": "- item 1\\n- item 2"}\n```')
        assert r.is_markdown is True

    def test_plain_text_not_detected(self):
        r = _p('```json\n{"text": "hello world"}\n```')
        assert r.is_markdown is False

    def test_empty_text(self):
        r = _p('```json\n{"text": ""}\n```')
        assert r.is_markdown is False

    def test_code_fence_text_md(self):
        r = _p("```python\nprint(1)\n```\n\n## Summary\nhere is result")
        assert r.is_markdown is True
