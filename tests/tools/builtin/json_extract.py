"""Built-in tool: extract a field from JSON."""

import json

from tools import ToolResult, register


@register(
    name="json_extract",
    description="Parse a JSON string and extract a value by key path (e.g. 'data.users.0.name')",
    parameters={
        "type": "object",
        "properties": {
            "json_str": {
                "type": "string",
                "description": "The JSON string to parse",
            },
            "key_path": {
                "type": "string",
                "description": "Dot-separated path to the value",
            },
        },
        "required": ["json_str", "key_path"],
    },
    group="data",
)
async def json_extract(params: dict) -> ToolResult:
    try:
        data = json.loads(params["json_str"])
    except json.JSONDecodeError as e:
        return ToolResult(content="", error=f"Invalid JSON: {e}")

    obj = data
    for key in params["key_path"].split("."):
        try:
            if isinstance(obj, list):
                obj = obj[int(key)]
            else:
                obj = obj[key]
        except (KeyError, IndexError, ValueError, TypeError) as e:
            return ToolResult(content="", error=f"Key '{key}' not found: {e}")

    return ToolResult(content=json.dumps(obj, ensure_ascii=False))
