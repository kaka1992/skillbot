(function () {
  "use strict";

  function getCellText(cmEl) {
    return cmEl ? (cmEl.textContent || "") : "";
  }

  function isSqlCell(cmEl) {
    return getCellText(cmEl).trimStart().startsWith("%%sql");
  }

  function getActiveCell() {
    var cells = document.querySelectorAll(".jp-Cell");
    var focused = document.activeElement;
    for (var i = 0; i < cells.length; i++) {
      if (cells[i].contains(focused)) return cells[i];
    }
    return cells.length > 0 ? cells[cells.length - 1] : null;
  }

  // ---- syntax highlighting (set cell language to SQL) ----

  function applySqlLanguage(cell) {
    if (!cell) return;
    // JupyterLab stores cell metadata via the model
    // Set language="sql" to trigger CodeMirror 6 SQL highlighting
    try {
      var notebook = document.querySelector(".jp-NotebookPanel");
      if (!notebook || !notebook.jupyterlab) return;

      // access the notebook widget's content
      var nbWidget = notebook.jupyterlab.shell.currentWidget;
      if (!nbWidget || !nbWidget.content) return;

      var notebookContent = nbWidget.content;
      // find the cell index
      var allCells = cell.parentNode ? cell.parentNode.querySelectorAll(":scope > .jp-Cell") : [];
      var cellIdx = -1;
      for (var i = 0; i < allCells.length; i++) {
        if (allCells[i] === cell) { cellIdx = i; break; }
      }
      if (cellIdx < 0) return;

      // get the cell widget from notebook's widgets list
      if (notebookContent.widgets && notebookContent.widgets[cellIdx]) {
        var cellWidget = notebookContent.widgets[cellIdx];
        // set metadata language to 'sql' — JupyterLab CM6 picks this up
        if (cellWidget.model && cellWidget.model.metadata) {
          cellWidget.model.metadata.set("language", "sql");
        }
      }
    } catch (e) {
      // fallback: CSS indicator
    }
  }

  function updateAllHighlights() {
    var cells = document.querySelectorAll(".jp-Cell");
    cells.forEach(function (cell) {
      var cmEl = cell.querySelector(".cm-content");
      if (cmEl && isSqlCell(cmEl)) {
        if (!cell.classList.contains("sql-cell")) {
          cell.classList.add("sql-cell");
          applySqlLanguage(cell);
        }
      } else {
        cell.classList.remove("sql-cell");
      }
    });
  }

  // ---- CSS fallback ----

  var _style = document.createElement("style");
  _style.textContent =
    ".jp-Cell.sql-cell .cm-line:first-child { color: #6a9955 !important; }";
  document.head.appendChild(_style);

  // ---- formatting via kernel ----

  function formatCell(cell) {
    var cmEl = cell.querySelector(".cm-content");
    if (!cmEl || !isSqlCell(cmEl)) return;

    var text = getCellText(cmEl);
    var lines = text.split("\n");
    var magic = lines[0];
    var sql = lines.slice(1).join("\n");
    if (!sql.trim()) return;

    var escapedSql = sql.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    var code = "from jupyter.dsl.sql import format_sql\nprint(format_sql('''" + escapedSql + "'''), end='')";

    var nbPanel = document.querySelector(".jp-NotebookPanel");
    if (!nbPanel || !nbPanel.jupyterlab) return;

    try {
      var sessionContext = nbPanel.jupyterlab.sessionContext;
      if (sessionContext && sessionContext.session) {
        var future = sessionContext.session.kernel.requestExecute({ code: code });
        future.done.then(function (reply) {
          var formatted = reply.content.text || sql;
          cmEl.textContent = magic + "\n" + formatted;
        });
      }
    } catch (e) {
      console.log("[%%sql] format error:", e);
    }
  }

  // ---- keyboard shortcut ----

  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "F") {
      var cell = getActiveCell();
      if (!cell) return;
      var cmEl = cell.querySelector(".cm-content");
      if (cmEl && isSqlCell(cmEl)) {
        e.preventDefault();
        e.stopPropagation();
        formatCell(cell);
      }
    }
  }, true);

  // ---- watch for changes ----

  setInterval(updateAllHighlights, 1000);
  document.addEventListener("focusin", function () { setTimeout(updateAllHighlights, 200); });

  console.log("[%%sql] highlighting + Ctrl+Shift+F loaded");
})();
