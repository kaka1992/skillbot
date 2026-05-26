"""BlockParser — extract structured output from agent text into ParsedResult."""

import json
import logging
import re
from dataclasses import dataclass, field

_log = logging.getLogger(__name__)

_JSON_FENCE = re.compile(
    r"```json\s*\n(.*?)\n```",
    re.MULTILINE | re.DOTALL,
)

_CODE_FENCE = re.compile(
    r"(?:^|\n)```(?:python)?[ \t]*\n(.*?)\n```",
    re.MULTILINE | re.DOTALL,
)

_MD_PATTERNS = (
    re.compile(r'^#{1,6}\s', re.MULTILINE),
    re.compile(r'\*\*.*\*\*'),
    re.compile(r'^[-*+]\s', re.MULTILINE),
    re.compile(r'^\d+\.\s', re.MULTILINE),
    re.compile(r'`[^`]+`'),
    re.compile(r'^\|.*\|', re.MULTILINE),
    re.compile(r'^> ', re.MULTILINE),
)


def _has_markdown(text: str) -> bool:
    return any(p.search(text) for p in _MD_PATTERNS)


@dataclass
class ParsedResult:
    text: str = ""
    csv: dict[str, str] = field(default_factory=dict)
    images: list[bytes] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    code_list: list[str] = field(default_factory=list)
    plan: str = ""
    is_markdown: bool = False


def parse(text: str) -> ParsedResult:
    """Parse agent output with cascading fallback.

    Priority: JSON fenced → raw JSON → code fenced → raw text.
    Unparseable content at each level is placed in ``.text`` and a warning
    is logged; the function never raises.
    """
    from .render import render_debug
    render_debug(f"parse input ({len(text)} chars)")
    _log.debug(text[:5000])

    # 1. JSON fenced block: ```json ... ```
    m = _JSON_FENCE.search(text)
    if m:
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            _log.warning("parse: invalid JSON in fenced block, falling back")
            return _from_code_fence_or_text(text)
        return _from_json(data)

    # 2. Raw JSON: { ... }
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            _log.warning("parse: invalid raw JSON, falling back")
            return _from_code_fence_or_text(text)
        return _from_json(data)

    # 3. Code fence + 4. raw text
    return _from_code_fence_or_text(text)


def _from_json(data: dict) -> ParsedResult:
    """Build ParsedResult from parsed JSON dict."""
    result = ParsedResult()
    result.text = data.get("text", "")
    result.plan = data.get("plan", "")
    code_raw = data.get("code", "")
    if isinstance(code_raw, list):
        result.code_list = [str(c) for c in code_raw if str(c).strip()]
    elif isinstance(code_raw, str) and code_raw.strip():
        result.code_list = [code_raw.strip()]
    result.files = [str(f) for f in data.get("files", [])]
    if result.text:
        result.is_markdown = _has_markdown(result.text)
    return result


def _from_code_fence_or_text(text: str) -> ParsedResult:
    """Extract code from `` ```python ``` `` or bare `` ``` ``` `` blocks.

    Code blocks populate ``code_list``; surrounding text goes to ``.text``.
    If no code fences are found, the whole *text* is placed in ``.text``.
    """
    result = ParsedResult()
    matches = list(_CODE_FENCE.finditer(text))
    if not matches:
        _log.warning("parse: no structured content found (%d chars)", len(text))
        result.text = text
        if result.text:
            result.is_markdown = _has_markdown(result.text)
        return result

    # text segments between code blocks
    text_parts: list[str] = []
    last_end = 0
    for m in matches:
        before = text[last_end:m.start()].strip()
        if before:
            text_parts.append(before)
        result.code_list.append(m.group(1).strip())
        last_end = m.end()
    after = text[last_end:].strip()
    if after:
        text_parts.append(after)
    result.text = "\n\n".join(text_parts)
    if result.text:
        result.is_markdown = _has_markdown(result.text)
    _log.warning("parse: %d code fence(s) extracted, no JSON", len(matches))
    return result


def parse_review_result(raw: str) -> dict:
    """Parse agent review output.

    Returns ``{"status": str|None, "code": str|None}``.

    status: ``"SOLVED"`` | ``"NOT_SOLVED"`` | ``"SOLVING"`` | ``None``
    """
    import json as _json
    from .render import render_debug
    render_debug(f"parse_review_result input ({len(raw)} chars)")
    _log.debug(raw[:5000])

    # Try JSON: fenced first, then raw
    data = None
    m = _JSON_FENCE.search(raw)
    if m:
        try:
            data = _json.loads(m.group(1))
        except _json.JSONDecodeError:
            pass
    if data is None and raw.strip().startswith("{"):
        try:
            data = _json.loads(raw.strip())
        except _json.JSONDecodeError:
            pass

    if data:
        status = str(data.get("text") or "").strip().upper()
        reason = str(data.get("reason") or "").strip()
        code = data.get("code") or None
        if isinstance(code, list):
            code = code[0] if code else None
        code = str(code).strip() if code else None
        text = data.get("text", "")
        # Normalize status
        if "NOT_SOLVED" in status:
            status = "NOT_SOLVED"
        elif "SOLVED" in status:
            status = "SOLVED"
        elif code:
            status = "SOLVING"
        else:
            status = None
    else:
        # Plain text fallback
        desc = raw.strip().upper()
        status = "NOT_SOLVED" if "NOT_SOLVED" in desc else ("SOLVED" if "SOLVED" in desc else None)
        reason = raw.strip()[:500]
        code = None
        text = raw.strip()

    is_markdown = _has_markdown(text) if text else False

    return {"status": status, "code": code, "reason": reason, "text": text, "is_markdown": is_markdown}


def traceback_line(tb) -> int:
    """Return the source line number from the LAST frame of a traceback."""
    import traceback
    frames = traceback.extract_tb(tb)
    return frames[-1].lineno if frames else 10**9
