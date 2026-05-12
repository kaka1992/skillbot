"""Jupyter integration — %%agent cell magic."""


def load_ipython_extension(ipython):
    """Register %%agent magic. Called by %load_ext jupyter."""
    from .magic import AgentMagic

    ipython.register_magics(AgentMagic)
