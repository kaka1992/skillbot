"""Jupyter integration — %%agent cell magic."""

import logging
from pathlib import Path


def _inject_sql_js_deferred(ipython) -> None:
    """Schedule JS injection on first cell execution (post kernel connect)."""
    js_path = Path(__file__).resolve().parent / "dsl" / "sql" / "static" / "sql-cell.js"
    if not js_path.is_file():
        return

    import base64
    js_b64 = base64.b64encode(js_path.read_bytes()).decode()

    def _on_first_exec(_info=None):
        try:
            from IPython.display import Javascript, display
            display(Javascript(f'eval(atob("{js_b64}"))'), include=["application/javascript"])
        except Exception:
            pass
        ipython.events.unregister("pre_run_cell", _on_first_exec)

    ipython.events.register("pre_run_cell", _on_first_exec)


def load_ipython_extension(ipython):
    """Register %%agent magic. Called by %load_ext jupyter."""
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
    from .magic import AgentMagic
    ipython.register_magics(AgentMagic)

    # register SQL completer
    from .dsl.sql.completer import load_sql_completer
    load_sql_completer(ipython)

    # inject SQL cell JS (deferred — injected on first %%sql cell execution)
    _inject_sql_js_deferred(ipython)
