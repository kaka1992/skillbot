(function () {
  "use strict";

  // ---- helpers ----

  function getCellText(cmEl) {
    if (!cmEl) return "";
    return cmEl.textContent || "";
  }

  function isSqlCell(cmEl) {
    return getCellText(cmEl).trimStart().startsWith("%%sql");
  }

  function getCellSql(cell) {
    var cmEl = cell.querySelector(".cm-content");
    var text = getCellText(cmEl);
    var lines = text.split("\n");
    return { magic: lines[0], sql: lines.slice(1).join("\n"), cmEl: cmEl };
  }

  function getActiveCell() {
    var cells = document.querySelectorAll(".jp-Cell");
    var focused = document.activeElement;
    for (var i = 0; i < cells.length; i++) {
      if (cells[i].contains(focused)) return cells[i];
    }
    return cells.length > 0 ? cells[cells.length - 1] : null;
  }

  // ---- syntax highlighting (CodeMirror 6) ----

  function setSqlHighlight(cell) {
    var cmEl = cell.querySelector(".cm-content");
    if (!cmEl || !isSqlCell(cmEl)) return false;

    // access the CodeMirror 6 EditorView via JupyterLab cell widget
    var cmView = cmEl.closest(".cm-editor");
    if (!cmView) return false;

    // find EditorView instance attached to the DOM wrapper
    try {
      // CodeMirror 6 stores the view on the DOM node
      var view = cmView.cmView ? cmView.cmView.view : null;
      // alternative: find via __jupyterlab editor property
      if (!view) {
        // walk up to find the cell widget's editor
        var notebookEl = cell.closest(".jp-NotebookPanel");
        if (notebookEl) {
          // try accessing via JupyterLab's global registry
          var jpLab = notebookEl.jupyterlab || window._jupyterlab;
        }
      }

      // Use CodeMirror 6 Compartment API if view is accessible
      if (view && view.dispatch) {
        // Try to set SQL language — need to import from @codemirror/lang-sql
        // Since we can't import, use a simpler approach: set the language name
        try {
          var cm = view.state;
          // CodeMirror 6 doesn't expose setMode directly; use facets
          // Fallback: configure the cell editor via JupyterLab commands
          var id = cell.getAttribute("id") || cell.getAttribute("data-id");
          if (id && window._jpLAB) {
            window._jpLAB.commands.execute("notebook:change-cell-to-code");
          }
        } catch (e) {
          // ignore
        }
      }
    } catch (e) {
      // ignore, fall back to CSS
    }

    // CSS fallback: simple visual indicator
    cell.classList.add("sql-cell");
    return true;
  }

  // ---- CSS ----

  var _style = document.createElement("style");
  _style.textContent =
    ".jp-Cell.sql-cell .cm-line:first-child { color: #6a9955 !important; font-style: italic; }";
  document.head.appendChild(_style);

  function updateAllHighlights() {
    var cells = document.querySelectorAll(".jp-Cell");
    cells.forEach(function (cell) {
      var cmEl = cell.querySelector(".cm-content");
      if (cmEl && isSqlCell(cmEl)) {
        cell.classList.add("sql-cell");
        setSqlHighlight(cell);
      } else {
        cell.classList.remove("sql-cell");
      }
    });
  }

  // ---- formatting via kernel ----

  function formatCell(cell) {
    var sq = getCellSql(cell);
    if (!sq.magic.startsWith("%%sql")) return;

    var sql = sq.sql.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    var code = "from jupyter.dsl.sql import format_sql\nprint(format_sql('''" + sql + "'''), end='')";

    var nbPanel = document.querySelector(".jp-NotebookPanel");
    if (!nbPanel || !nbPanel.jupyterlab) return;

    try {
      var sessionContext = nbPanel.jupyterlab.sessionContext;
      if (sessionContext && sessionContext.session) {
        var future = sessionContext.session.kernel.requestExecute({ code: code });
        future.done.then(function (reply) {
          var formatted = reply.content.text || sq.sql;
          var newText = sq.magic + "\n" + formatted;
          if (sq.cmEl) sq.cmEl.textContent = newText;
        });
      }
    } catch (e) {
      console.log("[%%sql] format error:", e);
    }
  }

  // ---- keyboard shortcut ----

  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "F") {
      e.preventDefault();
      e.stopPropagation();
      var cell = getActiveCell();
      if (cell) formatCell(cell);
    }
  }, true);

  // ---- watch for changes ----

  setInterval(updateAllHighlights, 1000);
  document.addEventListener("focusin", function () { setTimeout(updateAllHighlights, 200); });

  console.log("[%%sql] highlighting + Ctrl+Shift+F loaded");
})();
