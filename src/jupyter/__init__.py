"""Jupyter integration — %%agent cell magic."""

import logging
from pathlib import Path

_LOADED = False


def load_ipython_extension(ipython):
    """Register %%agent magic. Called by %load_ext jupyter.

    Idempotent: bootstrap and the startup script may both load it, and
    registering handlers twice would duplicate comm replies and log lines.
    """
    global _LOADED
    if _LOADED:
        return
    _LOADED = True

    # setup jupyter logging — resolve relative to project root
    _proj = Path(__file__).resolve().parents[2]
    _log_dir = _proj / ".run"
    _log_dir.mkdir(exist_ok=True)
    handler = logging.FileHandler(str(_log_dir / "jupyter.log"))
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logging.getLogger("jupyter").addHandler(handler)
    logging.getLogger("jupyter").setLevel(logging.INFO)

    # register magics
    from .magic import (
        AgentMagic,
        _panel_input,
        _panel_set_mode,
        _panel_track_cell_delete,
        _panel_track_cell_edit,
    )
    ipython.user_ns['_panel_input'] = _panel_input
    ipython.user_ns['_panel_set_mode'] = _panel_set_mode
    ipython.user_ns['_panel_track_cell_edit'] = _panel_track_cell_edit
    ipython.user_ns['_panel_track_cell_delete'] = _panel_track_cell_delete
    ipython.register_magics(AgentMagic)
