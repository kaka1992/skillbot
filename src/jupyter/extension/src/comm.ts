import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
} from '@jupyterlab/application';

import { INotebookTracker, NotebookActions } from '@jupyterlab/notebook';
import { ISessionContext } from '@jupyterlab/apputils';

const TARGET = 'skillbot:execute-cell';

function handleComm(
  comm: any,
  msg: any,
  tracker: INotebookTracker,
  sessionContext: ISessionContext,
): void {
  const data = msg.content?.data || {};
  const notebook = tracker.currentWidget;
  if (!notebook) return;
  const model = notebook.model;
  if (!model) return;

  // Run cell by ID
  const runCellId: string = data.run_cell_id || '';
  if (runCellId) {
    const cells = model.sharedModel.cells;
    for (let i = cells.length - 1; i >= 0; i--) {
      if (cells[i].id === runCellId) {
        notebook.content.activeCellIndex = i;
        const kernel = sessionContext.session?.kernel;
        if (kernel) kernel.requestExecute({ code: cells[i].source, store_history: true });
        return;
      }
    }
    return;
  }

  const code: string = data.code || '';
  const auto: boolean = data.auto !== false;
  const cellType: string = data.cell_type || 'code';
  const replaceId: string = data.replace_cell_id || '';
  if (!code) return;

  // Replace existing cell by ID
  if (replaceId) {
    const cells = model.sharedModel.cells;
    for (let i = cells.length - 1; i >= 0; i--) {
      if (cells[i].id === replaceId) {
        cells[i].source = code;
        notebook.content.activeCellIndex = i;
        comm.send({ cell_id: cells[i].id }).catch(() => {});
        return;
      }
    }
  }

  // Insert new cell
  const activeIndex = notebook.content.activeCellIndex;
  model.sharedModel.insertCell(activeIndex + 1, {
    cell_type: cellType as 'code' | 'markdown',
    source: code,
    metadata: {},
  });
  const newCell = model.sharedModel.cells[activeIndex + 1];
  notebook.content.activeCellIndex = activeIndex + 1;

  comm.send({ cell_id: newCell.id }).catch(() => {});

  if (cellType === 'markdown' || !auto) return;
  // retry loop: wait for cell widget to render, then execute
  const cellIndex = activeIndex + 1;
  let retries = 0;
  const execute = () => {
    notebook.content.activeCellIndex = cellIndex;
    const cell = notebook.content.activeCell;
    if (cell && cell.model.type === 'code') {
      NotebookActions.run(notebook.content, sessionContext)
        .catch(e => console.error('[comm] run failed:', e));
    } else if (retries < 20) {
      retries++;
      setTimeout(execute, 100);
    } else {
      console.error('[comm] cell widget never appeared at index', cellIndex);
    }
  };
  setTimeout(execute, 100);
}

export const commPlugin: JupyterFrontEndPlugin<void> = {
  id: 'skillbot:execute-cell',
  autoStart: true,
  requires: [INotebookTracker],
  activate: (app: JupyterFrontEnd, tracker: INotebookTracker) => {
    const registerOnKernel = () => {
      const notebook = tracker.currentWidget;
      if (!notebook) return;
      const ctx = notebook.context.sessionContext;
      if (!ctx) return;
      const kernel = ctx.session?.kernel;
      if (kernel) {
        kernel.registerCommTarget(TARGET, (comm: any, msg: any) =>
          handleComm(comm, msg, tracker, ctx),
        );
        console.log('[comm] registered target:', TARGET);
      }
    };

    let currentCtx: any = null;
    const onKernelChanged = () => registerOnKernel();

    const setup = () => {
      const notebook = tracker.currentWidget;
      if (!notebook) return;
      const ctx = notebook.context.sessionContext;
      if (!ctx || ctx === currentCtx) return;
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
