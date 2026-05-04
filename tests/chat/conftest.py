"""Shared fixtures for chat tests."""

import os
import subprocess
import sys

import pytest

PROJECT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
SRC_DIR = os.path.join(PROJECT_DIR, "src")

RUN_SH = os.path.join(PROJECT_DIR, "scripts", "run.sh")


def _ensure_src_path():
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)


def _agent_running(agent: str) -> bool:
    """Check if agent is running via run.sh status (parses stdout)."""
    try:
        result = subprocess.run(
            ["bash", RUN_SH, "status", agent],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=PROJECT_DIR,
        )
        return "RUNNING" in result.stdout
    except Exception:
        return False


# ---------------------------------------------------------------------------
# deer-flow
# ---------------------------------------------------------------------------


@pytest.fixture
def deerflow_client():
    """ChatClient("deer-flow"). Requires deer-flow running."""
    if not _agent_running("deer-flow"):
        pytest.skip("deer-flow not running (run.sh start deer-flow)")
    _ensure_src_path()

    from chat import ChatClient

    return ChatClient("deer-flow", model="deepseek-v4-flash")


# ---------------------------------------------------------------------------
# nanobot
# ---------------------------------------------------------------------------


@pytest.fixture
def nanobot_client():
    """ChatClient("nanobot"). Requires nanobot running."""
    if not _agent_running("nanobot"):
        pytest.skip("nanobot not running (run.sh start nanobot --no-webui)")
    _ensure_src_path()

    from chat import ChatClient

    return ChatClient("nanobot")


# ---------------------------------------------------------------------------
# hermes-agent
# ---------------------------------------------------------------------------


@pytest.fixture
def hermes_client():
    """ChatClient("hermes-agent"). Requires hermes-agent running."""
    if not _agent_running("hermes-agent"):
        pytest.skip("hermes-agent not running (run.sh start hermes-agent --no-webui)")
    _ensure_src_path()

    from chat import ChatClient

    return ChatClient("hermes-agent")


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def any_client(nanobot_client):
    """A client for ChatClient-common tests (uses nanobot by default)."""
    return nanobot_client


def assert_nonempty_response(text: str) -> None:
    """Response must be a non-empty string."""
    assert isinstance(text, str), f"Expected str, got {type(text)}"
    assert len(text.strip()) > 0, "Response must not be empty"
