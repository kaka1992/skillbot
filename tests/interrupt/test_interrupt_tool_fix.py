"""Test: after interrupt during tool use, send synthetic tool_result to fix state."""
import asyncio
from claude_agent_sdk import (
    ClaudeSDKClient, ClaudeAgentOptions,
    AssistantMessage, ResultMessage, UserMessage,
)
from claude_agent_sdk.types import ToolUseBlock, ToolResultBlock, TextBlock


async def drain(gen, timeout=15, label=""):
    """Drain messages with timeout."""
    result = None
    try:
        while True:
            msg = await asyncio.wait_for(gen.__anext__(), timeout=timeout)
            t = type(msg).__name__
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    bt = type(block).__name__
                    detail = ""
                    if isinstance(block, ToolUseBlock):
                        detail = f" id={block.id} name={block.name}"
                    elif isinstance(block, TextBlock):
                        detail = f" text={block.text[:50]}"
                    print(f"  {label}{t} [{bt}{detail}]")
            elif isinstance(msg, ResultMessage):
                print(f"  {label}{t} is_error={msg.is_error} stop={msg.stop_reason}")
                result = msg
            else:
                print(f"  {label}{t}")
    except StopAsyncIteration:
        pass
    except asyncio.TimeoutError:
        print(f"  {label}TIMEOUT")
    return result


def get_tool_uses(msg):
    """Extract tool_use blocks from AssistantMessage."""
    if isinstance(msg, AssistantMessage):
        return [b for b in msg.content if isinstance(b, ToolUseBlock)]
    return []


async def test():
    opts = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        cwd="/tmp",
        max_turns=5,
    )
    client = ClaudeSDKClient(options=opts)
    await client.connect(prompt="You are a test assistant.")

    # Drain connect
    async for msg in client.receive_response():
        pass

    # Step 1: send query that uses tool, interrupt mid-tool
    print("[1] Sending tool-using query...")
    await client.query("Create /tmp/test_fix_demo.txt with content 'hello world'")

    last_tool_use = None
    gen = client.receive_messages()
    try:
        while True:
            msg = await asyncio.wait_for(gen.__anext__(), timeout=10)
            tools = get_tool_uses(msg)
            if tools:
                last_tool_use = tools[0]
                print(f"    ToolUse detected: id={last_tool_use.id} name={last_tool_use.name}")
                print("    → interrupt()!")
                await client.interrupt()
                print("    interrupt() returned")
                break
            elif isinstance(msg, ResultMessage):
                print(f"    Result: is_error={msg.is_error}")
                break
    except asyncio.TimeoutError:
        print("    TIMEOUT waiting for tool_use")

    # Step 2: send synthetic tool_result to fix the state
    if last_tool_use:
        print(f"\n[2] Fixing state with synthetic tool_result for {last_tool_use.id}...")
        # query() accepts string or AsyncIterable[dict], not UserMessage
        async def fix_stream():
            yield {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": last_tool_use.id,
                        "content": "[interrupted by user]",
                        "is_error": True,
                    }
                ],
            }
        await client.query(fix_stream())
        await drain(client.receive_messages(), label="  fix: ")

    # Step 3: send normal query — should work if fix succeeded
    print("\n[3] Sending normal follow-up query...")
    await client.query("What is 7+7? Answer in one word.")
    text_parts = []

    # Use receive_messages with timeout-based loop
    gen2 = client.receive_messages()
    try:
        while True:
            msg = await asyncio.wait_for(gen2.__anext__(), timeout=10)
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
            elif isinstance(msg, ResultMessage):
                print(f"    Result: is_error={msg.is_error} stop={msg.stop_reason}")
                break
    except StopAsyncIteration:
        pass
    except asyncio.TimeoutError:
        print("    TIMEOUT")

    full = "".join(text_parts)
    print(f"    Text: {full[:200]}")
    if "14" in full or "fourteen" in full.lower():
        print("\n[PASS] Synthetic tool_result fix works — session preserved!")
        return True
    else:
        print(f"\n[WARN] Expected '14'/'fourteen', got: {full[:200]}")
        return False

    await client.disconnect()


asyncio.run(test())
