/**
 * %%sql cell support: syntax highlighting + Ctrl+Shift+F formatting.
 *
 * Installation: Load via Jupyter custom.js or jupyter-config.json.
 */
define(["base/js/namespace", "base/js/events"], function (Jupyter, events) {
  "use strict";

  function isSqlCell(cell) {
    var text = cell.get_text();
    return text.trimStart().startsWith("%%sql");
  }

  function setSqlHighlight(cell) {
    if (isSqlCell(cell)) {
      cell.code_mirror.setOption("mode", "text/x-sql");
    }
  }

  function formatSql(cell) {
    if (!isSqlCell(cell)) return;
    var text = cell.get_text();
    var lines = text.split("\n");
    var magicLine = lines[0]; // %%sql ...
    var sql = lines.slice(1).join("\n");

    // call kernel to format SQL
    var code = "from jupyter.dsl.sql import format_sql\nprint(format_sql('''" +
      sql.replace(/'/g, "\\'") + "'''), end='')";
    cell.kernel.execute(code, {
      iopub: {
        output: function (msg) {
          var formatted = msg.content.text || sql;
          cell.set_text(magicLine + "\n" + formatted);
        },
      },
    });
  }

  // hook: when a cell is selected, set SQL highlight
  events.on("selected_cell_type_changed.Notebook", function () {
    var cell = Jupyter.notebook.get_selected_cell();
    if (cell) setSqlHighlight(cell);
  });

  // hook: after cell creation, check highlight
  events.on("create.Cell", function (ev, data) {
    if (data && data.cell) setSqlHighlight(data.cell);
  });

  // hook: after cell execution, re-check
  events.on("finished_execute.CodeCell", function (ev, data) {
    if (data && data.cell) setSqlHighlight(data.cell);
  });

  // keyboard shortcut: Ctrl+Shift+F → format SQL
  Jupyter.keyboard_manager.command_shortcuts.add_shortcut(
    "Ctrl-Shift-F",
    "jupyter-sql:format-cell"
  );
  Jupyter.keyboard_manager.actions.register(
    {
      help: "Format %%sql cell",
      handler: function () {
        var cell = Jupyter.notebook.get_selected_cell();
        if (cell) formatSql(cell);
      },
    },
    "format-cell",
    "jupyter-sql"
  );
  Jupyter.keyboard_manager.command_shortcuts.add_shortcut(
    "Ctrl-Shift-F",
    "jupyter-sql:format-cell"
  );

  console.log("[%%sql] highlighting + formatting loaded");
});
