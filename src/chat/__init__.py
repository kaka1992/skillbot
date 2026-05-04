"""Unified chat client for deer-flow / nanobot / hermes-agent."""

from collections.abc import AsyncIterator, Iterator
from typing import Optional

from .base import AbstractBackend, AgentNotInstalledError, AgentStartupTimeout, ChatError
from .deerflow import DeerFlowBackend
from .nanobot import NanobotBackend
from .hermes import HermesBackend

__all__ = [
    "ChatClient",
    "ChatError",
    "AgentNotInstalledError",
    "AgentStartupTimeout",
]

_AGENTS = {"deer-flow", "nanobot", "hermes-agent"}


class ChatClient:
    """Unified chat client across deer-flow / nanobot / hermes-agent.

    Usage::

        from chat import ChatClient

        c = ChatClient("nanobot")
        reply = c.chat("Hello", session="s1")
        print(reply)

        for chunk in c.stream("Tell a joke", session="s2"):
            print(chunk, end="")
    """

    def __init__(
        self,
        agent: str,
        model: Optional[str] = None,
        auto_start: bool = True,
        timeout: int = 120,
    ) -> None:
        if agent not in _AGENTS:
            raise ValueError(f"Unknown agent '{agent}'. Choose: {', '.join(sorted(_AGENTS))}")

        self._agent = agent
        self._model = model

        if agent == "deer-flow":
            self._backend: AbstractBackend = DeerFlowBackend(model=model, timeout=timeout)
        elif agent == "nanobot":
            self._backend = NanobotBackend(model=model, auto_start=auto_start, timeout=timeout)
        elif agent == "hermes-agent":
            self._backend = HermesBackend(model=model, auto_start=auto_start, timeout=timeout)
        else:
            raise ValueError(f"Unknown agent: {agent}")

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def chat(self, content: str, session: str = "default", model: Optional[str] = None) -> str:
        """Send a message and return the full response."""
        return self._backend.chat(content=content, session=session, model=model)

    async def async_chat(
        self, content: str, session: str = "default", model: Optional[str] = None
    ) -> str:
        """Async: send a message and return the full response."""
        return await self._backend.async_chat(content=content, session=session, model=model)

    def stream(self, content: str, session: str = "default", model: Optional[str] = None) -> Iterator[str]:
        """Send a message and yield response tokens."""
        yield from self._backend.stream(content=content, session=session, model=model)

    async def async_stream(
        self, content: str, session: str = "default", model: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Async: send a message and yield response tokens."""
        async for chunk in self._backend.async_stream(content=content, session=session, model=model):
            yield chunk

    def list_sessions(self) -> list[str]:
        """Return tracked session IDs."""
        return self._backend.list_sessions()

    def clear_session(self, session: str) -> None:
        """Clear a session."""
        self._backend.clear_session(session)

    @property
    def agent(self) -> str:
        return self._agent
