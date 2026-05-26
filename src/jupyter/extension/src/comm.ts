import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
} from '@jupyterlab/application';

import { INotebookTracker, NotebookActions } from '@jupyterlab/notebook';
import { ISessionContext } from '@jupyterlab/apputils';

const TARGET = 'skillbot:execute-cell';

/** Insert code cell below active cell, optionally auto-execute. */
function handleComm(
  comm: any,
  msg: any,
  tracker: INotebookTracker,
  sessionContext: ISessionContext,
): void {
  const data = msg.content?.data || {};
  const runMarker: string = data.run_cell_marker || '';
  const notebook = tracker.currentWidget;
  if (!notebook) return;
  const model = notebook.model;
  if (!model) return;

  // Run cell by ID (used by %confirm to re-execute agent cell)
  const runCellId: string = data.run_cell_id || '';
  if (runCellId) {
    const cells = model.sharedModel.cells;
    for (let i = cells.length - 1; i >= 0; i--) {
      if (cells[i].id === runCellId) {
        notebook.content.activeCellIndex = i;
        NotebookActions.run(notebook.content, sessionContext);
        return;
      }
    }
    return;
  }

  const code: string = data.code || '';
  const auto: boolean = data.auto !== false;
  const cellType: string = data.cell_type || 'code';
  const marker: string = data.replace_cell_marker || '';
  if (!code) return;

  // Replace existing cell by marker
  if (marker) {
    const cells = model.sharedModel.cells;
    for (let i = cells.length - 1; i >= 0; i--) {
      if (cells[i].source.includes(marker)) {
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

  // Reply with cell ID so kernel can track it
  comm.send({ cell_id: newCell.id }).catch(() => {});

  if (cellType === 'markdown' || !auto) return;
  NotebookActions.run(notebook.content, sessionContext);
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
      const kernel = ctx.session?.kernel;
      if (kernel) {
        kernel.registerCommTarget(TARGET, (comm: any, msg: any) =>
          handleComm(comm, msg, tracker, ctx),
        );
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
