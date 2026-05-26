"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.sqlPlugin = void 0;
const apputils_1 = require("@jupyterlab/apputils");
const notebook_1 = require("@jupyterlab/notebook");
const sql_formatter_1 = require("sql-formatter");
const lang_sql_1 = require("@codemirror/lang-sql");
const state_1 = require("@codemirror/state");
// ---- pure SQL helpers ----
function isSqlCell(code) {
    const first = code.trimStart().split('\n')[0] || '';
    return first.startsWith('%%sql');
}
/**
 * Convert # comments to -- so sql-formatter (spark dialect) can parse them.
 * Skips # inside string literals.
 */
function convertHashComments(sql) {
    let result = '';
    let inSingle = false;
    let inDouble = false;
    for (const ch of sql) {
        if (ch === "'" && !inDouble) {
            inSingle = !inSingle;
            result += ch;
        }
        else if (ch === '"' && !inSingle) {
            inDouble = !inDouble;
            result += ch;
        }
        else if (ch === '#' && !inSingle && !inDouble) {
            result += '--';
        }
        else {
            result += ch;
        }
    }
    return result;
}
function formatCell(code, dialect) {
    const lines = code.split('\n');
    const i = lines.findIndex(l => l.trimStart().startsWith('%%sql'));
    const magic = lines.slice(0, i + 1).join('\n');
    const sqlBody = lines.slice(i + 1).join('\n').trim();
    if (!sqlBody)
        return code;
    // Extract % magic lines (re-appended after formatting).
    // # comments are converted to -- inline so sql-formatter can parse them.
    const sqlLines = [];
    const magicLines = [];
    for (const line of sqlBody.split('\n')) {
        if (line.trimStart().startsWith('%')) {
            magicLines.push(line);
        }
        else {
            sqlLines.push(convertHashComments(line));
        }
    }
    const sqlToFormat = sqlLines.join('\n').trim();
    if (!sqlToFormat)
        return code;
    const body = (0, sql_formatter_1.format)(sqlToFormat, {
        language: dialect,
        tabWidth: 2,
        keywordCase: 'upper',
        linesBetweenQueries: 2,
    });
    const formatted = magicLines.length ? `${body}\n${magicLines.join('\n')}` : body;
    return `${magic}\n${formatted}`;
}
function getEditor(cell) {
    const e = cell === null || cell === void 0 ? void 0 : cell.editor;
    if (!(e === null || e === void 0 ? void 0 : e.injectExtension))
        return null;
    return { editor: e, view: e.editor };
}
// ---- CodeMirror SQL highlighting ----
const sqlConf = {};
const sqlCompartment = new state_1.Compartment();
function toggleHighlight(e, view, active) {
    if (!active) {
        view.dispatch({ effects: sqlCompartment.reconfigure([]) });
        return;
    }
    try {
        e.injectExtension(state_1.Prec.highest(sqlCompartment.of([])));
    }
    catch (_a) {
        // already injected
    }
    view.dispatch({ effects: sqlCompartment.reconfigure((0, lang_sql_1.sql)(sqlConf)) });
}
// ---- JupyterLab plugin ----
const CMD = 'skillbot:format-sql';
exports.sqlPlugin = {
    id: 'skillbot:sql-tools',
    autoStart: true,
    requires: [notebook_1.INotebookTracker],
    optional: [apputils_1.ICommandPalette],
    activate: (app, tracker, palette) => {
        const dialect = 'spark';
        let active = null;
        // ---- format command ----
        app.commands.addCommand(CMD, {
            label: 'Format SQL (%%sql cell)',
            execute: () => {
                const cell = tracker.activeCell;
                if (!cell)
                    return;
                const code = cell.model.sharedModel.getSource();
                if (!isSqlCell(code))
                    return;
                cell.model.sharedModel.setSource(formatCell(code, dialect));
            },
        });
        if (palette) {
            palette.addItem({ command: CMD, category: 'skillbot' });
        }
        app.commands.addKeyBinding({
            command: CMD,
            keys: ['Ctrl Shift F'],
            selector: '.jp-Notebook-cell',
        });
        // ---- SQL highlighting on active cell change ----
        tracker.activeCellChanged.connect((_, cell) => {
            if (active) {
                toggleHighlight(active.editor, active.view, false);
                active = null;
            }
            if (!cell)
                return;
            const info = getEditor(cell);
            if (!info)
                return;
            const code = cell.model.sharedModel.getSource();
            if (isSqlCell(code)) {
                toggleHighlight(info.editor, info.view, true);
                active = info;
            }
        });
    },
};
