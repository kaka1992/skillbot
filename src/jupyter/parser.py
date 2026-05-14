"""BlockParser — extract JSON from agent output into ParsedResult."""

import json
import re
from dataclasses import dataclass, field

_JSON_FENCE = re.compile(
    r"```json\s*\n(.*?)\n```",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class ParsedResult:
    text: str = ""
    csv: dict[str, str] = field(default_factory=dict)
    images: list[bytes] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)
    code: str = ""


def parse(text: str) -> ParsedResult:
    """Parse JSON block from agent output into ParsedResult.

    Raises ValueError if no JSON block found or JSON is invalid.
    """
    m = _JSON_FENCE.search(text)
    if not m:
        raise ValueError(f"No JSON block found in agent output:\n{text[:500]}")

    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in agent output: {e}\n{m.group(1)[:500]}")

    result = ParsedResult()
    result.text = data.get("text", "")
    result.code = data.get("code", "")
    for path in data.get("files", []):
        result.files[path] = path
    return result
