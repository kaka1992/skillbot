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

  // ---- access JupyterLab notebook widget ----

  function getApp() { return window._JUPYTERLAB; }

  function getCellEditorView(cell) {
    try {
      var app = getApp();
      if (!app || !app.shell) { console.log("[%%sql] no app/shell"); return null; }
      var nbWidget = app.shell.currentWidget;
      if (!nbWidget) { console.log("[%%sql] currentWidget is null"); return null; }
      if (!nbWidget.content) { console.log("[%%sql] currentWidget has no content prop, type=" + (nbWidget.constructor ? nbWidget.constructor.name : typeof nbWidget)); return null; }
      if (!nbWidget.content.widgets) { console.log("[%%sql] notebook content has no widgets, keys=" + Object.keys(nbWidget.content).join(",")); return null; }
      var widgets = nbWidget.content.widgets;
      var matched = 0, noHost = 0, noContain = 0;
      for (var i = 0; i < widgets.length; i++) {
        var w = widgets[i];
        if (!w || !w.editor) continue;
        matched++;
        var host = w.editor.host;
        if (!host) { noHost++; continue; }
        if (!cell.contains(host)) { noContain++; continue; }
        return w.editor.editor || null;
      }
      console.log("[%%sql] widget scan: matched=" + matched + " noHost=" + noHost + " noContain=" + noContain + " total=" + widgets.length);
      return null;
    } catch (e) { return null; }
  }

  // ---- SQL syntax highlighting via CM6 dynamic import ----

  function toggleSqlLanguage(cell, enable) {
    if (enable === !!cell.__sql_on) return;
    cell.__sql_on = enable;
    if (!enable) return;

    var view = getCellEditorView(cell);
    if (!view) { console.log("[%%sql] no EditorView (window._JUPYTERLAB=" + !!getApp() + ")"); return; }

    import("@codemirror/lang-sql").then(function (sqlMod) {
      return import("@codemirror/state").then(function (stateMod) {
        view.dispatch({
          effects: stateMod.StateEffect.appendConfig.of(
            sqlMod.sql({ upperCaseKeywords: true })
          ),
        });
        console.log("[%%sql] SQL language applied ✓");
      });
    }).catch(function (err) {
      console.log("[%%sql] import failed:", err.message);
    });
  }

  // ---- highlight scan ----

  function updateAllHighlights() {
    var cells = document.querySelectorAll(".jp-Cell");
    cells.forEach(function (cell) {
      var isSql = isSqlCell(cell);
      if (isSql) {
        if (!cell.classList.contains("sql-cell")) cell.classList.add("sql-cell");
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

    var app = getApp();
    if (!app || !app.shell) return;
    var nb = app.shell.currentWidget;
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
