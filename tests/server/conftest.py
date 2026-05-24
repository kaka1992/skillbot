"""Shared fixtures for server tests."""

import os
import shutil

import pytest

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SETTINGS_SRC = os.path.join(
    PROJECT_DIR, "conf", "agent_conf", "claude-code", "settings.json"
)


def _get_claude_home() -> str:
    """Return claude home path (same logic as install.sh get_agent_path)."""
    install_dir = os.environ.get("SKILL_BOT_AGENT_INSTALL_DIR", "")
    if install_dir:
        return os.path.join(install_dir, "claude-code")
    return os.path.join(PROJECT_DIR, "agents", "claude-code")


@pytest.fixture(scope="session", autouse=True)
def _setup_claude():
    """Ensure isolated claude home has settings.json."""
    # 1. Resolve claude home via install.sh
    claude_home = _get_claude_home()

    # 2. settings.json source must exist
    if not os.path.exists(_SETTINGS_SRC):
        raise RuntimeError(f"Settings template not found: {_SETTINGS_SRC}")

    # 3. Copy settings.json to claude home
    dest_dir = os.path.join(claude_home, ".claude")
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(_SETTINGS_SRC, os.path.join(dest_dir, "settings.json"))
