"""Built-in tool: read a file from disk."""

from tools import ToolResult, register


@register(
    name="file_read",
    description="Read the contents of a file from the filesystem",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read",
            }
        },
        "required": ["path"],
    },
    group="file",
)
async def file_read(params: dict) -> ToolResult:
    from pathlib import Path

    path = Path(params["path"])
    if not path.is_file():
        return ToolResult(error=f"File not found: {params['path']}")
    try:
        content = path.read_text()
        return ToolResult(data={
            "text": content[:5000],
            "path": str(path),
            "size": path.stat().st_size,
        })
    except Exception as e:
        return ToolResult(error=str(e))
