import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
} from "@jupyterlab/application";
import { INotebookTracker, NotebookPanel } from "@jupyterlab/notebook";
import { CodeCell } from "@jupyterlab/cells";

const PLUGIN_ID = "@skillbot/sql-cell:plugin";
const SQL_MIME = "text/x-sql";
const PYTHON_MIME = "text/x-python";

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
 * Get the current MIME type from the cell's editor model.
 */
function getMimeType(cell: CodeCell): string {
  try {
    return (cell.editor.model as any).mimeType || "";
  } catch {
    return "";
  }
}

/**
 * Set the MIME type on the cell's editor model.
 * This triggers JupyterLab's built-in language switching (CM6).
 */
function setMimeType(cell: CodeCell, mime: string): void {
  try {
    const model = cell.editor.model as any;
    if (model.mimeType !== mime) {
      model.mimeType = mime;
    }
  } catch {
    // Ignore
  }
}

/**
 * Update all cells in the notebook — set SQL MIME for %%sql cells,
 * restore Python MIME for non-%%sql cells.
 */
function updateNotebook(panel: NotebookPanel): void {
  const notebook = panel.content;
  notebook.widgets.forEach((cell) => {
    if (cell.model.type === "code") {
      const codeCell = cell as CodeCell;
      if (isSqlCell(codeCell)) {
        if (getMimeType(codeCell) !== SQL_MIME) {
          setMimeType(codeCell, SQL_MIME);
        }
      } else {
        if (getMimeType(codeCell) === SQL_MIME) {
          setMimeType(codeCell, PYTHON_MIME);
        }
      }
    }
  });
}

/**
 * JupyterLab plugin: monitors notebook cells and switches language
 * between SQL and Python based on %%sql magic.
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

    tracker.currentChanged.connect((_, panel) => {
      if (panel) {
        updateNotebook(panel);
        panel.content.model?.sharedModel.changed.connect(() => {
          updateNotebook(panel);
        });
      }
    });

    tracker.widgetAdded.connect((_, panel) => {
      updateNotebook(panel);
      panel.content.model?.sharedModel.changed.connect(() => {
        updateNotebook(panel);
      });
    });

    tracker.forEach((panel) => {
      updateNotebook(panel);
      panel.content.model?.sharedModel.changed.connect(() => {
        updateNotebook(panel);
      });
    });
  },
};

export default plugin;
