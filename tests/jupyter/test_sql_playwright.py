"""Playwright E2E tests for %%sql cell highlighting + formatting."""

import json
import time
import urllib.request

JUPYTER_URL = "http://localhost:8888"
JUPYTER_TOKEN = "15b932e5827a8ccc38d2fe48417fc36a863c91af5ec72ce0"
_counter = 0


def _api(path, data=None, method=None):
    """Call Jupyter REST API."""
    url = f"{JUPYTER_URL}/api{path}?token={JUPYTER_TOKEN}"
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                  method=method or "GET")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read()) if resp.status != 204 else {}


def _create_notebook():
    """Create unique notebook via API."""
    global _counter
    _counter += 1
    path = f"TestSqlPW_{_counter}.ipynb"
    nb = json.dumps({
        "type": "notebook",
        "content": {"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5},
    }).encode()
    _api(f"/contents/{path}", data=nb, method="PUT")
    return path


def _open_notebook(page, path):
    """Open notebook and wait for kernel."""
    url = f"{JUPYTER_URL}/notebooks/{path}?token={JUPYTER_TOKEN}"
    page.goto(url, timeout=30000)
    # wait for notebook to load
    try:
        page.wait_for_selector(".jp-NotebookPanel", timeout=10000)
    except Exception:
        try:
            page.wait_for_selector("#notebook-container", timeout=10000)
        except Exception:
            page.wait_for_selector(".CodeMirror", timeout=10000)
    # wait for kernel ready
    time.sleep(3)


def _focus_cell(page):
    """Focus the first cell by clicking on the editor area."""
    # Jupyter Notebook v7 (JupyterLab-based) uses .cm-editor, v6 uses .CodeMirror
    for selector in [".cm-editor", ".CodeMirror", ".jp-CodeMirrorEditor"]:
        try:
            page.wait_for_selector(selector, timeout=5000)
            page.click(selector)
            time.sleep(0.5)
            return
        except Exception:
            continue
    raise RuntimeError("Could not find editor element")


def _cell_text(page):
    """Get current cell text (handles CodeMirror 5 and 6)."""
    return page.evaluate("""
        () => {
            // CodeMirror 5 (.CodeMirror with .CodeMirror API)
            const cm5 = document.querySelectorAll(".CodeMirror");
            for (const el of cm5) {
                if (el.CodeMirror && el.CodeMirror.getValue().trim())
                    return el.CodeMirror.getValue();
            }
            // CodeMirror 6 (.cm-editor with .cm-content)
            const cm6 = document.querySelectorAll(".cm-editor .cm-content");
            for (const el of cm6) {
                const text = el.textContent || "";
                if (text.trim()) return text;
            }
            return "";
        }
    """)


class TestSqlCellBasic:
    """Basic %%sql cell text entry."""

    def test_sql_cell_text_roundtrip(self):
        from playwright.sync_api import sync_playwright

        path = _create_notebook()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            _open_notebook(page, path)
            _focus_cell(page)

            page.keyboard.type("%%sql\nSELECT * FROM users")
            time.sleep(0.5)

            text = _cell_text(page)
            assert "%%sql" in (text or ""), f"cell text: '{text}'"
            assert "SELECT" in (text or "")
            assert "users" in (text or "")
            browser.close()

    def test_multiple_lines(self):
        from playwright.sync_api import sync_playwright

        path = _create_notebook()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            _open_notebook(page, path)
            _focus_cell(page)

            page.keyboard.type("%%sql --var df1 --poll 30\nSELECT a, b\nFROM my_table\nWHERE c > 100")
            time.sleep(0.5)

            text = _cell_text(page)
            assert "%%sql --var df1 --poll 30" in (text or ""), f"cell text: '{text}'"
            assert "SELECT a, b" in (text or "")
            assert "FROM my_table" in (text or "")
            browser.close()


class TestSqlFormatting:
    """Test kernel-side format_sql."""

    def test_kernel_format_sql(self):
        from playwright.sync_api import sync_playwright

        path = _create_notebook()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            _open_notebook(page, path)
            _focus_cell(page)

            code = (
                "from jupyter.dsl.sql import format_sql\n"
                "result = format_sql('select a,b from t where x=1')\n"
                "assert 'SELECT' in result, f'Got: {repr(result)}'\n"
                "assert 'FROM' in result\n"
                "print('OK')"
            )
            page.keyboard.type(code)
            time.sleep(0.5)

            page.keyboard.press("Control+Enter")
            time.sleep(5)

            # check output — try multiple selector patterns
            output = page.evaluate("""
                () => {
                    const cells = document.querySelectorAll(".jp-Cell, .cell, [data-cell-id]");
                    for (const cell of cells) {
                        const outputs = cell.querySelectorAll(
                            ".jp-OutputArea-output, .jp-RenderedText, .output_text, .output_stream, pre"
                        );
                        for (const out of outputs) {
                            const text = out.textContent || "";
                            if (text.includes("OK")) return text;
                        }
                    }
                    return "";
                }
            """)
            assert "OK" in (output or ""), f"output: '{output}'"
            browser.close()
