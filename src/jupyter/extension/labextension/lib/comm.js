"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.commPlugin = void 0;
const notebook_1 = require("@jupyterlab/notebook");
const TARGET = 'skillbot:execute-cell';
/** Insert code cell below active cell, optionally auto-execute. */
function handleComm(comm, msg, tracker, sessionContext) {
    var _a;
    const data = ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.data) || {};
    const code = data.code || '';
    const auto = data.auto !== false;
    if (!code)
        return;
    const notebook = tracker.currentWidget;
    if (!notebook)
        return;
    const model = notebook.model;
    if (!model)
        return;
    const activeIndex = notebook.content.activeCellIndex;
    model.sharedModel.insertCell(activeIndex + 1, {
        cell_type: 'code',
        source: code,
        metadata: {},
    });
    notebook.content.activeCellIndex = activeIndex + 1;
    if (!auto)
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
