(function () {
  "use strict";

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
      var nbPanel = document.querySelector(".jp-NotebookPanel");
      if (!nbPanel)        { console.log("[%%sql] getCellEditorView: no .jp-NotebookPanel"); return null; }
      if (!nbPanel.jupyterlab) { console.log("[%%sql] getCellEditorView: no jupyterlab on panel"); return null; }
      var notebook = nbPanel.jupyterlab.shell.currentWidget;
      if (!notebook)        { console.log("[%%sql] getCellEditorView: no currentWidget"); return null; }
      if (!notebook.content) { console.log("[%%sql] getCellEditorView: no notebook.content"); return null; }
      if (!notebook.content.widgets) { console.log("[%%sql] getCellEditorView: no widgets array"); return null; }

      var widgets = notebook.content.widgets;
      for (var i = 0; i < widgets.length; i++) {
        var w = widgets[i];
        if (!w || !w.editor) continue;
        var host = w.editor.host;
        if (!host) { console.log("[%%sql] getCellEditorView: widget " + i + " has no editor.host"); continue; }
        if (cell.contains(host)) {
          var view = w.editor.editor || null;
          if (!view) console.log("[%%sql] getCellEditorView: found cell but w.editor.editor is null");
          return view;
        }
      }
      console.log("[%%sql] getCellEditorView: no widget matched cell (widgets=" + widgets.length + ")");
      return null;
    } catch (e) {
      console.log("[%%sql] getCellEditorView error:", e.message);
      return null;
    }
  }

  function toggleSqlLanguage(cell, enable) {
    if (enable === !!cell.__sql_on) return;
    cell.__sql_on = enable;

    if (!enable) return;

    var view = getCellEditorView(cell);
    if (!view) {
      console.log("[%%sql] no EditorView for cell");
      return;
    }

    import("@codemirror/lang-sql")
      .then(function (sqlMod) {
        return import("@codemirror/state").then(function (stateMod) {
          return { sqlMod: sqlMod, stateMod: stateMod };
        });
      })
      .then(function (mods) {
        view.dispatch({
          effects: mods.stateMod.StateEffect.appendConfig.of(
            mods.sqlMod.sql({ upperCaseKeywords: true })
          ),
        });
        console.log("[%%sql] SQL language applied to cell");
      })
      .catch(function (err) {
        console.log("[%%sql] import failed:", err.message);
      });
  }

  // ---- highlight scan ----

  function updateAllHighlights() {
    var cells = document.querySelectorAll(".jp-Cell");
    cells.forEach(function (cell) {
      var isSql = isSqlCell(cell);
      if (isSql) {
        if (!cell.classList.contains("sql-cell")) {
          cell.classList.add("sql-cell");
        }
        toggleSqlLanguage(cell, true);
      } else {
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

  // ---- CSS indicator ----
  var _style = document.createElement("style");
  _style.textContent = ".jp-Cell.sql-cell .cm-line:first-child { color: #6a9955 !important; }";
  document.head.appendChild(_style);

  // ---- watch ----
  setInterval(updateAllHighlights, 1000);
  document.addEventListener("focusin", function () { setTimeout(updateAllHighlights, 200); });

  console.log("[%%sql] highlighting + Ctrl+Shift+F loaded");
})();
