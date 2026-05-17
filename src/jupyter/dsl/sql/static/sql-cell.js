/**
 * %%sql cell support: syntax highlighting + Ctrl+Shift+F formatting.
 * JupyterLab / Notebook v7 plugin — auto-start via labextension.
 */
const plugin = {
  id: "skillbot:sql-cell",
  autoStart: true,
  requires: ["@jupyterlab/notebook", "@jupyterlab/codemirror"],
  activate: function (app, notebook, codeMirror) {
    "use strict";

    const { CodeMirror } = codeMirror;
    const log = (...args) => console.log("[%%sql]", ...args);

    function isSqlCell(cell) {
      try {
        const text = cell.model.sharedModel.getSource();
        return text.trimStart().startsWith("%%sql");
      } catch (e) {
        return false;
      }
    }

    function sqlContent(cell) {
      const text = cell.model.sharedModel.getSource();
      const lines = text.split("\n");
      return { magicLine: lines[0], sql: lines.slice(1).join("\n"), full: text };
    }

    function setSqlHighlight(cell) {
      if (isSqlCell(cell) && cell.editor) {
        cell.editor.setOption("mode", "text/x-sql");
      }
    }

    function formatCell(cell) {
      if (!isSqlCell(cell)) return false;
      try {
        const { magicLine, sql } = sqlContent(cell);
        // call kernel to format SQL
        cell.sessionContext.session.kernel.requestExecute({
          code: `from jupyter.dsl.sql import format_sql\nprint(format_sql('''${sql.replace(/'/g, "\\'")}'''), end='')`,
        }).done.then(reply => {
          const formatted = reply.content.text || sql;
          cell.model.sharedModel.setSource(magicLine + "\n" + formatted);
        }).catch(() => {});
        return true;
      } catch (e) {
        return false;
      }
    }

    // hook: cell changed → set highlight
    notebook.NotebookActions.executed.connect((_, args) => {
      const cell = args.cell;
      if (cell) setSqlHighlight(cell);
    });

    // hook: after cell creation
    app.commands.addCommand("skillbot:sql-format", {
      label: "Format %%sql cell",
      execute: () => {
        const nb = app.shell.currentWidget;
        if (nb && nb.content && nb.content.activeCell) {
          formatCell(nb.content.activeCell);
        }
      },
    });

    // keyboard shortcut: Ctrl+Shift+F
    app.commands.addKeyBinding({
      command: "skillbot:sql-format",
      keys: ["Accel Shift F"],
      selector: ".jp-Notebook",
    });

    log("highlighting + formatting loaded (JupyterLab)");
  },
};

// JupyterLab plugin export
if (typeof module !== "undefined" && module.exports) {
  module.exports = [plugin];
} else {
  window._skillbot_sql_plugin = plugin;
}
