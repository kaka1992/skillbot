"""Hook events, status codes, and result type."""

from __future__ import annotations


class HookEvent:
    CODE_REVIEW = "code_review"
    AGENT_CELL_REVIEW = "agent_cell_review"


class HookStatus:
    SUCCESS = "success"
    FAILED_STOP = "failed_stop"
    FAILED_CONTINUE = "failed_continue"


class HookResult:
    __slots__ = ("status", "message", "detail")

    def __init__(self, status: str, message: str = "", detail: str = "") -> None:
        self.status = status
        self.message = message
        self.detail = detail
