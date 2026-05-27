"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.commPlugin = void 0;
const notebook_1 = require("@jupyterlab/notebook");
const TARGET = 'skillbot:execute-cell';
function handleComm(comm, msg, tracker, sessionContext) {
    var _a, _b;
    const data = ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.data) || {};
    const notebook = tracker.currentWidget;
    if (!notebook)
        return;
    const model = notebook.model;
    if (!model)
        return;
    // Run cell by ID
    const runCellId = data.run_cell_id || '';
    if (runCellId) {
        const cells = model.sharedModel.cells;
        for (let i = cells.length - 1; i >= 0; i--) {
            if (cells[i].id === runCellId) {
                notebook.content.activeCellIndex = i;
                const kernel = (_b = sessionContext.session) === null || _b === void 0 ? void 0 : _b.kernel;
                if (kernel)
                    kernel.requestExecute({ code: cells[i].source, store_history: true });
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
    comm.send({ cell_id: newCell.id }).catch(() => { });
    if (cellType === 'markdown' || !auto)
        return;
    // retry loop: wait for cell widget to render, then execute
    const cellIndex = activeIndex + 1;
    let retries = 0;
    const execute = () => {
        notebook.content.activeCellIndex = cellIndex;
        const cell = notebook.content.activeCell;
        if (cell && cell.model.type === 'code') {
            notebook_1.NotebookActions.run(notebook.content, sessionContext)
                .catch(e => console.error('[comm] run failed:', e));
        }
        else if (retries < 20) {
            retries++;
            setTimeout(execute, 100);
        }
        else {
            console.error('[comm] cell widget never appeared at index', cellIndex);
        }
    };
    setTimeout(execute, 100);
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
            if (!ctx)
                return;
            const kernel = (_a = ctx.session) === null || _a === void 0 ? void 0 : _a.kernel;
            if (kernel) {
                kernel.registerCommTarget(TARGET, (comm, msg) => handleComm(comm, msg, tracker, ctx));
                console.log('[comm] registered target:', TARGET);
            }
        };
        let currentCtx = null;
        const onKernelChanged = () => registerOnKernel();
        const setup = () => {
            const notebook = tracker.currentWidget;
            if (!notebook)
                return;
            const ctx = notebook.context.sessionContext;
            if (!ctx || ctx === currentCtx)
                return;
            // disconnect old, connect new
            if (currentCtx) {
                currentCtx.kernelChanged.disconnect(onKernelChanged);
            }
            currentCtx = ctx;
            ctx.kernelChanged.connect(onKernelChanged);
            registerOnKernel();
        };
        tracker.currentChanged.connect(() => setup());
        setTimeout(setup, 500);
    },
};
