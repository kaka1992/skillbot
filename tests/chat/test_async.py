"""Tests for async chat/stream (ChatClient.async_chat / async_stream)."""

import pytest


@pytest.mark.asyncio
async def test_async_chat_nanobot(nanobot_client):
    """Async single-turn chat returns non-empty."""
    reply = await nanobot_client.async_chat("Say hello in one word", session="a1")
    assert isinstance(reply, str) and len(reply.strip()) > 0


@pytest.mark.asyncio
async def test_async_stream_nanobot(nanobot_client):
    """Async stream yields tokens."""
    chunks = []
    async for chunk in nanobot_client.async_stream("Count 1 to 3", session="a2"):
        chunks.append(chunk)
    text = "".join(chunks)
    assert len(text) > 0
    assert any(c.isdigit() for c in text), f"Expected numbers in stream, got: {text}"


@pytest.mark.asyncio
async def test_async_concurrent(nanobot_client):
    """Concurrent async calls do not interfere."""
    import asyncio

    async def ask(msg, sid):
        return await nanobot_client.async_chat(msg, session=sid)

    results = await asyncio.gather(
        ask("Say hello in one word", "c1"),
        ask("What is 1+1? One word", "c2"),
        ask("What color is the sky? One word", "c3"),
    )
    for r in results:
        assert isinstance(r, str) and len(r.strip()) > 0


@pytest.mark.asyncio
async def test_async_session_isolation(nanobot_client):
    """Async multi-turn remembers context."""
    sid = "amem"
    try:
        await nanobot_client.async_chat("My name is Alice", session=sid)
        reply = await nanobot_client.async_chat(
            "What is my name?", session=sid
        )
        assert "Alice" in reply or "alice" in reply.lower()
    finally:
        nanobot_client.clear_session(sid)


# ---- hermes-agent ----


@pytest.mark.asyncio
async def test_async_chat_hermes(hermes_client):
    reply = await hermes_client.async_chat("Say hello in one word", session="ah1")
    assert isinstance(reply, str) and len(reply.strip()) > 0


@pytest.mark.asyncio
async def test_async_stream_hermes(hermes_client):
    chunks = []
    async for chunk in hermes_client.async_stream("Count 1 to 3", session="ah2"):
        chunks.append(chunk)
    assert len("".join(chunks)) > 0


# ---- deer-flow ----


@pytest.mark.asyncio
async def test_async_chat_deerflow(deerflow_client):
    reply = await deerflow_client.async_chat("Say hello in one word", session="ad1")
    assert isinstance(reply, str) and len(reply.strip()) > 0
