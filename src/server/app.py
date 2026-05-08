"""Claude Code HTTP server — FastAPI app with multi-session support."""

import json
import logging
import os
import sys
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .session import SessionManager

# ---- config -----------------------------------------------------------

PORT = int(os.environ.get("CLAUDE_SERVER_PORT", "9000"))
HOST = os.environ.get("CLAUDE_SERVER_HOST", "127.0.0.1")
TIMEOUT = int(os.environ.get("CLAUDE_SERVER_TIMEOUT", "300"))
ALLOWED_TOOLS = os.environ.get("CLAUDE_SERVER_ALLOWED_TOOLS", "")
WORK_DIR = os.environ.get("CLAUDE_SERVER_WORK_DIR", os.getcwd())

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("claude-server")

# ---- app --------------------------------------------------------------

app = FastAPI(title="Claude Code HTTP Server", version="0.1.0")
manager = SessionManager()


# ---- models -----------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    timeout: Optional[int] = None
    allowed_tools: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    elapsed: float


class SessionInfo(BaseModel):
    session_id: str
    messages: int
    created_at: float


# ---- routes -----------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "claude-code-server"}


@app.post("/sessions", status_code=201)
async def create_session():
    s = manager.create()
    return {"session_id": s.sid}


@app.get("/sessions")
async def list_sessions() -> list[SessionInfo]:
    return [SessionInfo(**s) for s in manager.list_sessions()]


@app.get("/sessions/{sid}")
async def get_session(sid: str) -> SessionInfo:
    s = manager.get(sid)
    if not s:
        raise HTTPException(404, f"Session {sid} not found")
    return SessionInfo(**s.to_dict())


@app.delete("/sessions/{sid}", status_code=204)
async def delete_session(sid: str):
    if not await manager.delete(sid):
        raise HTTPException(404, f"Session {sid} not found")


@app.post("/sessions/{sid}/chat", response_model=ChatResponse)
async def chat(sid: str, body: ChatRequest):
    s = manager.get(sid)
    if not s:
        raise HTTPException(404, f"Session {sid} not found")

    async with s.lock:
        t0 = time.monotonic()
        try:
            text = await s.send(
                body.message,
                timeout=body.timeout or TIMEOUT,
                allowed_tools=body.allowed_tools or ALLOWED_TOOLS or None,
                cwd=WORK_DIR,
            )
        except RuntimeError as e:
            raise HTTPException(500, str(e))

        elapsed = round(time.monotonic() - t0, 2)
        return ChatResponse(session_id=sid, reply=text, elapsed=elapsed)


@app.post("/sessions/{sid}/chat/stream")
async def chat_stream(sid: str, body: ChatRequest):
    s = manager.get(sid)
    if not s:
        raise HTTPException(404, f"Session {sid} not found")

    async def event_generator():
        async with s.lock:
            try:
                async for chunk in s.send_stream(
                    body.message,
                    timeout=body.timeout or TIMEOUT,
                    allowed_tools=body.allowed_tools or ALLOWED_TOOLS or None,
                    cwd=WORK_DIR,
                ):
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
            except RuntimeError as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
                return
            except Exception:
                logger.exception("Unhandled error during streaming")
                yield f"data: {json.dumps({'type': 'error', 'error': 'Internal server error'})}\n\n"
                return

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/sessions/{sid}/chat/trace")
async def chat_trace(sid: str, body: ChatRequest):
    """Stream chat with full trace: text + thinking + tool_use + subagent + usage."""
    s = manager.get(sid)
    if not s:
        raise HTTPException(404, f"Session {sid} not found")

    async def event_generator():
        async with s.lock:
            try:
                async for chunk in s.send_stream_chunks(
                    body.message,
                    timeout=body.timeout or TIMEOUT,
                    allowed_tools=body.allowed_tools or ALLOWED_TOOLS or None,
                    cwd=WORK_DIR,
                ):
                    if chunk.text:
                        yield f"data: {json.dumps({'type': 'text', 'text': chunk.text})}\n\n"
                    if chunk.blocks:
                        for b in chunk.blocks:
                            yield f"data: {json.dumps({'type': b.type, 'data': b.data})}\n\n"
            except RuntimeError as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
                return
            except Exception:
                logger.exception("Unhandled error during trace streaming")
                yield f"data: {json.dumps({'type': 'error', 'error': 'Internal server error'})}\n\n"
                return

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/sessions/{sid}/history")
async def get_history(sid: str):
    s = manager.get(sid)
    if not s:
        raise HTTPException(404, f"Session {sid} not found")
    return [
        {"role": m.role, "content": m.content, "time": m.time}
        for m in s.history
    ]


# ---- main -------------------------------------------------------------

def main():
    import uvicorn

    logger.info("Starting Claude Code HTTP Server on %s:%s", HOST, PORT)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
