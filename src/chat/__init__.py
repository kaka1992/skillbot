"""Unified chat client for deer-flow / nanobot / hermes-agent."""

from collections.abc import Iterator
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
    ) -> None:
        if agent not in _AGENTS:
            raise ValueError(f"Unknown agent '{agent}'. Choose: {', '.join(sorted(_AGENTS))}")

        self._agent = agent
        self._model = model

        if agent == "deer-flow":
            self._backend: AbstractBackend = DeerFlowBackend(model=model)
        elif agent == "nanobot":
            self._backend = NanobotBackend(model=model, auto_start=auto_start)
        elif agent == "hermes-agent":
            self._backend = HermesBackend(model=model, auto_start=auto_start)
        else:
            raise ValueError(f"Unknown agent: {agent}")

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def chat(self, content: str, session: str = "default", model: Optional[str] = None) -> str:
        """Send a message and return the full response."""
        return self._backend.chat(content=content, session=session, model=model)

    def stream(self, content: str, session: str = "default", model: Optional[str] = None) -> Iterator[str]:
        """Send a message and yield response tokens."""
        yield from self._backend.stream(content=content, session=session, model=model)

    def list_sessions(self) -> list[str]:
        """Return tracked session IDs."""
        return self._backend.list_sessions()

    def clear_session(self, session: str) -> None:
        """Clear a session."""
        self._backend.clear_session(session)

    @property
    def agent(self) -> str:
        return self._agent
