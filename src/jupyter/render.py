"""Render parsed agent output into Jupyter cell."""

from io import StringIO
from pathlib import Path

from IPython.display import Image, display

from .namespace import Namespace
from .parser import ParsedResult


def _load_csv(name: str, content: str, ns: Namespace) -> None:
    """Try to load CSV from content (inline) or filesystem path."""
    import pandas as pd

    # Try content as path, then name as path
    for candidate in (content.strip(), name):
        for p in (Path(candidate), Path(candidate.strip("'\""))):
            try:
                if p.is_file():
                    df = pd.read_csv(str(p))
                    var_name = p.stem
                    ns.inject(var_name, df)
                    print(f"[{var_name}] {df.shape[0]} rows × {df.shape[1]} cols (from {p})")
                    return
            except Exception:
                pass

    # Try inline CSV content
    if content.strip():
        try:
            df = pd.read_csv(StringIO(content))
            var_name = name.rsplit(".", 1)[0]
            ns.inject(var_name, df)
            print(f"[{var_name}] {df.shape[0]} rows × {df.shape[1]} cols")
        except Exception as e:
            ns.inject(name, content)
            print(f"[{name}] csv parse error: {e}")
    else:
        print(f"[{name}] csv load skipped (empty content, file not found)")


def render_output(ns: Namespace, result: ParsedResult, skip_text: bool = False, inject_code: bool = False) -> None:
    """Print text, display images, inject DataFrames + code into user_ns."""
    print(result)

    if result.text and not skip_text:
        print(result.text)

    if result.code and inject_code:
        ns.set_next_input(f"# %%agent code\n{result.code}")

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
        elif name.endswith((".png", ".jpg", ".jpeg", ".svg")):
            # image file — try disk path first, then inline
            _display_image(name, content)
        else:
            if content.strip():
                ns.inject(name, content)
                print(f"[{name}] file loaded ({len(content)} bytes)")
            else:
                p = Path(name)
                if p.is_file():
                    text = p.read_text()
                    ns.inject(name, text)
                    print(f"[{name}] file loaded ({len(text)} bytes from {p})")
                else:
                    ns.inject(name, content)
                    print(f"[{name}] file loaded (empty)")


def _display_image(name: str, content: str) -> None:
    """Display an image file: disk path preferred, inline base64 fallback."""
    # Try content as path, then name as path
    for candidate in (content.strip().strip("'\""), name):
        p = Path(candidate)
        if p.is_file():
            display(Image(filename=str(p)))
            print(f"[{name}] image displayed ({p.stat().st_size} bytes)")
            return

    if content.strip():
        import base64
        try:
            display(Image(data=base64.b64decode(content.strip()), format="png", embed=True))
            print(f"[{name}] image displayed (inline base64)")
        except Exception:
            print(f"[{name}] image display error")
    else:
        print(f"[{name}] image display skipped (empty content, file not found)")
