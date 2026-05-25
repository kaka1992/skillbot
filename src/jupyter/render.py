"""Render parsed agent output into Jupyter cell — unified output layer."""

import logging
import sys
from io import StringIO
from pathlib import Path

import base64

import pandas as pd
from IPython.display import Image, Markdown, display

from .namespace import Namespace, _describe
from .parser import ParsedResult

_log = logging.getLogger("jupyter.render")


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


def render_text(text: str) -> None:
    """Print result content to the cell (agent output, data)."""
    if text:
        print(text)


def render_markdown(text: str) -> None:
    """Render markdown text in Jupyter cell output."""
    if text.strip():
        display(Markdown(text))


def render_info(text: str) -> None:
    """Print status / progress / hints to the cell."""
    if text:
        print(text)


def _is_debug() -> bool:
    """Check if debug mode is on (via %agent_config --debug)."""
    return logging.getLogger("jupyter").isEnabledFor(logging.DEBUG)


def render_debug(text: str) -> None:
    """Print to cell only when debug is on."""
    if _is_debug() and text:
        print(text)


def render_error(text: str) -> None:
    """Print to stderr in red."""
    if text:
        print(f"\033[91m{text}\033[0m", file=sys.stderr)


def render_code(ns: Namespace, code: str, auto: bool = False, trace: bool = False) -> None:
    """Send code to frontend via comm; extension creates cell + optionally executes.

    *auto* tells the extension to execute the cell immediately.
    *trace* appends ``%agent --trace`` to the code.
    Cell visibility and execution are entirely handled by the frontend extension;
    nothing is done kernel-side.
    """
    if not code:
        return
    code = code.strip()
    if _is_sql(code) and not code.startswith("%%sql"):
        code = f"%%sql\n{code}"
    code = f"{code}\n# %%agent generate code"
    if trace:
        code += f"\n%agent --trace{' --auto' if auto else ''}"

    _log.info("render_code: %d chars auto=%s trace=%s", len(code), auto, trace)

    from .comm import send_cell_via_comm
    send_cell_via_comm(ns, code, auto=auto)


def render_variables(ns: Namespace) -> None:
    """Print available variables summary."""
    vars_dict = ns.vars()
    if vars_dict:
        print("Available variables:")
        for name, val in sorted(vars_dict.items()):
            print(f"  {_describe(name, val)}")


def render_image(data: bytes) -> None:
    """Display an inline image from raw bytes."""
    try:
        display(Image(data, format="png", embed=True))
    except Exception:
        pass


def render_sql_dataframe(ns: Namespace, data: dict, var_name: str):
    """Load SQL result into namespace as DataFrame. Returns the DataFrame or None."""
    sample = data.get("sample_data", [])
    if sample and len(sample) > 1:
        cols = sample[0]
        rows = sample[1:1001]  # max 1000 rows for preview display
        df_sample = pd.DataFrame(rows, columns=cols)
        render_text(f"[{var_name}] sample: {len(sample) - 1} rows x {len(cols)} cols" +
                    (" (showing first 1000)" if len(sample) > 1001 else ""))
        render_text(df_sample.to_string(max_rows=20, max_cols=10, max_colwidth=30))

    output_path = data.get("output_path", "")
    result_url = data.get("result_url", "")
    if output_path and Path(output_path).is_file():
        df = pd.read_csv(output_path)
        ns.inject(var_name, df)
        render_text(f"[{var_name}] loaded from {output_path}: {len(df)} rows x {len(df.columns)} cols")
        return df
    elif result_url:
        df = pd.read_csv(result_url)
        ns.inject(var_name, df)
        render_text(f"[{var_name}] loaded from {result_url}: {len(df)} rows x {len(df.columns)} cols")
        return df
    else:
        render_text(f"\033[91m[{var_name}] no data available\033[0m")
        return None


def render_output(ns: Namespace, result: ParsedResult,
                  skip_text: bool = False,
                  auto: bool = False, trace: bool = False) -> None:
    """Dispatch parsed agent result to render methods.

    Code (if any) is always injected. *auto* triggers auto-execution;
    *trace* appends ``%agent --trace`` to the last injected cell.
    """
    if result.text and not skip_text:
        if result.is_markdown:
            render_markdown(result.text)
        else:
            render_text(result.text)

    for name, content in result.csv.items():
        _load_csv(name, content, ns)

    for img_bytes in result.images:
        render_image(img_bytes)

    for path in result.files:
        p = Path(path)
        if path.endswith(".py"):
            if p.is_file():
                result.code_list.append(p.read_text())
        elif path.endswith(".csv"):
            _load_csv(path, "", ns)
        elif path.endswith((".png", ".jpg", ".jpeg", ".svg")):
            _display_image_file(path, "")
        elif p.is_file():
            ns.inject(path, p.read_text())
            render_text(f"[{path}] file loaded ({p.stat().st_size} bytes)")

    if result.code_list:
        from hook import HookRegistry, HookEvent
        context = {"code_list": result.code_list, "ns": ns}
        HookRegistry.dispatch(HookEvent.CODE_REVIEW, context)
        result.code_list = context["code_list"]

        for i, c in enumerate(result.code_list):
            is_last = (i == len(result.code_list) - 1)
            render_code(ns, c, auto=auto, trace=(trace and is_last))


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------


def _is_sql(code: str) -> bool:
    """Use sqlparse to detect if *code* is SQL (not Python)."""
    if code.startswith("%%"):
        return False
    import sqlparse
    stmt = sqlparse.parse(code.strip())
    if not stmt:
        return False
    return stmt[0].get_type() not in (None, "UNKNOWN")


def _load_csv(name: str, content: str, ns: Namespace) -> None:
    """Try to load CSV from content (inline) or filesystem path."""
    for candidate in (content.strip(), name):
        for p in (Path(candidate), Path(candidate.strip("'\""))):
            try:
                if p.is_file():
                    df = pd.read_csv(str(p))
                    var_name = p.stem
                    ns.inject(var_name, df)
                    render_text(f"[{var_name}] {df.shape[0]} rows x {df.shape[1]} cols (from {p})")
                    return
            except Exception:
                pass

    if content.strip():
        try:
            df = pd.read_csv(StringIO(content))
            var_name = name.rsplit(".", 1)[0]
            ns.inject(var_name, df)
            render_text(f"[{var_name}] {df.shape[0]} rows x {df.shape[1]} cols")
        except Exception as e:
            ns.inject(name, content)
            render_text(f"[{name}] csv parse error: {e}")
    else:
        render_text(f"[{name}] csv load skipped (empty content, file not found)")


def _display_image_file(name: str, content: str) -> None:
    """Display an image file: disk path preferred, inline base64 fallback."""
    for candidate in (content.strip().strip("'\""), name):
        p = Path(candidate)
        if p.is_file():
            display(Image(filename=str(p)))
            render_text(f"[{name}] image displayed ({p.stat().st_size} bytes)")
            return

    if content.strip():
        try:
            display(Image(data=base64.b64decode(content.strip()), format="png", embed=True))
            render_text(f"[{name}] image displayed (inline base64)")
        except Exception:
            render_text(f"[{name}] image display error")
    else:
        render_text(f"[{name}] image display skipped (empty content, file not found)")


