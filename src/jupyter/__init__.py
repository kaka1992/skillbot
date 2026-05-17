"""Jupyter integration — %%agent cell magic."""

import logging


def load_ipython_extension(ipython):
    """Register %%agent magic. Called by %load_ext jupyter."""
    # setup jupyter logging
    handler = logging.FileHandler(".run/jupyter.log")
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
