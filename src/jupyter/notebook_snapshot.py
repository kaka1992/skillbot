"""Notebook-level snapshot — capture all cells at a point in time.

Stores under ``.run/notebook_snapshots/<notebook>/<timestamp>.json``.
Keeps last 50 snapshots.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .snapshot_utils import notebook_id, dir_for

_log = logging.getLogger(__name__)

MAX_SNAPSHOTS = 50


def _base_dir(nb_path: str = "") -> Path:
    base = Path(__file__).resolve().parents[2] / ".run" / "notebook_snapshots"
    return base / dir_for(nb_path)


def _prune(directory: Path) -> None:
    files = sorted(directory.glob("*.json"))
    while len(files) > MAX_SNAPSHOTS:
        files.pop(0).unlink()
        files = sorted(directory.glob("*.json"))


def take(cells: list | None = None, nb_path: str = "") -> Path | None:
    """Capture all cell contents + outputs as a snapshot.

    If *nb_path* is given, uses it for directory isolation.
    Otherwise falls back to kernel CWD."""
    cell_list: list[dict] = []
    if cells is not None:
        cell_list = [
            {"cell_id": c.get("cell_id", ""), "code": c.get("code", ""),
             "output": c.get("output", ""), "error": c.get("error", "")}
            for c in cells
        ]
    else:
        try:
            from jupyter.magic import _get_magic
            inst = _get_magic()
            if inst and inst.ns and inst.ns._cells:
                cell_list = [
                    {"cell_id": c.get("cell_id", ""), "code": c.get("code", ""),
                     "output": c.get("output", ""), "error": c.get("error", "")}
                    for c in inst.ns._cells
                ]
        except Exception as e:
            _log.warning("snapshot take: failed to get cells: %s", e)
    if not cell_list:
        return None

    d = _base_dir(nb_path)
    d.mkdir(parents=True, exist_ok=True)
    _prune(d)

    ts = int(time.time())
    path = d / f"{ts}.json"
    path.write_text(json.dumps({"timestamp": ts, "cells": cell_list},
                    indent=2, ensure_ascii=False), encoding="utf-8")
    _log.info("snapshot saved: %s (%d cells)", path.name, len(cell_list))
    return path


def list_snapshots_for(nb_path: str) -> list[dict]:
    return _list_dir(_base_dir(nb_path))


def list_snapshots() -> list[dict]:
    return _list_dir(_base_dir())


def _list_dir(d: Path) -> list[dict]:
    if not d.is_dir():
        return []
    results = []
    for f in sorted(d.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            pv = []
            for c in data.get("cells", [])[:5]:
                line = (c.get("code", "") or "").split("\n")[0][:80]
                if line.strip():
                    pv.append(line.strip())
            results.append({
                "id": f.stem,
                "timestamp": data.get("timestamp", 0),
                "cells_count": len(data.get("cells", [])),
                "preview": pv,
            })
        except Exception:
            pass
    return results


def get_snapshot(snapshot_id: str, nb_path: str = "") -> dict | None:
    path = _base_dir(nb_path) / f"{snapshot_id}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def restore(snapshot_id: str, nb_path: str = "") -> list[dict] | None:
    data = get_snapshot(snapshot_id, nb_path)
    return data.get("cells") if data else None
