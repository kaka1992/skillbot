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

  // ---- highlight scan ----

  function updateAllHighlights() {
    document.querySelectorAll(".jp-Cell").forEach(function (cell) {
      cell.classList.toggle("sql-cell", isSqlCell(cell));
    });
  }

  // ---- Ctrl+Shift+F formatting ----

  function formatActiveCell() {
    var cell = getActiveCell();
    if (!cell || !isSqlCell(cell)) return;
    var cmEl = cell.querySelector(".cm-content");
    if (!cmEl) return;
    var text = cmEl.textContent || "";
    var lines = text.split("\n");
    var sql = lines.slice(1).join("\n");
    if (!sql.trim()) return;

    // Find kernel via JupyterLab's kernel status indicator
    var statusBar = document.querySelector(".jp-NotebookPanel .jp-Toolbar-item .jp-KernelName");
    var nbPanel = document.querySelector(".jp-NotebookPanel");
    if (!nbPanel) return;

    // Access notebook session via Lumino widget — stored on DOM as __widget
    var session = null;
    function walk(el) {
      if (!el || session) return;
      try {
        if (el._notebookModel && el._notebookModel.sharedModel) {
          // This is the notebook widget
          // Session is on parent notebook panel widget
        }
      } catch (e) {}
      walk(el.parentElement);
    }
    walk(nbPanel);

    // Fallback: find kernel via any output area
    if (!session) {
      var outputs = document.querySelectorAll(".jp-OutputArea");
      for (var i = 0; i < outputs.length; i++) {
        try {
          var w = outputs[i].__widget || outputs[i]._widget;
          if (w && w.sessionContext && w.sessionContext.session) {
            session = w.sessionContext.session;
            break;
          }
        } catch (e) {}
      }
    }

    if (!session || !session.kernel) return;
    var escaped = sql.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    session.kernel.requestExecute({
      code: "from jupyter.dsl.sql import format_sql\nprint(format_sql('''" + escaped + "'''), end='')"
    }).done.then(function (reply) {
      var formatted = reply.content.text || sql;
      cmEl.textContent = lines[0] + "\n" + formatted;
    }).catch(function () {});
  }

  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "F") {
      e.preventDefault();
      e.stopPropagation();
      formatActiveCell();
    }
  }, true);

  // ---- CSS ----
  var s = document.createElement("style");
  s.textContent = ".jp-Cell.sql-cell .cm-line:first-child { color: #6a9955 !important; }";
  document.head.appendChild(s);

  // ---- watch ----
  setInterval(updateAllHighlights, 1000);
  document.addEventListener("focusin", function () { setTimeout(updateAllHighlights, 200); });

  console.log("[%%sql] highlighting + Ctrl+Shift+F loaded");
})();
