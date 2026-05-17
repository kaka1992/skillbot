(function () {
  "use strict";

  // ---- helpers ----

  function isSqlCell(cell) {
    try {
      var cmEl = cell.querySelector(".cm-content");
      return cmEl && (cmEl.textContent || "").trimStart().startsWith("%%sql");
    } catch (e) { return false; }
  }

  function getActiveCell() {
    var cells = document.querySelectorAll(".jp-Cell");
    var focused = document.activeElement;
    for (var i = 0; i < cells.length; i++) {
      if (cells[i].contains(focused)) return cells[i];
    }
    return cells.length > 0 ? cells[cells.length - 1] : null;
  }

  function getCellEditorView(cell) {
    try {
      // JupyterLab stores the notebook widget hierarchy on the DOM
      var nbPanel = document.querySelector(".jp-NotebookPanel");
      if (!nbPanel || !nbPanel.jupyterlab) return null;
      var notebook = nbPanel.jupyterlab.shell.currentWidget;
      if (!notebook || !notebook.content) return null;
      var cellIdx = Array.from(cell.parentNode.querySelectorAll(":scope > .jp-Cell")).indexOf(cell);
      if (cellIdx < 0) return null;
      var cellWidget = notebook.content.widgets[cellIdx];
      if (!cellWidget || !cellWidget.editor) return null;
      // CodeMirrorEditor.editor is the public EditorView
      return cellWidget.editor.editor || null;
    } catch (e) { return null; }
  }

  function toggleSqlLanguage(cell, enable) {
    var view = getCellEditorView(cell);
    if (!view) return;
    if (view.__sql_applied === enable) return;
    view.__sql_applied = enable;

    if (enable) {
      // Dynamic import @codemirror/lang-sql from JupyterLab's federated modules
      import("@codemirror/lang-sql").then(function (mod) {
        import("@codemirror/state").then(function (stateMod) {
          try {
            view.dispatch({
              effects: stateMod.StateEffect.appendConfig.of(mod.sql({ upperCaseKeywords: true }))
            });
          } catch (e) { /* ignore */ }
        });
      }).catch(function () { /* module not available */ });
    }
  }

  // ---- highlight scan ----

  function updateAllHighlights() {
    var cells = document.querySelectorAll(".jp-Cell");
    cells.forEach(function (cell) {
      var isSql = isSqlCell(cell);
      if (isSql && !cell.classList.contains("sql-cell")) {
        cell.classList.add("sql-cell");
        toggleSqlLanguage(cell, true);
      } else if (!isSql && cell.classList.contains("sql-cell")) {
        cell.classList.remove("sql-cell");
      }
    });
  }

  // ---- Ctrl+Shift+F formatting via kernel ----

  function formatActiveCell() {
    var cell = getActiveCell();
    if (!cell || !isSqlCell(cell)) return;
    var cmEl = cell.querySelector(".cm-content");
    if (!cmEl) return;
    var text = cmEl.textContent || "";
    var lines = text.split("\n");
    var magic = lines[0];
    var sql = lines.slice(1).join("\n");
    if (!sql.trim()) return;

    var nbPanel = document.querySelector(".jp-NotebookPanel");
    if (!nbPanel || !nbPanel.jupyterlab) return;
    var nb = nbPanel.jupyterlab.shell.currentWidget;
    if (!nb || !nb.content || !nb.sessionContext) return;
    var session = nb.sessionContext.session;
    if (!session || !session.kernel) return;

    var escaped = sql.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    session.kernel.requestExecute({
      code: "from jupyter.dsl.sql import format_sql\nprint(format_sql('''" + escaped + "'''), end='')"
    }).done.then(function (reply) {
      var formatted = reply.content.text || sql;
      cmEl.textContent = magic + "\n" + formatted;
    }).catch(function () {});
  }

  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "F") {
      e.preventDefault();
      e.stopPropagation();
      formatActiveCell();
    }
  }, true);

  // ---- watch ----

  setInterval(updateAllHighlights, 1000);
  document.addEventListener("focusin", function () { setTimeout(updateAllHighlights, 200); });

  console.log("[%%sql] highlighting + Ctrl+Shift+F loaded");
})();
