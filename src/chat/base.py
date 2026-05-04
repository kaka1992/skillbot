"""Abstract backend interface for ChatClient."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from typing import Optional


class ChatError(Exception):
    """Base error for chat operations."""


class AgentNotInstalledError(ChatError):
    """Agent is not installed."""


class AgentStartupTimeout(ChatError):
    """Agent failed to start within the timeout."""


class AbstractBackend(ABC):
    """Unified chat backend interface."""

    @abstractmethod
    def chat(self, content: str, session: str, model: Optional[str] = None) -> str:
        """Send a single message and return the full response."""
        ...

    @abstractmethod
    def stream(self, content: str, session: str, model: Optional[str] = None) -> Iterator[str]:
        """Send a message and yield response tokens via SSE."""
        ...

    async def async_chat(
        self, content: str, session: str, model: Optional[str] = None
    ) -> str:
        """Async wrapper: run sync chat in thread pool."""
        return await asyncio.to_thread(self.chat, content, session, model)

    async def async_stream(
        self, content: str, session: str, model: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Async wrapper: run sync stream in thread pool, yielding via queue."""
        queue: asyncio.Queue = asyncio.Queue()

        def _run():
            try:
                for chunk in self.stream(content, session, model):
                    queue.put_nowait(("data", chunk))
            except Exception as exc:
                queue.put_nowait(("error", exc))
            finally:
                queue.put_nowait(("done", None))

        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(None, _run)

        while True:
            kind, value = await queue.get()
            if kind == "done":
                break
            if kind == "error":
                raise value  # type: ignore[misc]
            yield value

    def list_sessions(self) -> list[str]:
        """List active session IDs."""
        return []

    def clear_session(self, session: str) -> None:
        """Clear a specific session."""
        ...
