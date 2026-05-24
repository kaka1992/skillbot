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
  const code: string = data.code || '';
  const auto: boolean = data.auto !== false;
  if (!code) return;

  const notebook = tracker.currentWidget;
  if (!notebook) return;
  const model = notebook.model;
  if (!model) return;

  const activeIndex = notebook.content.activeCellIndex;
  model.sharedModel.insertCell(activeIndex + 1, {
    cell_type: 'code',
    source: code,
    metadata: {},
  });
  notebook.content.activeCellIndex = activeIndex + 1;

  if (!auto) return;
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
