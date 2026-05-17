(function () {
  "use strict";

  // ---- helpers ----

  function isSqlCell(cell) {
    try {
      return cell.getText().trimStart().startsWith("%%sql");
    } catch (e) {
      return false;
    }
  }

  function getActiveCell() {
    // JupyterLab / Notebook v7
    var nb = document.querySelector(".jp-Notebook");
    if (nb && nb.jupyterlab) {
      var panel = document.querySelector(".jp-NotebookPanel");
      if (!panel) return null;
      // get active cell from the notebook panel widget
      try {
        var cells = document.querySelectorAll(".jp-Cell");
        var focused = document.activeElement;
        for (var i = 0; i < cells.length; i++) {
          if (cells[i].contains(focused)) return cells[i];
        }
        return cells[cells.length - 1];
      } catch (e) {
        return null;
      }
    }
    return null;
  }

  function getCellText(cell) {
    var cmContent = cell.querySelector(".cm-content");
    if (cmContent) return cmContent.textContent || "";
    return "";
  }

  function getCellMagicLine(cell) {
    var text = getCellText(cell);
    var lines = text.split("\n");
    return lines[0] || "";
  }

  function getCellSql(cell) {
    var text = getCellText(cell);
    var lines = text.split("\n");
    return { magic: lines[0], sql: lines.slice(1).join("\n") };
  }

  // ---- formatting via kernel ----

  function formatCell(cell) {
    var sq = getCellSql(cell);
    if (!sq.magic.startsWith("%%sql")) return;

    var sql = sq.sql.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    var code = "from jupyter.dsl.sql import format_sql\nprint(format_sql('''" + sql + "'''), end='')";

    // access kernel via JupyterLab notebook
    var nbPanel = document.querySelector(".jp-NotebookPanel");
    if (!nbPanel || !nbPanel.jupyterlab) return;

    try {
      var sessionContext = nbPanel.jupyterlab.sessionContext;
      if (sessionContext && sessionContext.session) {
        var future = sessionContext.session.kernel.requestExecute({ code: code });
        future.done.then(function (reply) {
          var formatted = reply.content.text || sq.sql;
          var newText = sq.magic + "\n" + formatted;
          // set cell text via NotebookActions-like approach
          var cm = cell.querySelector(".cm-content");
          if (cm) cm.textContent = newText;
        });
      }
    } catch (e) {
      console.log("[%%sql] format error:", e);
    }
  }

  // ---- syntax highlighting via CSS ----

  var _style = document.createElement("style");
  _style.textContent =
    ".jp-Cell.sql-highlight .cm-content { background: #f7f9fc !important; }";
  document.head.appendChild(_style);

  function updateSqlHighlight() {
    var cells = document.querySelectorAll(".jp-Cell");
    cells.forEach(function (cell) {
      var text = getCellText(cell);
      if (text.trimStart().startsWith("%%sql")) {
        cell.classList.add("sql-highlight");
      } else {
        cell.classList.remove("sql-highlight");
      }
    });
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

  // ---- watch for cell changes ----

  setInterval(updateSqlHighlight, 2000);  // periodic check
  document.addEventListener("focusin", updateSqlHighlight);
  document.addEventListener("click", function () {
    setTimeout(updateSqlHighlight, 100);
  });

  console.log("[%%sql] highlighting + Ctrl+Shift+F loaded (injected)");
})();
