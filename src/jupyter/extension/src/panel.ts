import { Widget } from '@lumino/widgets';
import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';
import { INotebookTracker } from '@jupyterlab/notebook';

const TARGET = 'skillbot:tui';
let _panelInstance: AgentPanel | null = null;

class AgentPanel extends Widget {
  private _outputEl: HTMLElement;
  private _inputEl: HTMLInputElement;
  private _comm: any = null;

  constructor() {
    super();
    this.id = 'skillbot:tui';
    this.title.label = 'Agent';
    this.title.closable = true;
    this.node.style.display = 'flex';
    this.node.style.flexDirection = 'column';
    this.node.style.backgroundColor = '#1e1e1e';
    this.node.style.color = '#d4d4d4';

    this._outputEl = document.createElement('pre');
    this._outputEl.style.flex = '1';
    this._outputEl.style.margin = '0';
    this._outputEl.style.padding = '8px';
    this._outputEl.style.overflowY = 'auto';
    this._outputEl.style.whiteSpace = 'pre-wrap';
    this._outputEl.style.fontFamily = 'monospace';
    this._outputEl.style.fontSize = '13px';
    this._outputEl.style.lineHeight = '1.4';
    this.node.appendChild(this._outputEl);

    this._inputEl = document.createElement('input');
    this._inputEl.placeholder = '> ask the agent...';
    this._inputEl.style.padding = '6px 8px';
    this._inputEl.style.border = 'none';
    this._inputEl.style.borderTop = '1px solid #444';
    this._inputEl.style.backgroundColor = '#2d2d2d';
    this._inputEl.style.color = '#d4d4d4';
    this._inputEl.style.fontFamily = 'monospace';
    this._inputEl.style.fontSize = '13px';
    this._inputEl.style.outline = 'none';
    this._inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this._sendPrompt();
    });
    this.node.appendChild(this._inputEl);
  }

  private _sendPrompt(): void {
    const text = this._inputEl.value.trim();
    if (!text) return;
    this._append(`\n> ${text}\n`);
    if (this._comm) {
      this._comm.send({ action: 'prompt', text });
    }
    this._inputEl.value = '';
  }

  private _append(text: string): void {
    this._outputEl.textContent += text;
    this._outputEl.scrollTop = this._outputEl.scrollHeight;
  }

  private _onMsg(msg: any): void {
    const data = msg.content?.data || {};
    switch (data.action) {
      case 'text':
        this._append(data.content || '');
        break;
      case 'tool':
        this._append(`\x1b[90m[${data.name}]\x1b[0m\n`);
        break;
      case 'thinking':
        this._append(`\x1b[90m# ${data.text}\x1b[0m\n`);
        break;
      case 'clear':
        this._outputEl.textContent = '';
        break;
    }
  }

  registerComm(kernel: any): void {
    if (!kernel) return;
    kernel.registerCommTarget(TARGET, (comm: any, _msg: any) => {
      this._comm = comm;
      comm.onMsg = (m: any) => this._onMsg(m);
    });
  }
}


export const panelPlugin: JupyterFrontEndPlugin<void> = {
  id: 'skillbot:tui',
  autoStart: true,
  requires: [INotebookTracker],
  activate: (_app: JupyterFrontEnd, tracker: INotebookTracker) => {
    const panel = new AgentPanel();
    _app.shell.add(panel, 'right', { rank: 100 });
    _panelInstance = panel;

    const register = () => {
      const nb = tracker.currentWidget;
      if (!nb) return;
      const ctx = nb.context.sessionContext;
      const kernel = ctx.session?.kernel;
      if (kernel) {
        panel.registerComm(kernel);
      }
    };

    tracker.currentChanged.connect(() => register());
    setTimeout(register, 500);
  },
};
