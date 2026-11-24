import { JupyterFrontEndPlugin } from '@jupyterlab/application';
import { INotebookTracker, NotebookActions } from '@jupyterlab/notebook';

const TARGET = 'skillbot:execute-cell';
const PROTOCOL_VERSION = 1;

type ReceiptPhase =
  | 'received'
  | 'materialized'
  | 'started'
  | 'succeeded'
  | 'failed'
  | 'rejected'
  | 'cancelled';

interface ExecutionRequest {
  protocol_version: number;
  request_id: string;
  batch_id: string;
  notebook_path: string;
  kernel_id: string;
  operation: 'create' | 'replace' | 'run_existing';
  code: string;
  cell_type: 'code' | 'markdown';
  auto_execute: boolean;
  replace_cell_id: string;
  run_cell_id: string;
  sequence_index: number;
  sequence_size: number;
}

interface ActiveRequest {
  request: ExecutionRequest;
  comm: any;
  notebook: any;
  cellId: string;
  startedAt: number;
  phases: Set<ReceiptPhase>;
}

const activeRequests = new Map<string, ActiveRequest>();

function now(): number {
  return Date.now();
}

function sendReceipt(
  active: ActiveRequest,
  phase: ReceiptPhase,
  extra: Record<string, unknown> = {},
): void {
  if (active.phases.has(phase)) return;
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
    void future?.done?.catch(() => {});
  } finally {
    if (terminal) {
      activeRequests.delete(request.request_id);
    }
  }
}

function reject(
  comm: any,
  data: Partial<ExecutionRequest>,
  errorCode: string,
  errorMessage: string,
): void {
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
  void future?.done?.catch(() => {});
}

function findNotebook(tracker: INotebookTracker, path: string): any | null {
  let found: any | null = null;
  tracker.forEach(widget => {
    if (!found && widget.context.path === path) found = widget;
  });
  return found;
}

function getKernelId(notebook: any): string {
  return notebook?.context?.sessionContext?.session?.kernel?.id || '';
}

function setRequestMetadata(cell: any, request: ExecutionRequest): void {
  cell.setMetadata('skillbot', {
    generated: true,
    protocol_version: PROTOCOL_VERSION,
    request_id: request.request_id,
    batch_id: request.batch_id,
    sequence_index: request.sequence_index,
  });
}

function executeWhenReady(active: ActiveRequest, retries = 0): void {
  if (activeRequests.get(active.request.request_id) !== active) return;
  const notebook = active.notebook.content;
  const widget = notebook.widgets.find((cell: any) => cell.model.id === active.cellId);
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

  if (activeRequests.get(active.request.request_id) !== active) return;
  notebook.activeCellIndex = notebook.widgets.indexOf(widget);
  NotebookActions.runCells(
    notebook,
    [widget],
    active.notebook.context.sessionContext,
  ).then(ok => {
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

function handleV1(comm: any, data: ExecutionRequest, tracker: INotebookTracker): void {
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
  if (!target?.model) {
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

  const active: ActiveRequest = {
    request: data,
    comm,
    notebook: target,
    cellId: '',
    startedAt: 0,
    phases: new Set<ReceiptPhase>(),
  };
  comm.onClose = () => {
    activeRequests.delete(data.request_id);
  };
  sendReceipt(active, 'received');

  const cells = target.model.sharedModel.cells;
  let cell: any | null = null;
  if (data.operation === 'replace' || data.operation === 'run_existing') {
    const targetId = data.operation === 'replace'
      ? data.replace_cell_id
      : data.run_cell_id;
    cell = cells.find((candidate: any) => candidate.id === targetId) || null;
    if (!cell) {
      reject(comm, data, 'CELL_NOT_FOUND', targetId);
      return;
    }
    if (data.operation === 'replace') cell.source = data.code;
  } else {
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

  if (data.cell_type === 'markdown' || !data.auto_execute) return;
  executeWhenReady(active);
}

function handleLegacy(comm: any, data: any, tracker: INotebookTracker): void {
  const notebook = tracker.currentWidget;
  if (!notebook?.model) return;
  const cells = notebook.model.sharedModel.cells;
  const replaceId: string = data.replace_cell_id || '';
  let cell: any | null = null;

  if (replaceId) {
    cell = cells.find((candidate: any) => candidate.id === replaceId) || null;
    if (cell) cell.source = data.code || '';
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
  notebook.content.activeCellIndex = cells.findIndex(
    (candidate: any) => candidate.id === cell.id,
  );
  comm.send({ cell_id: cell.id }).catch(() => {});
  if ((data.cell_type || 'code') !== 'markdown' && data.auto !== false) {
    const widget = notebook.content.widgets.find((item: any) => item.model.id === cell.id);
    if (widget) {
      NotebookActions.runCells(
        notebook.content,
        [widget],
        notebook.context.sessionContext,
      ).catch(() => {});
    }
  }
}

function handleComm(comm: any, msg: any, tracker: INotebookTracker): void {
  const data = msg.content?.data || {};
  if (data.protocol_version === PROTOCOL_VERSION) {
    handleV1(comm, data as ExecutionRequest, tracker);
  } else if (!Object.prototype.hasOwnProperty.call(data, 'protocol_version')) {
    handleLegacy(comm, data, tracker);
  } else {
    reject(
      comm,
      data,
      'UNSUPPORTED_PROTOCOL_VERSION',
      `Expected protocol version ${PROTOCOL_VERSION}, got ${String(data.protocol_version)}`,
    );
  }
}

export const commPlugin: JupyterFrontEndPlugin<void> = {
  id: 'skillbot:execute-cell',
  autoStart: true,
  requires: [INotebookTracker],
  activate: (_app, tracker) => {
    const registered = new WeakSet<object>();
    const observedContexts = new WeakSet<object>();
    const register = (kernel: any) => {
      if (!kernel || registered.has(kernel)) return;
      kernel.registerCommTarget(TARGET, (comm: any, msg: any) => {
        handleComm(comm, msg, tracker);
      });
      registered.add(kernel);
    };

    const setup = () => {
      const notebook = tracker.currentWidget;
      const context = notebook?.context?.sessionContext;
      if (!context) return;
      register(context.session?.kernel);
      if (!observedContexts.has(context)) {
        context.kernelChanged.connect((_sender: any, args: any) => {
          register(args.newValue);
        });
        observedContexts.add(context);
      }
    };

    NotebookActions.executionScheduled.connect((_sender, args) => {
      const active = Array.from(activeRequests.values()).find(
        item => item.cellId === args.cell.model.id
          && item.notebook.content === args.notebook,
      );
      if (!active) return;
      active.startedAt = now();
      sendReceipt(active, 'started');
    });

    NotebookActions.executed.connect((_sender, args) => {
      const active = Array.from(activeRequests.values()).find(
        item => item.cellId === args.cell.model.id
          && item.notebook.content === args.notebook,
      );
      if (!active) return;
      const executionCount = (args.cell.model as any).executionCount ?? null;
      if (args.success) {
        sendReceipt(active, 'succeeded', {
          execution_count: executionCount,
          elapsed_ms: active.startedAt ? now() - active.startedAt : null,
        });
      } else {
        const error = args.error;
        sendReceipt(active, 'failed', {
          execution_count: executionCount,
          elapsed_ms: active.startedAt ? now() - active.startedAt : null,
          error_code: error?.errorName || 'CELL_EXECUTION_ERROR',
          error_message: error?.errorValue || String(error || 'Cell execution failed'),
        });
      }
    });

    tracker.currentChanged.connect(setup);
    tracker.widgetAdded.connect(setup);
    setTimeout(setup, 500);
  },
};
