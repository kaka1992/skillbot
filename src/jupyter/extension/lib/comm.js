"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.commPlugin = void 0;
const notebook_1 = require("@jupyterlab/notebook");
const TARGET = 'skillbot:execute-cell';
/** Insert code cell below active cell, optionally auto-execute. */
function handleComm(comm, msg, tracker, sessionContext) {
    var _a;
    const data = ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.data) || {};
    const runMarker = data.run_cell_marker || '';
    const notebook = tracker.currentWidget;
    if (!notebook)
        return;
    const model = notebook.model;
    if (!model)
        return;
    // Run cell by ID (used by %confirm to re-execute agent cell)
    const runCellId = data.run_cell_id || '';
    if (runCellId) {
        const cells = model.sharedModel.cells;
        for (let i = cells.length - 1; i >= 0; i--) {
            if (cells[i].id === runCellId) {
                notebook.content.activeCellIndex = i;
                notebook_1.NotebookActions.run(notebook.content, sessionContext);
                return;
            }
        }
        return;
    }
    const code = data.code || '';
    const auto = data.auto !== false;
    const cellType = data.cell_type || 'code';
    const replaceId = data.replace_cell_id || '';
    if (!code)
        return;
    // Replace existing cell by ID
    if (replaceId) {
        const cells = model.sharedModel.cells;
        for (let i = cells.length - 1; i >= 0; i--) {
            if (cells[i].id === replaceId) {
                cells[i].source = code;
                notebook.content.activeCellIndex = i;
                comm.send({ cell_id: cells[i].id }).catch(() => { });
                return;
            }
        }
    }
    // Insert new cell
    const activeIndex = notebook.content.activeCellIndex;
    model.sharedModel.insertCell(activeIndex + 1, {
        cell_type: cellType,
        source: code,
        metadata: {},
    });
    const newCell = model.sharedModel.cells[activeIndex + 1];
    notebook.content.activeCellIndex = activeIndex + 1;
    // Reply with cell ID so kernel can track it
    comm.send({ cell_id: newCell.id }).catch(() => { });
    if (cellType === 'markdown' || !auto)
        return;
    notebook_1.NotebookActions.run(notebook.content, sessionContext);
}
exports.commPlugin = {
    id: 'skillbot:execute-cell',
    autoStart: true,
    requires: [notebook_1.INotebookTracker],
    activate: (app, tracker) => {
        const registerOnKernel = () => {
            var _a;
            const notebook = tracker.currentWidget;
            if (!notebook)
                return;
            const ctx = notebook.context.sessionContext;
            const kernel = (_a = ctx.session) === null || _a === void 0 ? void 0 : _a.kernel;
            if (kernel) {
                kernel.registerCommTarget(TARGET, (comm, msg) => handleComm(comm, msg, tracker, ctx));
            }
        };
        tracker.currentChanged.connect(() => {
            const notebook = tracker.currentWidget;
            if (notebook) {
                notebook.context.sessionContext.kernelChanged.connect(() => {
                    registerOnKernel();
                });
            }
            registerOnKernel();
        });
        registerOnKernel();
    },
};
