"""Cell-level snapshot — auto-save code + output on each execution.

Stores under ``.run/cell_snapshots/<notebook>/<cell_id>/vNNNN.json``.
Keeps the last N versions (default 50), oldest overwritten first.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .snapshot_utils import notebook_id, dir_for

_log = logging.getLogger(__name__)

MAX_VERSIONS = 50


def _base_dir(nb_path: str = "") -> Path:
    base = Path(__file__).resolve().parents[2] / ".run" / "cell_snapshots"
    return base / dir_for(nb_path)


def save(cell_id: str, code: str, output: str = "", error: str = "",
         nb_path: str = "") -> Path | None:
    """Save a version snapshot. Returns the file path or None."""
    if not cell_id:
        return None
    d = _base_dir(nb_path) / cell_id
    d.mkdir(parents=True, exist_ok=True)

    # Find next version number (ring buffer: overwrite oldest if at limit)
    existing = sorted(d.glob("v*.json"))
    if len(existing) >= MAX_VERSIONS:
        existing[0].unlink()  # remove oldest
        existing = existing[1:]

    next_num = 1
    if existing:
        last = existing[-1].stem  # e.g. "v0042"
        try:
            next_num = int(last[1:]) + 1
        except ValueError:
            next_num = len(existing) + 1

    path = d / f"v{next_num:04d}.json"
    data = {
        "cell_id": cell_id,
        "timestamp": time.time(),
        "code": code.strip(),
        "output": output.strip()[:5000],
        "error": error.strip()[:2000],
    }
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        _log.debug("cell_snapshot saved: %s v%04d", cell_id[:8], next_num)
        return path
    except Exception:
        _log.exception("cell_snapshot save failed: %s", cell_id)
        return None


def list_versions(cell_id: str, nb_path: str = "") -> list[dict]:
    """Return version list for a cell, newest first."""
    d = _base_dir(nb_path) / cell_id
    if not d.is_dir():
        return []
    versions = []
    for f in sorted(d.glob("v*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["version"] = f.stem
            versions.append(data)
        except Exception:
            pass
    return versions


def get_version(cell_id: str, version: str, nb_path: str = "") -> dict | None:
    """Get a specific version snapshot."""
    path = _base_dir(nb_path) / cell_id / f"{version}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def restore(cell_id: str, version: str, nb_path: str = "") -> str | None:
    """Return the code from a specific version, or None."""
    data = get_version(cell_id, version, nb_path)
    return data.get("code") if data else None
