from typing import Optional
"""Abstract backend interface for ChatClient."""

from abc import ABC, abstractmethod
from collections.abc import Iterator


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

    def list_sessions(self) -> list[str]:
        """List active session IDs."""
        return []

    def clear_session(self, session: str) -> None:
        """Clear a specific session."""
        ...
