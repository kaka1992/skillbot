import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
} from "@jupyterlab/application";
import { INotebookTracker, NotebookPanel } from "@jupyterlab/notebook";
import { CodeCell } from "@jupyterlab/cells";
import { sql } from "@codemirror/lang-sql";
import { StateEffect } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { language } from "@codemirror/language";

const PLUGIN_ID = "@skillbot/sql-cell:plugin";

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
 * Uses StateEffect.appendConfig to inject sql() extension directly.
 */
function applySqlLanguage(cell: CodeCell): void {
  try {
    const cmView = (cell.editor as any).editor as EditorView | undefined;
    if (!cmView || !cmView.dispatch) return;

    cmView.dispatch({
      effects: StateEffect.appendConfig.of([
        language.of(sql({ upperCaseKeywords: true })),
      ]),
    });
  } catch {
    // Ignore
  }
}

/**
 * Update all cells in the notebook — apply SQL language to %%sql cells.
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

    const onPanel = (panel: NotebookPanel) => {
      updateNotebook(panel);
      panel.content.model?.sharedModel.changed.connect(() => {
        updateNotebook(panel);
      });
    };

    tracker.currentChanged.connect((_, panel) => {
      if (panel) onPanel(panel);
    });

    tracker.widgetAdded.connect((_, panel) => {
      onPanel(panel);
    });

    tracker.forEach((panel) => onPanel(panel));
  },
};

export default plugin;
