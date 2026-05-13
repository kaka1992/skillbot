"""Render parsed agent output into Jupyter cell."""

from io import StringIO
from pathlib import Path

from IPython.display import Image, display

from .namespace import Namespace
from .parser import ParsedResult


def _load_csv(name: str, content: str, ns: Namespace) -> None:
    """Try to load CSV from content (inline) or filesystem path."""
    import pandas as pd

    path_hint = content.strip()
    for path in (Path(path_hint), Path(path_hint.strip('\'"'))):
        try:
            if path.is_file():
                df = pd.read_csv(str(path))
                var_name = path.stem
                ns.inject(var_name, df)
                print(f"[{var_name}] {df.shape[0]} rows × {df.shape[1]} cols (from {path})")
                return
        except Exception:
            pass

    try:
        df = pd.read_csv(StringIO(content))
        var_name = name.rsplit(".", 1)[0]
        ns.inject(var_name, df)
        print(f"[{var_name}] {df.shape[0]} rows × {df.shape[1]} cols")
    except Exception as e:
        ns.inject(name, content)
        print(f"[{name}] csv parse error: {e}")


def render_output(shell_or_ns, result: ParsedResult, skip_text: bool = False) -> None:
    """Print text, display images, inject DataFrames + code into user_ns."""
    if isinstance(shell_or_ns, Namespace):
        ns = shell_or_ns
    else:
        ns = Namespace(shell_or_ns)

    if result.text and not skip_text:
        print(result.text)

    if result.code:
        ns.set_next_input(result.code)

    for name, content in result.csv.items():
        _load_csv(name, content, ns)

    for img_bytes in result.images:
        try:
            display(Image(img_bytes, format="png", embed=True))
        except Exception:
            pass

    for name, content in result.files.items():
        if name.endswith(".csv"):
            _load_csv(name, content, ns)
        else:
            ns.inject(name, content)
            print(f"[{name}] file loaded ({len(content)} bytes)")
