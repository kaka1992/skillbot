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

  function getCellEditorView(cell) {
    try {
      // Find all window keys containing 'lab' or 'Lab' (case insensitive)
      var labKeys = Object.keys(window).filter(function(k){return k.toLowerCase().indexOf('lab')>=0});
      console.log("[%%sql] window keys with 'lab':", JSON.stringify(labKeys));

      // Check each for a usable app object
      for (var i = 0; i < labKeys.length; i++) {
        var v = window[labKeys[i]];
        if (!v || typeof v !== "object") continue;
        if (v.shell && v.commands) {
          console.log("[%%sql] found app: window." + labKeys[i]);
          var nbWidget = v.shell.currentWidget;
          if (nbWidget && nbWidget.content && nbWidget.content.widgets) {
            var widgets = nbWidget.content.widgets;
            for (var j = 0; j < widgets.length; j++) {
              var w = widgets[j];
              if (!w || !w.editor) continue;
              var host = w.editor.host;
              if (host && cell.contains(host)) return w.editor.editor || null;
            }
          }
        }
      }
      console.log("[%%sql] no usable app found in lab keys");
      return null;
    } catch (e) { console.log("[%%sql] error:", e.message); return null; }
  }

  // ---- SQL syntax highlighting via CM6 dynamic import ----

  function toggleSqlLanguage(cell, enable) {
    if (enable === !!cell.__sql_on) return;
    cell.__sql_on = enable;
    if (!enable) return;

    var view = getCellEditorView(cell);
    if (!view) { console.log("[%%sql] no EditorView"); return; }

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

    // Find session via React fiber (same approach as getCellEditorView)
    var panel = document.querySelector(".jp-NotebookPanel");
    if (!panel) return;
    var fiberKey = Object.keys(panel).find(function(k){return k.startsWith("__reactFiber")||k.startsWith("__reactInternalInstance")});
    if (!fiberKey) return;
    var fiber = panel[fiberKey], nb = null;
    while (fiber) {
      var sn = fiber.stateNode;
      if (sn && sn.content && sn.sessionContext) { nb = sn; break; }
      fiber = fiber["return"];
    }
    if (!nb || !nb.sessionContext) return;
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
