"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const notebook_1 = require("@jupyterlab/notebook");
const lang_sql_1 = require("@codemirror/lang-sql");
const state_1 = require("@codemirror/state");
const PLUGIN_ID = "@skillbot/sql-cell:plugin";
const sqlExtension = (0, lang_sql_1.sql)({ upperCaseKeywords: true });
const languageCompartment = new state_1.Compartment();
/**
 * Check if a code cell contains a %%sql magic.
 */
function isSqlCell(cell) {
    try {
        const text = cell.model.sharedModel.getSource();
        return text.trimStart().startsWith("%%sql");
    }
    catch {
        return false;
    }
}
/**
 * Apply SQL language mode to the cell's CodeMirror editor.
 */
function applySqlLanguage(cell) {
    try {
        const editor = cell.editor;
        // Access the underlying CodeMirror 6 EditorView
        const cmView = editor._editor;
        if (!cmView || !cmView.dispatch)
            return;
        cmView.dispatch({
            effects: languageCompartment.reconfigure(sqlExtension),
        });
    }
    catch {
        // Ignore — cell may not have an active editor
    }
}
/**
 * Remove SQL language mode from the cell.
 */
function removeSqlLanguage(cell) {
    try {
        const editor = cell.editor;
        const cmView = editor._editor;
        if (!cmView || !cmView.dispatch)
            return;
        cmView.dispatch({
            effects: languageCompartment.reconfigure([]),
        });
    }
    catch {
        // Ignore
    }
}
/**
 * Check all cells in the notebook and update SQL highlighting.
 */
function updateNotebook(panel) {
    const notebook = panel.content;
    notebook.widgets.forEach((cell) => {
        if (cell.model.type === "code") {
            const codeCell = cell;
            if (isSqlCell(codeCell)) {
                applySqlLanguage(codeCell);
            }
        }
    });
}
/**
 * JupyterLab plugin: monitors notebook cells and applies SQL syntax highlighting.
 */
const plugin = {
    id: PLUGIN_ID,
    autoStart: true,
    requires: [notebook_1.INotebookTracker],
    activate: (app, tracker) => {
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
exports.default = plugin;
//# sourceMappingURL=index.js.map