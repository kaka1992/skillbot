"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.panelPlugin = void 0;
const widgets_1 = require("@lumino/widgets");
const notebook_1 = require("@jupyterlab/notebook");
const TARGET = 'skillbot:tui';
let _panelInstance = null;
class AgentPanel extends widgets_1.Widget {
    constructor() {
        super();
        this._comm = null;
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
            if (e.key === 'Enter')
                this._sendPrompt();
        });
        this.node.appendChild(this._inputEl);
    }
    _sendPrompt() {
        const text = this._inputEl.value.trim();
        if (!text)
            return;
        this._append(`\n> ${text}\n`);
        if (this._comm) {
            this._comm.send({ action: 'prompt', text });
        }
        this._inputEl.value = '';
    }
    _append(text) {
        this._outputEl.textContent += text;
        this._outputEl.scrollTop = this._outputEl.scrollHeight;
    }
    _onMsg(msg) {
        var _a;
        const data = ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.data) || {};
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
    registerComm(kernel) {
        if (!kernel)
            return;
        kernel.registerCommTarget(TARGET, (comm, _msg) => {
            this._comm = comm;
            comm.onMsg = (m) => this._onMsg(m);
        });
    }
}
exports.panelPlugin = {
    id: 'skillbot:tui',
    autoStart: true,
    requires: [notebook_1.INotebookTracker],
    activate: (_app, tracker) => {
        const panel = new AgentPanel();
        _app.shell.add(panel, 'right', { rank: 100 });
        _panelInstance = panel;
        const register = () => {
            var _a;
            const nb = tracker.currentWidget;
            if (!nb)
                return;
            const ctx = nb.context.sessionContext;
            const kernel = (_a = ctx.session) === null || _a === void 0 ? void 0 : _a.kernel;
            if (kernel) {
                panel.registerComm(kernel);
            }
        };
        tracker.currentChanged.connect(() => register());
        setTimeout(register, 500);
    },
};
