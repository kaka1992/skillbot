(function () {
  "use strict";

  // cache for SQL language extension
  var _sqlLang = null;
  var _sqlCompartment = null;
  var _loadedExtensions = new WeakSet();

  function getCodeMirrorSQL() {
    // Try to get SQL language from CodeMirror 6 bundled in JupyterLab
    if (_sqlLang) return _sqlLang;
    try {
      // JupyterLab exposes CM6 via its plugin system
      var cmPackages = window["@codemirror/lang-sql"];
      if (!cmPackages) {
        // try alternate paths
        var jpWidgets = document.querySelector(".jp-NotebookPanel");
        if (jpWidgets && jpWidgets.jupyterlab) {
          // Try to access via the service manager
          var sm = jpWidgets.jupyterlab.serviceManager;
        }
      }
    } catch (e) {}
    return null;
  }

  function getCellText(cmEl) { return cmEl ? (cmEl.textContent || "") : ""; }
  function isSqlCell(cmEl) { return getCellText(cmEl).trimStart().startsWith("%%sql"); }

  function getActiveCell() {
    var cells = document.querySelectorAll(".jp-Cell");
    var focused = document.activeElement;
    for (var i = 0; i < cells.length; i++) {
      if (cells[i].contains(focused)) return cells[i];
    }
    return cells.length > 0 ? cells[cells.length - 1] : null;
  }

  // ---- syntax highlighting via CodeMirror 6 EditorView ----

  function setSqlMode(cell) {
    if (!cell || _loadedExtensions.has(cell)) return;
    var cmEl = cell.querySelector(".cm-content");
    if (!cmEl || !isSqlCell(cmEl)) return;

    try {
      // Access CodeMirror 6 EditorView via JupyterLab cell widget
      var notebook = document.querySelector(".jp-NotebookPanel");
      if (!notebook || !notebook.jupyterlab) return;

      var nbWidget = notebook.jupyterlab.shell.currentWidget;
      if (!nbWidget || !nbWidget.content) return;

      var allCells = cell.parentNode ? Array.from(cell.parentNode.querySelectorAll(":scope > .jp-Cell")) : [];
      var cellIdx = allCells.indexOf(cell);
      if (cellIdx < 0) return;

      var cellWidget = nbWidget.content.widgets && nbWidget.content.widgets[cellIdx];
      if (!cellWidget) return;

      // Try to access the CodeMirror 6 EditorView
      // JupyterLab stores it at cellWidget.editor._editor (private) or cellWidget.editor.editor
      var editor = cellWidget.editor;
      if (!editor) return;

      // The editor might be CodeMirrorEditor wrapping CM6
      var cmView = editor._editor || editor.editor;
      if (!cmView || !cmView.state) return;

      // Get language compartment — JupyterLab uses this to manage per-cell language
      // Try to set language via dispatch with a SQL language extension
      if (cmView.dispatch && editor._languageCompartment) {
        // JupyterLab >=4.2 has _languageCompartment on CodeMirrorEditor
        var compartment = editor._languageCompartment;
        var sqlLang = getCodeMirrorSQL();
        if (sqlLang) {
          cmView.dispatch({ effects: compartment.reconfigure(sqlLang()) });
          _loadedExtensions.add(cell);
        }
      }
    } catch (e) {
      // Fall through to metadata approach
    }

    // Fallback: set metadata + CSS
    try {
      var notebook = document.querySelector(".jp-NotebookPanel");
      if (!notebook || !notebook.jupyterlab) return;
      var nbWidget = notebook.jupyterlab.shell.currentWidget;
      if (!nbWidget || !nbWidget.content) return;
      var allCells = cell.parentNode ? Array.from(cell.parentNode.querySelectorAll(":scope > .jp-Cell")) : [];
      var cellIdx = allCells.indexOf(cell);
      if (cellIdx < 0) return;
      var cellWidget = nbWidget.content.widgets && nbWidget.content.widgets[cellIdx];
      if (cellWidget && cellWidget.model && cellWidget.model.metadata) {
        cellWidget.model.metadata.set("language", "sql");
      }
    } catch (e2) {}
  }

  function updateAllHighlights() {
    var cells = document.querySelectorAll(".jp-Cell");
    cells.forEach(function (cell) {
      var cmEl = cell.querySelector(".cm-content");
      if (cmEl && isSqlCell(cmEl)) {
        if (!cell.classList.contains("sql-cell")) {
          cell.classList.add("sql-cell");
        }
        setSqlMode(cell);
      } else {
        cell.classList.remove("sql-cell");
      }
    });
  }

  // ---- CSS ----

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
        sessionContext.session.kernel.requestExecute({ code: code }).done
          .then(function (reply) {
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

  // ---- watch ----

  setInterval(updateAllHighlights, 1000);
  document.addEventListener("focusin", function () { setTimeout(updateAllHighlights, 200); });

  console.log("[%%sql] highlighting + Ctrl+Shift+F loaded");
})();
