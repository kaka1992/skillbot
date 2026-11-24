"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.commPlugin = void 0;
const notebook_1 = require("@jupyterlab/notebook");
const TARGET = 'skillbot:execute-cell';
const PROTOCOL_VERSION = 1;
const activeRequests = new Map();
function now() {
    return Date.now();
}
function sendReceipt(active, phase, extra = {}) {
    var _a;
    if (active.phases.has(phase))
        return;
    active.phases.add(phase);
    const request = active.request;
    const terminal = ['succeeded', 'failed', 'rejected', 'cancelled'].includes(phase)
        || (phase === 'materialized'
            && (!request.auto_execute || request.cell_type === 'markdown'));
    try {
        const future = active.comm.send({
            protocol_version: PROTOCOL_VERSION,
            request_id: request.request_id,
            batch_id: request.batch_id,
            notebook_path: request.notebook_path,
            kernel_id: request.kernel_id,
            phase,
            timestamp_ms: now(),
            cell_id: active.cellId,
            ...extra,
        });
        void ((_a = future === null || future === void 0 ? void 0 : future.done) === null || _a === void 0 ? void 0 : _a.catch(() => { }));
    }
    finally {
        if (terminal) {
            activeRequests.delete(request.request_id);
        }
    }
}
function reject(comm, data, errorCode, errorMessage) {
    var _a;
    const payload = {
        protocol_version: PROTOCOL_VERSION,
        request_id: data.request_id || '',
        batch_id: data.batch_id || '',
        notebook_path: data.notebook_path || '',
        kernel_id: data.kernel_id || '',
        phase: 'rejected',
        timestamp_ms: now(),
        cell_id: '',
        error_code: errorCode,
        error_message: errorMessage.slice(0, 2000),
    };
    const future = comm.send(payload);
    void ((_a = future === null || future === void 0 ? void 0 : future.done) === null || _a === void 0 ? void 0 : _a.catch(() => { }));
}
function findNotebook(tracker, path) {
    let found = null;
    tracker.forEach(widget => {
        if (!found && widget.context.path === path)
            found = widget;
    });
    return found;
}
function getKernelId(notebook) {
    var _a, _b, _c, _d;
    return ((_d = (_c = (_b = (_a = notebook === null || notebook === void 0 ? void 0 : notebook.context) === null || _a === void 0 ? void 0 : _a.sessionContext) === null || _b === void 0 ? void 0 : _b.session) === null || _c === void 0 ? void 0 : _c.kernel) === null || _d === void 0 ? void 0 : _d.id) || '';
}
function setRequestMetadata(cell, request) {
    cell.setMetadata('skillbot', {
        generated: true,
        protocol_version: PROTOCOL_VERSION,
        request_id: request.request_id,
        batch_id: request.batch_id,
        sequence_index: request.sequence_index,
    });
}
function executeWhenReady(active, retries = 0) {
    if (activeRequests.get(active.request.request_id) !== active)
        return;
    const notebook = active.notebook.content;
    const widget = notebook.widgets.find((cell) => cell.model.id === active.cellId);
    if (!widget) {
        if (retries < 20) {
            setTimeout(() => executeWhenReady(active, retries + 1), 100);
            return;
        }
        sendReceipt(active, 'failed', {
            error_code: 'CELL_WIDGET_TIMEOUT',
            error_message: 'Cell widget did not appear within 2 seconds',
        });
        return;
    }
    if (activeRequests.get(active.request.request_id) !== active)
        return;
    notebook.activeCellIndex = notebook.widgets.indexOf(widget);
    notebook_1.NotebookActions.runCells(notebook, [widget], active.notebook.context.sessionContext).then(ok => {
        if (!ok && !active.phases.has('started')) {
            sendReceipt(active, 'failed', {
                error_code: 'CELL_EXECUTION_NOT_STARTED',
                error_message: 'JupyterLab did not start Cell execution',
            });
        }
    }).catch(error => {
        sendReceipt(active, 'failed', {
            error_code: 'CELL_EXECUTION_ERROR',
            error_message: String(error),
        });
    });
}
function handleV1(comm, data, tracker) {
    if (!data.request_id || !data.batch_id || !data.notebook_path || !data.kernel_id) {
        reject(comm, data, 'INVALID_REQUEST', 'Missing request identity');
        return;
    }
    if (!['create', 'replace', 'run_existing'].includes(data.operation)) {
        reject(comm, data, 'INVALID_REQUEST', `Unsupported operation: ${data.operation}`);
        return;
    }
    if (!['code', 'markdown'].includes(data.cell_type)) {
        reject(comm, data, 'INVALID_REQUEST', `Unsupported Cell type: ${data.cell_type}`);
        return;
    }
    const target = findNotebook(tracker, data.notebook_path);
    if (!(target === null || target === void 0 ? void 0 : target.model)) {
        reject(comm, data, 'NOTEBOOK_NOT_FOUND', data.notebook_path);
        return;
    }
    const kernelId = getKernelId(target);
    if (!kernelId) {
        reject(comm, data, 'KERNEL_NOT_FOUND', data.notebook_path);
        return;
    }
    if (kernelId !== data.kernel_id) {
        reject(comm, data, 'KERNEL_MISMATCH', `Expected ${data.kernel_id}, got ${kernelId}`);
        return;
    }
    const active = {
        request: data,
        comm,
        notebook: target,
        cellId: '',
        startedAt: 0,
        phases: new Set(),
    };
    comm.onClose = () => {
        activeRequests.delete(data.request_id);
    };
    sendReceipt(active, 'received');
    const cells = target.model.sharedModel.cells;
    let cell = null;
    if (data.operation === 'replace' || data.operation === 'run_existing') {
        const targetId = data.operation === 'replace'
            ? data.replace_cell_id
            : data.run_cell_id;
        cell = cells.find((candidate) => candidate.id === targetId) || null;
        if (!cell) {
            reject(comm, data, 'CELL_NOT_FOUND', targetId);
            return;
        }
        if (data.operation === 'replace')
            cell.source = data.code;
    }
    else {
        const index = target.content.activeCellIndex + 1;
        target.model.sharedModel.insertCell(index, {
            cell_type: data.cell_type,
            source: data.code,
            metadata: {},
        });
        cell = target.model.sharedModel.cells[index];
    }
    active.cellId = cell.id;
    setRequestMetadata(cell, data);
    activeRequests.set(data.request_id, active);
    sendReceipt(active, 'materialized');
    if (data.cell_type === 'markdown' || !data.auto_execute)
        return;
    executeWhenReady(active);
}
function handleLegacy(comm, data, tracker) {
    const notebook = tracker.currentWidget;
    if (!(notebook === null || notebook === void 0 ? void 0 : notebook.model))
        return;
    const cells = notebook.model.sharedModel.cells;
    const replaceId = data.replace_cell_id || '';
    let cell = null;
    if (replaceId) {
        cell = cells.find((candidate) => candidate.id === replaceId) || null;
        if (cell)
            cell.source = data.code || '';
    }
    if (!cell) {
        const index = notebook.content.activeCellIndex + 1;
        notebook.model.sharedModel.insertCell(index, {
            cell_type: data.cell_type || 'code',
            source: data.code || '',
            metadata: {},
        });
        cell = notebook.model.sharedModel.cells[index];
    }
    notebook.content.activeCellIndex = cells.findIndex((candidate) => candidate.id === cell.id);
    comm.send({ cell_id: cell.id }).catch(() => { });
    if ((data.cell_type || 'code') !== 'markdown' && data.auto !== false) {
        const widget = notebook.content.widgets.find((item) => item.model.id === cell.id);
        if (widget) {
            notebook_1.NotebookActions.runCells(notebook.content, [widget], notebook.context.sessionContext).catch(() => { });
        }
    }
}
function handleComm(comm, msg, tracker) {
    var _a;
    const data = ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.data) || {};
    if (data.protocol_version === PROTOCOL_VERSION) {
        handleV1(comm, data, tracker);
    }
    else if (!Object.prototype.hasOwnProperty.call(data, 'protocol_version')) {
        handleLegacy(comm, data, tracker);
    }
    else {
        reject(comm, data, 'UNSUPPORTED_PROTOCOL_VERSION', `Expected protocol version ${PROTOCOL_VERSION}, got ${String(data.protocol_version)}`);
    }
}
exports.commPlugin = {
    id: 'skillbot:execute-cell',
    autoStart: true,
    requires: [notebook_1.INotebookTracker],
    activate: (_app, tracker) => {
        const registered = new WeakSet();
        const observedContexts = new WeakSet();
        const register = (kernel) => {
            if (!kernel || registered.has(kernel))
                return;
            kernel.registerCommTarget(TARGET, (comm, msg) => {
                handleComm(comm, msg, tracker);
            });
            registered.add(kernel);
        };
        const setup = () => {
            var _a, _b;
            const notebook = tracker.currentWidget;
            const context = (_a = notebook === null || notebook === void 0 ? void 0 : notebook.context) === null || _a === void 0 ? void 0 : _a.sessionContext;
            if (!context)
                return;
            register((_b = context.session) === null || _b === void 0 ? void 0 : _b.kernel);
            if (!observedContexts.has(context)) {
                context.kernelChanged.connect((_sender, args) => {
                    register(args.newValue);
                });
                observedContexts.add(context);
            }
        };
        notebook_1.NotebookActions.executionScheduled.connect((_sender, args) => {
            const active = Array.from(activeRequests.values()).find(item => item.cellId === args.cell.model.id
                && item.notebook.content === args.notebook);
            if (!active)
                return;
            active.startedAt = now();
            sendReceipt(active, 'started');
        });
        notebook_1.NotebookActions.executed.connect((_sender, args) => {
            var _a;
            const active = Array.from(activeRequests.values()).find(item => item.cellId === args.cell.model.id
                && item.notebook.content === args.notebook);
            if (!active)
                return;
            const executionCount = (_a = args.cell.model.executionCount) !== null && _a !== void 0 ? _a : null;
            if (args.success) {
                sendReceipt(active, 'succeeded', {
                    execution_count: executionCount,
                    elapsed_ms: active.startedAt ? now() - active.startedAt : null,
                });
            }
            else {
                const error = args.error;
                sendReceipt(active, 'failed', {
                    execution_count: executionCount,
                    elapsed_ms: active.startedAt ? now() - active.startedAt : null,
                    error_code: (error === null || error === void 0 ? void 0 : error.errorName) || 'CELL_EXECUTION_ERROR',
                    error_message: (error === null || error === void 0 ? void 0 : error.errorValue) || String(error || 'Cell execution failed'),
                });
            }
        });
        tracker.currentChanged.connect(setup);
        tracker.widgetAdded.connect(setup);
        setTimeout(setup, 500);
    },
};
