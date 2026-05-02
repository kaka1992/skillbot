"""Shared fixtures for chat tests."""

import os
import socket
import sys

import pytest

PROJECT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
SRC_DIR = os.path.join(PROJECT_DIR, "src")
DEER_PKG = os.path.join(
    PROJECT_DIR, "agents", "deer-flow", "backend", "packages", "harness"
)


def _ensure_src_path():
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)


def _port_reachable(port: int, timeout: float = 1.0) -> bool:
    s = socket.socket()
    try:
        s.settimeout(timeout)
        s.connect(("localhost", port))
        return True
    except Exception:
        return False
    finally:
        s.close()


# ---------------------------------------------------------------------------
# deer-flow
# ---------------------------------------------------------------------------


@pytest.fixture
def deerflow_client():
    """ChatClient("deer-flow"). Requires deer-flow Gateway :8001 reachable."""
    if not _port_reachable(8001):
        pytest.skip("deer-flow Gateway :8001 not reachable (run.sh start deer-flow)")
    _ensure_src_path()

    from chat import ChatClient

    return ChatClient("deer-flow", model="deepseek-v4-flash")


# ---------------------------------------------------------------------------
# nanobot
# ---------------------------------------------------------------------------


@pytest.fixture
def nanobot_client():
    """ChatClient("nanobot"). Requires :8900 reachable."""
    if not _port_reachable(8900):
        pytest.skip("nanobot :8900 not reachable")
    _ensure_src_path()

    from chat import ChatClient

    return ChatClient("nanobot")


# ---------------------------------------------------------------------------
# hermes-agent
# ---------------------------------------------------------------------------


@pytest.fixture
def hermes_client():
    """ChatClient("hermes-agent"). Requires :8642 reachable."""
    if not _port_reachable(8642):
        pytest.skip("hermes :8640 not reachable")
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
