"""Render parsed agent output into Jupyter cell."""

from io import StringIO

from IPython.display import Image, display

from .parser import ParsedResult


def render_output(shell, result: ParsedResult) -> None:
    """Print text, display images, inject DataFrames into user_ns."""
    # 1. text — auto-print
    if result.text:
        print(result.text)

    # 2. csv → DataFrame
    for name, content in result.csv.items():
        try:
            import pandas as pd
            df = pd.read_csv(StringIO(content))
            shell.user_ns[name] = df
            print(f"[{name}] {df.shape[0]} rows × {df.shape[1]} cols")
        except Exception as e:
            shell.user_ns[name] = content
            print(f"[{name}] csv parse error: {e}")

    # 3. images → direct display
    for img in result.images:
        try:
            display(Image(data=img))
        except Exception:
            pass

    # 4. files → inject raw content as variable
    for name, content in result.files.items():
        shell.user_ns[name] = content
        print(f"[{name}] file loaded ({len(content)} bytes)")
