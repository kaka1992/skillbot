import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
} from "@jupyterlab/application";
import { INotebookTracker, NotebookPanel } from "@jupyterlab/notebook";
import { CodeCell } from "@jupyterlab/cells";
import { sql } from "@codemirror/lang-sql";
import { Compartment } from "@codemirror/state";
import { EditorView } from "@codemirror/view";

const PLUGIN_ID = "@skillbot/sql-cell:plugin";

const sqlExtension = sql({ upperCaseKeywords: true });
const languageCompartment = new Compartment();

/**
 * Check if a code cell contains a %%sql magic.
 */
function isSqlCell(cell: CodeCell): boolean {
  try {
    const text = cell.model.sharedModel.getSource();
    return text.trimStart().startsWith("%%sql");
  } catch {
    return false;
  }
}

/**
 * Apply SQL language mode to the cell's CodeMirror editor.
 */
function applySqlLanguage(cell: CodeCell): void {
  try {
    const editor = cell.editor;
    // Access the underlying CodeMirror 6 EditorView
    const cmView = (editor as any)._editor as EditorView | undefined;
    if (!cmView || !cmView.dispatch) return;

    cmView.dispatch({
      effects: languageCompartment.reconfigure(sqlExtension),
    });
  } catch {
    // Ignore — cell may not have an active editor
  }
}

/**
 * Remove SQL language mode from the cell.
 */
function removeSqlLanguage(cell: CodeCell): void {
  try {
    const editor = cell.editor;
    const cmView = (editor as any)._editor as EditorView | undefined;
    if (!cmView || !cmView.dispatch) return;

    cmView.dispatch({
      effects: languageCompartment.reconfigure([]),
    });
  } catch {
    // Ignore
  }
}

/**
 * Check all cells in the notebook and update SQL highlighting.
 */
function updateNotebook(panel: NotebookPanel): void {
  const notebook = panel.content;
  notebook.widgets.forEach((cell) => {
    if (cell.model.type === "code") {
      const codeCell = cell as CodeCell;
      if (isSqlCell(codeCell)) {
        applySqlLanguage(codeCell);
      }
    }
  });
}

/**
 * JupyterLab plugin: monitors notebook cells and applies SQL syntax highlighting.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: PLUGIN_ID,
  autoStart: true,
  requires: [INotebookTracker],
  activate: (
    app: JupyterFrontEnd,
    tracker: INotebookTracker
  ) => {
    console.log("[%%sql] JupyterLab extension activated");

    // Hook: when a notebook is opened or active notebook changes
    tracker.currentChanged.connect((_, panel) => {
      if (panel) {
        updateNotebook(panel);
        // Listen for cell content changes
        panel.content.model?.sharedModel.changed.connect(() => {
          updateNotebook(panel);
        });
      }
    });

    // Hook: when any notebook widget is added
    tracker.widgetAdded.connect((_, panel) => {
      updateNotebook(panel);
      panel.content.model?.sharedModel.changed.connect(() => {
        updateNotebook(panel);
      });
    });

    // Also check all open notebooks
    tracker.forEach((panel) => {
      updateNotebook(panel);
      panel.content.model?.sharedModel.changed.connect(() => {
        updateNotebook(panel);
      });
    });
  },
};

export default plugin;
