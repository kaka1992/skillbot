"""Shared notebook identification for cell_ and notebook_snapshot modules."""

import hashlib
import os


def notebook_id() -> str:
    """Stable notebook identifier.

    Uses kernel metadata's notebook_path (set by JupyterLab on each
    cell execution) for per-file isolation. Falls back to CWD.
    """
    import os as _os
    try:
        ip = get_ipython()  # noqa: F821
        kernel = getattr(ip, "kernel", None)
        parent = getattr(kernel, "_parent_header", None) or {}
        nb = (parent.get("metadata") or {}).get("notebook_path", "")
        if nb:
            return hashlib.md5(nb.encode()).hexdigest()[:12]
        nb = getattr(ip, "_notebook_path", None)
        if nb:
            return hashlib.md5(str(nb).encode()).hexdigest()[:12]
    except Exception:
        pass
    return hashlib.md5(_os.getcwd().encode()).hexdigest()[:12]


def dir_for(nb_path: str) -> str:
    """Return directory name from a notebook path (for querying by path)."""
    if nb_path:
        return hashlib.md5(nb_path.encode()).hexdigest()[:12]
    return notebook_id()
