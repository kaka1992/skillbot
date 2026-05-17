(function () {
  "use strict";

  function isSqlCell(cell) {
    try {
      var cmEl = cell.querySelector(".cm-content");
      if (!cmEl) return false;
      var text = cmEl.textContent || "";
      var match = text.trimStart().startsWith("%%sql");
      if (match) console.log("[%%sql] isSqlCell: YES, text starts with:", text.substring(0, 20));
      return match;
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
      // Try multiple paths to access the JupyterLab notebook widget:
      // 1) window._jupyterlab 2) .jp-LabShell 3) document jupyterlab attribute
      var nbWidget = null;

      // Path 1: global JupyterLab instance
      var app = window.jupyterlab || window._jupyterlab || window.jupyterapp;
      console.log("[%%sql] path1: app=" + typeof app + " hasShell=" + !!(app && app.shell));
      if (app && app.shell) {
        nbWidget = app.shell.currentWidget;
        console.log("[%%sql] path1: nbWidget=" + (nbWidget ? "found" : "null"));
      }

      // Path 2: find via LabShell DOM
      if (!nbWidget) {
        var shell = document.querySelector(".jp-LabShell");
        console.log("[%%sql] path2: .jp-LabShell=" + !!shell);
        if (shell) {
          var fiberKey = Object.keys(shell).find(function (k) { return k.startsWith("__reactFiber"); });
          console.log("[%%sql] path2: fiberKey=" + !!fiberKey);
          if (fiberKey) {
            var fiber = shell[fiberKey];
            while (fiber) {
              if (fiber.stateNode && fiber.stateNode.shell) {
                nbWidget = fiber.stateNode.shell.currentWidget;
                console.log("[%%sql] path2: found via fiber");
                break;
              }
              fiber = fiber.return;
            }
          }
        }
      }

      if (!nbWidget) {
        console.log("[%%sql] getCellEditorView: could not find notebook widget");
        return null;
      }
      if (!nbWidget.content || !nbWidget.content.widgets) {
        console.log("[%%sql] getCellEditorView: notebook has no content/widgets");
        return null;
      }

      var widgets = nbWidget.content.widgets;
      for (var i = 0; i < widgets.length; i++) {
        var w = widgets[i];
        if (!w || !w.editor) continue;
        var host = w.editor.host;
        if (!host) continue;
        if (cell.contains(host)) {
          return w.editor.editor || null;
        }
      }
      return null;
    } catch (e) {
      console.log("[%%sql] getCellEditorView error:", e.message);
      return null;
    }
  }

  function toggleSqlLanguage(cell, enable) {
    console.log("[%%sql] toggleSqlLanguage: enable=" + enable + " __sql_on=" + cell.__sql_on);
    if (enable === !!cell.__sql_on) {
      console.log("[%%sql] toggleSqlLanguage: SKIP (already " + enable + ")");
      return;
    }
    cell.__sql_on = enable;

    if (!enable) {
      console.log("[%%sql] toggleSqlLanguage: return (disable)");
      return;
    }

    console.log("[%%sql] toggleSqlLanguage: calling getCellEditorView...");
    var view = getCellEditorView(cell);
    if (!view) {
      console.log("[%%sql] no EditorView for cell");
      return;
    }

    console.log("[%%sql] toggleSqlLanguage: got EditorView, calling import()...");

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
    var sqlCount = 0;
    cells.forEach(function (cell) {
      var isSql = isSqlCell(cell);
      if (isSql) {
        sqlCount++;
        var hadClass = cell.classList.contains("sql-cell");
        if (!hadClass) {
          cell.classList.add("sql-cell");
        }
        toggleSqlLanguage(cell, true);
      } else {
        cell.classList.remove("sql-cell");
      }
    });
    if (sqlCount > 0) console.log("[%%sql] updateAllHighlights: found " + sqlCount + " sql cells, cells=" + cells.length);
  }

  // ---- Ctrl+Shift+F formatting via kernel ----

  function getNotebookSession() {
    var app = window.jupyterlab || window._jupyterlab;
    if (app && app.shell && app.shell.currentWidget) {
      var nb = app.shell.currentWidget;
      if (nb && nb.content && nb.sessionContext) {
        return nb.sessionContext.session;
      }
    }
    return null;
  }

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

    var session = getNotebookSession();
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

  console.log("[%%sql] highlighting + Ctrl+Shift+F loaded v2");
})();
