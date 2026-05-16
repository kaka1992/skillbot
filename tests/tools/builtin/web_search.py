"""Example built-in tool: web search via DuckDuckGo."""

from tools import ToolResult, register


@register(
    name="web_search",
    description="Search the web using DuckDuckGo",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            }
        },
        "required": ["query"],
    },
    group="web",
)
async def web_search(params: dict) -> ToolResult:
    from urllib.parse import quote_plus

    url = f"https://html.duckduckgo.com/html/?q={quote_plus(params['query'])}"
    # placeholder — real implementation would fetch + parse
    return ToolResult(
        content=f"Search results for: {params['query']} (DuckDuckGo: {url})",
    )
