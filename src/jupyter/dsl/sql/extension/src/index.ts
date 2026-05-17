import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
} from "@jupyterlab/application";
import { INotebookTracker, NotebookPanel } from "@jupyterlab/notebook";
import { CodeCell } from "@jupyterlab/cells";
import { sql } from "@codemirror/lang-sql";
import { Compartment } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { language } from "@codemirror/language";

const PLUGIN_ID = "@skillbot/sql-cell:plugin";
const sqlCompartment = new Compartment();

function isSqlCell(cell: CodeCell): boolean {
  try {
    return cell.model.sharedModel.getSource().trimStart().startsWith("%%sql");
  } catch {
    return false;
  }
}

function getSqlBody(cell: CodeCell): string {
  const text = cell.model.sharedModel.getSource();
  const lines = text.split("\n");
  return lines.slice(1).join("\n");
}

function applySqlLanguage(cell: CodeCell): void {
  try {
    const cmView = (cell.editor as any).editor as EditorView | undefined;
    if (!cmView?.dispatch) return;

    cmView.dispatch({
      effects: sqlCompartment.reconfigure(
        language.of(sql({ upperCaseKeywords: true }))
      ),
    });
  } catch {
    // editor not ready — will retry on next cell change
  }
}

function formatActiveCell(app: JupyterFrontEnd): void {
  const widget = app.shell.currentWidget;
  if (!widget) return;

  const notebook = (widget as any).content;
  const cell = notebook?.activeCell as CodeCell | undefined;
  if (!cell || !isSqlCell(cell)) return;

  const sqlBody = getSqlBody(cell);
  if (!sqlBody.trim()) return;

  // call kernel to format
  const session = notebook.sessionContext?.session;
  if (!session?.kernel) return;

  const escaped = sqlBody.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
  const code = `from jupyter.dsl.sql import format_sql\nprint(format_sql('''${escaped}'''), end='')`;

  session.kernel.requestExecute({ code }).done.then((reply: any) => {
    const formatted: string = reply?.content?.text || sqlBody;
    const magicLine = cell.model.sharedModel.getSource().split("\n")[0];
    cell.model.sharedModel.setSource(magicLine + "\n" + formatted);
  }).catch(() => {});
}

function updateNotebook(panel: NotebookPanel): void {
  panel.content.widgets.forEach((cell) => {
    if (cell.model.type === "code" && isSqlCell(cell as CodeCell)) {
      applySqlLanguage(cell as CodeCell);
    }
  });
}

const plugin: JupyterFrontEndPlugin<void> = {
  id: PLUGIN_ID,
  autoStart: true,
  requires: [INotebookTracker],
  activate: (app: JupyterFrontEnd, tracker: INotebookTracker) => {
    console.log("[%%sql] JupyterLab extension activated");

    // ---- SQL highlighting ----
    const onPanel = (panel: NotebookPanel) => {
      updateNotebook(panel);
      panel.content.model?.sharedModel.changed.connect(() => {
        updateNotebook(panel);
      });
    };
    tracker.currentChanged.connect((_, panel) => { if (panel) onPanel(panel); });
    tracker.widgetAdded.connect((_, panel) => onPanel(panel));
    tracker.forEach((panel) => onPanel(panel));

    // ---- Ctrl+Shift+F formatting shortcut ----
    app.commands.addCommand("skillbot:sql-format", {
      label: "Format %%sql cell",
      execute: () => formatActiveCell(app),
    });
    app.commands.addKeyBinding({
      command: "skillbot:sql-format",
      keys: ["Accel Shift F"],
      selector: ".jp-Notebook",
    });
    console.log("[%%sql] Ctrl+Shift+F registered");
  },
};

export default plugin;
