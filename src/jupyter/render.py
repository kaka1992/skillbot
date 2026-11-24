"""Render parsed agent output into Jupyter cell — unified output layer."""

from __future__ import annotations

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


def prepare_cell_code(code: str, cell_type: str = "code") -> str:
    """Normalize generated code before it is materialized as a notebook Cell."""
    code = code.strip()
    marker = "\n# %%agent generate code"
    if cell_type != "markdown":
        if _is_sql(code) and not code.startswith("%%sql"):
            code = f"%%sql\n{code}"
        if marker not in code:
            code = f"{code}{marker}"
    return code


def render_code(ns: Namespace, code: str, auto: bool = False,
                cell_type: str = "code", replace_cell_id: str = "",
                on_cell_id: callable | None = None) -> None:
    """Send code to frontend via comm; extension creates cell + optionally executes."""
    if not code:
        return
    code = prepare_cell_code(code, cell_type)

    _log.info("render_code: %d chars auto=%s type=%s", len(code), auto, cell_type)

    from .comm import send_cell_via_comm
    send_cell_via_comm(ns, code, auto=auto, cell_type=cell_type,
                       replace_cell_id=replace_cell_id, on_cell_id=on_cell_id)


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
    df = None
    if sample and len(sample) > 1:
        cols = sample[0]
        rows = sample[1:1001]  # max 1000 rows for preview display
        df = pd.DataFrame(rows, columns=cols)
        render_text(f"[{var_name}] sample: {len(sample) - 1} rows x {len(cols)} cols" +
                    (" (showing first 1000)" if len(sample) > 1001 else ""))
        render_text(df.to_string(max_rows=20, max_cols=10, max_colwidth=30))

    output_path = data.get("output_path", "")
    result_url = data.get("result_url", "")
    if output_path and Path(output_path).is_file():
        df = pd.read_csv(output_path)
        render_text(f"[{var_name}] loaded from {output_path}: {len(df)} rows x {len(df.columns)} cols")
    elif result_url:
        df = pd.read_csv(result_url)
        render_text(f"[{var_name}] loaded from {result_url}: {len(df)} rows x {len(df.columns)} cols")

    if df is not None:
        ns.inject(var_name, df)
        return df
    render_text(f"\033[91m[{var_name}] no data available\033[0m")
    return None


def render_output(ns: Namespace, result: ParsedResult,
                  skip_text: bool = False,
                  auto: bool = False, plan_cell_id: str = "",
                  on_cell_id: callable | None = None,
                  session=None, cell_submitter: callable | None = None) -> int:
    """Dispatch parsed agent result to render methods.

    Returns the number of code cells handed to the dispatch path after
    .py file appends and code review. Execution outcome comes from Comm receipts.
    """
    if result.text and not skip_text:
        if result.is_markdown:
            render_markdown(result.text)
        else:
            render_text(result.text)

    if result.plan:
        content = "# %%plan\n\n" + result.plan
        def _on_plan_cell(cid, _code):
            ns._shell.user_ns["__plan_cell_id__"] = cid
        render_code(ns, content, cell_type="markdown", replace_cell_id=plan_cell_id,
                    on_cell_id=_on_plan_cell)

    for name, content in result.csv.items():
        _load_csv(name, content, ns)

    for img_bytes in result.images:
        render_image(img_bytes)

    for path in result.files:
        p = Path(path)
        if path.endswith(".py"):
            if p.is_file():
                try:
                    result.code_list.append(p.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    _log.warning("render_output: cannot read %s", path)
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
        HookRegistry.dispatch(HookEvent.CODE_REVIEW, context, session=session)
        result.code_list = context["code_list"]

        if result.code_list:
            if cell_submitter is not None:
                cell_submitter(result.code_list, auto)
            else:
                for c in result.code_list:
                    render_code(ns, c, auto=auto, on_cell_id=on_cell_id)

    return len(result.code_list)


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
    t = stmt[0]
    if t.get_type() in (None, "UNKNOWN"):
        return False
    # sqlparse reports SELECT even for Python like `select = [1,2,3]` or
    # `select[0]`; a real SQL keyword is never followed by `=` / `[`
    seen = 0
    for tok in t.tokens:
        if tok.is_whitespace:
            continue
        seen += 1
        if seen == 1:
            continue  # the leading keyword itself
        if (str(tok.ttype).startswith("Token.Operator")
                or tok.ttype == sqlparse.tokens.Punctuation
                or getattr(tok, "value", "").startswith("[")):
            return False
        break
    return True


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
