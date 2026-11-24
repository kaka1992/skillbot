"""Disk persistence for per-notebook Agent Panel conversations.

The frontend keeps a per-notebook conversation buffer in localStorage (fast,
per-browser). This module mirrors that buffer to disk under the project's
``.run/conversations/`` directory so a conversation survives a JupyterLab
restart, a browser change, or moving to another machine.

Files are keyed by md5(notebook_path)[:12] — the same scheme used by
``snapshot_utils`` — so a notebook always maps to the same conversation file.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

_log = logging.getLogger(__name__)


def _conversations_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    d = root / ".run" / "conversations"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _key(nb_path: str) -> str:
    return hashlib.md5((nb_path or "").encode()).hexdigest()[:12]


def save_conversation(nb_path: str, payload: str) -> bool:
    """Persist a serialized conversation buffer for a notebook path.

    ``payload`` is the JSON string the frontend already stores in localStorage
    (output HTML, history, mode, status). We store it verbatim plus the path
    so the switcher can label recovered sessions.
    """
    if not nb_path:
        return False
    try:
        data = {"path": nb_path, "buffer": payload}
        target = _conversations_dir() / f"{_key(nb_path)}.json"
        target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        _log.debug("save_conversation: failed", exc_info=True)
        return False


def load_conversation(nb_path: str) -> str:
    """Return the persisted buffer JSON string for a notebook, or '' if none."""
    if not nb_path:
        return ""
    try:
        target = _conversations_dir() / f"{_key(nb_path)}.json"
        if not target.exists():
            return ""
        data = json.loads(target.read_text(encoding="utf-8"))
        return data.get("buffer", "") or ""
    except Exception:
        _log.debug("load_conversation: failed", exc_info=True)
        return ""


def list_conversations() -> list[dict]:
    """Return [{path, key}] for every persisted conversation (for the switcher)."""
    out: list[dict] = []
    try:
        for f in _conversations_dir().glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                p = data.get("path", "")
                if p:
                    out.append({"path": p, "key": f.stem})
            except Exception:
                continue
    except Exception:
        _log.debug("list_conversations: failed", exc_info=True)
    return out


def delete_conversation(nb_path: str) -> bool:
    """Delete the persisted conversation for a notebook path.

    Called when the user removes a session from the switcher, or when the
    underlying .ipynb file is deleted. Returns True if a file was removed.
    """
    if not nb_path:
        return False
    try:
        target = _conversations_dir() / f"{_key(nb_path)}.json"
        if target.exists():
            target.unlink()
            return True
        return False
    except Exception:
        _log.debug("delete_conversation: failed", exc_info=True)
        return False
