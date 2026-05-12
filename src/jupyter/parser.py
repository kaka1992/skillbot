"""BlockParser — extract text / csv / image / file from fenced blocks."""

import base64
import re
from dataclasses import dataclass, field

_FENCE = re.compile(
    r"^```(csv|image|file)(?::(\S+))?\s*\n(.*?)\n```",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class ParsedResult:
    text: str = ""
    csv: dict[str, str] = field(default_factory=dict)        # name → csv_content
    images: list[bytes] = field(default_factory=list)        # decoded PNG bytes
    files: dict[str, str] = field(default_factory=dict)       # name → content


def parse(text: str) -> ParsedResult:
    """Parse fenced blocks from agent output, return structured result."""
    result = ParsedResult()
    pos = 0

    for m in _FENCE.finditer(text):
        # capture text before this block
        before = text[pos:m.start()].strip()
        if before:
            if result.text:
                result.text += "\n\n"
            result.text += before

        block_type = m.group(1)
        label = m.group(2) or ""
        content = m.group(3)

        if block_type == "csv":
            result.csv[label or "df"] = content
        elif block_type == "image":
            try:
                result.images.append(base64.b64decode(content))
            except Exception:
                result.images.append(content.encode())
        elif block_type == "file":
            result.files[label or "file"] = content

        pos = m.end()

    # trailing text after last fence
    after = text[pos:].strip()
    if after:
        if result.text:
            result.text += "\n\n"
        result.text += after

    return result
