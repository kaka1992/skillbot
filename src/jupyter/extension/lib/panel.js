"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.panelPlugin = void 0;
const widgets_1 = require("@lumino/widgets");
const notebook_1 = require("@jupyterlab/notebook");
const TARGET = 'skillbot:tui';
let _panelInstance = null;
// ---------------------------------------------------------------------------
// Claude Code colour palette
// ---------------------------------------------------------------------------
const CC = {
    bg: '#171717',
    surface: '#2c2c2c',
    text: '#ececec',
    inactive: 'rgb(175,175,175)',
    subtle: 'rgb(130,130,130)',
    border: '#333',
    accent: 'rgb(0,180,180)', // bright teal for section dividers
    brand: 'rgb(215,119,87)',
    success: 'rgb(78,186,101)',
    error: 'rgb(255,107,128)',
    userBg: 'rgb(55,55,55)',
    pointer: 'rgb(175,175,175)', // matches cc-haha 'subtle' for pointer
};
// All CSS lives inside shadowRoot — completely isolated from JupyterLab
const STYLES = `
:host {
  display: flex;
  flex-direction: column;
  min-width: 650px;
  height: 100%;
  background: ${CC.bg};
  color: ${CC.text};
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 13px;
  line-height: 1.5;
}

/* ---- welcome banner ---- */
.skillbot-welcome {
  padding: 10px 16px;
  border-bottom: 2px solid ${CC.accent};
}

.skillbot-output {
  flex: 1;
  overflow-y: auto;
  padding: 8px 16px 8px 4px;
  scroll-behavior: smooth;
  color: ${CC.text};
}
.skillbot-output::-webkit-scrollbar { width: 6px; }
.skillbot-output::-webkit-scrollbar-thumb { background: ${CC.subtle}; border-radius: 3px; }
.skillbot-output::-webkit-scrollbar-track { background: transparent; }

/* ---- message block (one prompt+response pair) ---- */
.skillbot-msg-block {
  margin-top: 8px;
  color: ${CC.text};
}

/* ---- user prompt ---- */
.skillbot-prompt-line {
  display: flex;
  align-items: flex-start;
  background: ${CC.userBg};
  padding: 4px 8px 4px 8px;
  border-radius: 2px;
}
.skillbot-prompt-prefix {
  color: ${CC.pointer};
  user-select: none;
  flex-shrink: 0;
  margin-right: 6px;
}
.skillbot-prompt-text {
  color: ${CC.text};
  white-space: pre-wrap;
}

/* ---- agent response ---- */
.skillbot-response-prefix {
  color: ${CC.inactive};
  user-select: none;
  flex-shrink: 0;
}
.skillbot-response-text {
  color: ${CC.text};
  white-space: pre-wrap;
  line-height: 1.6;
}

.skillbot-tool-line {
  color: ${CC.brand};
  padding-left: 8px;
  margin: 2px 0;
}

.skillbot-thinking-line {
  color: rgb(180,180,180);
  font-style: italic;
  padding-left: 8px;
  margin: 2px 0;
}

.skillbot-code-block {
  background: ${CC.surface};
  border: 1px solid ${CC.border};
  border-radius: 4px;
  margin: 6px 0 6px 8px;
  padding: 10px 14px;
  overflow-x: auto;
}
.skillbot-code-block pre {
  margin: 0;
  font-family: inherit;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  color: ${CC.text};
}
.skillbot-code-block code {
  color: ${CC.text};
}
.skillbot-code-block::-webkit-scrollbar { height: 4px; }
.skillbot-code-block::-webkit-scrollbar-thumb { background: ${CC.subtle}; border-radius: 2px; }

.skillbot-result-line {
  margin-top: 4px;
  padding-left: 8px;
  color: ${CC.text};
}

/* ---- spinner (cc-haha style: ✻ + verb) ---- */
@keyframes skillbot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.skillbot-spinner {
  color: ${CC.brand};
  animation: skillbot-pulse 1s ease-in-out infinite;
  user-select: none;
}
.skillbot-spinner-label {
  color: rgb(180,180,180);
  margin-left: 4px;
}

/* ---- info bar (mode switch messages) ---- */
.skillbot-info {
  font-size: 12px;
  font-weight: 500;
  color: rgb(190,190,190);
  padding: 5px 16px;
  border-top: 2px solid ${CC.accent};
  min-height: 20px;
  transition: opacity 0.3s;
}

.skillbot-status {
  font-size: 12px;
  font-weight: 500;
  color: rgb(180,180,180);
  padding: 5px 16px;
  border-top: 2px solid ${CC.accent};
  user-select: none;
  display: flex;
  justify-content: space-between;
}

.skillbot-input-wrapper {
  display: flex;
  align-items: center;
  border-top: 2px solid ${CC.accent};
}
.skillbot-input-wrapper:focus-within {
  border-top-color: ${CC.text};
}
.skillbot-input-marker {
  color: rgb(210,210,210);
  font-weight: 600;
  padding-left: 16px;
  user-select: none;
  flex-shrink: 0;
}
.skillbot-input {
  flex: 1;
  background: transparent;
  color: ${CC.text};
  border: none;
  padding: 10px 12px 10px 4px;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.5;
  outline: none;
  resize: none;
  overflow-y: auto;
  max-height: 200px;
  box-sizing: border-box;
}
.skillbot-input::placeholder {
  color: rgb(150,150,150);
  font-weight: 400;
}
.skillbot-input::-webkit-scrollbar { width: 4px; }
.skillbot-input::-webkit-scrollbar-thumb { background: ${CC.subtle}; border-radius: 2px; }

/* ---- plan confirmation (replaces input area) ---- */
.skillbot-confirm-wrapper {
  border-top: 2px solid ${CC.accent};
  padding: 10px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.skillbot-confirm-label {
  color: rgb(200,200,200);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
}
.skillbot-confirm-option {
  padding: 6px 10px;
  border-radius: 4px;
  color: rgb(180,180,180);
  cursor: pointer;
}
.skillbot-confirm-option-active {
  background: ${CC.surface};
  color: ${CC.text};
  font-weight: 600;
}
.skillbot-confirm-option-active::before {
  content: '❯ ';
  color: ${CC.brand};
}
.skillbot-confirm-hint {
  color: rgb(150,150,150);
  font-size: 12px;
  margin-top: 4px;
}

/* ---- plan block in output area ---- */
.skillbot-plan-block {
  background: #0a2a2a;
  border-left: 3px solid ${CC.accent};
  padding: 8px 12px;
  margin: 6px 0;
  border-radius: 2px;
  white-space: pre-wrap;
  line-height: 1.6;
  color: rgb(200,200,200);
}
.skillbot-plan-header {
  font-weight: 600;
  color: ${CC.accent};
  font-size: 11px;
  margin-bottom: 6px;
}

/* ---- plan preview in confirm dialog ---- */
.skillbot-plan-preview {
  background: #0a2a2a;
  border-left: 3px solid ${CC.accent};
  padding: 8px 12px;
  margin-bottom: 8px;
  max-height: 200px;
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  border-radius: 2px;
  color: rgb(200,200,200);
}
.skillbot-plan-preview::-webkit-scrollbar { width: 4px; }
.skillbot-plan-preview::-webkit-scrollbar-thumb { background: ${CC.subtle}; border-radius: 2px; }

/* ---- feedback textarea in confirm ---- */
.skillbot-confirm-feedback {
  background: transparent;
  color: ${CC.text};
  border: 1px solid #333;
  padding: 6px 8px;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  min-height: 60px;
  outline: none;
  border-radius: 2px;
  box-sizing: border-box;
}
.skillbot-confirm-feedback:focus {
  border-color: ${CC.accent};
}
.skillbot-confirm-feedback::placeholder {
  color: rgb(130,130,130);
  font-weight: 400;
}
`;
// ===========================================================================
// AgentPanel
// ===========================================================================
class AgentPanel extends widgets_1.Widget {
    constructor() {
        super();
        this._killRing = ''; // for Ctrl+Y yank
        this._lastKill = ''; // track consecutive kill type for accumulation
        this._charsPerLine = 80; // computed from textarea width / monospace char width
        this._statusTimer = null;
        this._execStartTime = 0;
        this._statusIcon = '○';
        this._statusLabel = 'idle';
        this._tracker = null;
        this._kernel = null;
        this._comm = null;
        this._history = [];
        this._historyIdx = -1;
        this._historyDraft = ''; // saved original input when navigating history
        // spinner
        this._spinnerEl = null;
        this._infoTimer = null;
        // mode (cc-haha style: Shift+Tab to cycle)
        this._mode = 'default';
        // plan confirmation
        this._planConfirmActive = false;
        this._planConfirmOptionIdx = 0;
        this._planConfirmFeedbackMode = false;
        this._planCurrentSummary = '';
        // message block
        this._currentBlock = null;
        this._streaming = false;
        this._responseStarted = false;
        this._textEl = null; // accumulated text element for streaming
        this.id = 'skillbot:tui';
        this.title.label = 'Agent';
        this.title.closable = true;
        // Light-DOM min styles (just enough for JupyterLab to lay out the panel)
        this.node.style.display = 'flex';
        this.node.style.flexDirection = 'column';
        this.node.style.minWidth = '300px';
        this.node.style.backgroundColor = CC.bg;
        this.node.style.color = CC.text;
        // Shadow DOM — isolates all CSS from JupyterLab
        this._root = this.node.attachShadow({ mode: 'open' });
        const style = document.createElement('style');
        style.textContent = STYLES;
        this._root.appendChild(style);
        // welcome banner
        const welcome = document.createElement('div');
        welcome.className = 'skillbot-welcome';
        welcome.innerHTML = `
      <div style="font-size:14px;font-weight:600;color:${CC.text};margin-bottom:4px;">Agent Panel</div>
      <div style="font-size:12px;font-weight:500;color:rgb(180,180,180);">Shift+Tab mode · Ctrl+A/E/B/F/H/K/U/W/Y · Ctrl+P/N history · Shift+↵ newline</div>
    `;
        this._root.appendChild(welcome);
        // output — click to focus input
        this._outputEl = document.createElement('div');
        this._outputEl.className = 'skillbot-output';
        this._outputEl.addEventListener('click', () => {
            // Don't steal focus if user was selecting text (drag, double-click, etc.)
            const sel = document.getSelection();
            if (sel && sel.type !== 'None' && sel.toString().length > 0)
                return;
            if (this._planConfirmActive) {
                this._confirmWrapper.focus();
            }
            else {
                this._inputEl.focus();
            }
        });
        this._root.appendChild(this._outputEl);
        // status bar
        this._statusEl = document.createElement('div');
        this._statusEl.className = 'skillbot-status';
        this._statusEl.innerHTML = '<span>○ idle</span><span>skillbot</span>';
        this._root.appendChild(this._statusEl);
        // input
        this._inputWrapper = document.createElement('div');
        this._inputWrapper.className = 'skillbot-input-wrapper';
        this._markerEl = document.createElement('span');
        this._markerEl.className = 'skillbot-input-marker';
        this._markerEl.textContent = '❯ ';
        this._inputWrapper.appendChild(this._markerEl);
        this._inputEl = document.createElement('textarea');
        this._inputEl.className = 'skillbot-input';
        this._inputEl.placeholder = 'ask the agent...';
        this._inputEl.rows = 1;
        this._inputEl.addEventListener('keydown', (e) => this._onKeydown(e));
        this._inputEl.addEventListener('input', () => this._resizeInput());
        this._inputWrapper.appendChild(this._inputEl);
        this._root.appendChild(this._inputWrapper);
        // plan confirm overlay (hidden, replaces input area when active)
        this._confirmWrapper = document.createElement('div');
        this._confirmWrapper.className = 'skillbot-confirm-wrapper';
        this._confirmWrapper.style.display = 'none';
        this._confirmWrapper.tabIndex = 0;
        this._confirmWrapper.addEventListener('keydown', (e) => this._onKeydown(e));
        this._root.appendChild(this._confirmWrapper);
        // info bar (mode switch messages, at bottom)
        this._infoEl = document.createElement('div');
        this._infoEl.className = 'skillbot-info';
        this._root.appendChild(this._infoEl);
        this._restoreState();
    }
    // ---- keyboard -----------------------------------------------------------
    _onKeydown(e) {
        // plan confirm mode: intercept navigation and commit keys
        if (this._planConfirmActive) {
            // Feedback mode: let typing pass through to textarea, intercept Enter/Esc
            if (this._planConfirmFeedbackMode) {
                if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.altKey && !e.isComposing) {
                    e.preventDefault();
                    e.stopPropagation();
                    this._submitPlanConfirm();
                    return;
                }
                if (e.key === 'Escape') {
                    e.preventDefault();
                    e.stopPropagation();
                    this._planConfirmFeedbackMode = false;
                    this._renderConfirmOptions();
                    this._confirmWrapper.focus();
                    return;
                }
                if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
                    e.preventDefault();
                    e.stopPropagation();
                    this._cancelPlanConfirm();
                    return;
                }
                // Shift+Enter, Arrow keys, etc. pass through to textarea natively
                return;
            }
            // Option selection mode
            switch (e.key) {
                case 'ArrowUp':
                    e.preventDefault();
                    e.stopPropagation();
                    this._planConfirmOptionIdx = (this._planConfirmOptionIdx === 0 ? 2 : this._planConfirmOptionIdx - 1);
                    this._renderConfirmOptions();
                    this._confirmWrapper.focus();
                    return;
                case 'ArrowDown':
                case 'Tab':
                    e.preventDefault();
                    e.stopPropagation();
                    this._planConfirmOptionIdx = ((this._planConfirmOptionIdx + 1) % 3);
                    this._renderConfirmOptions();
                    this._confirmWrapper.focus();
                    return;
                case 'Enter':
                    e.preventDefault();
                    e.stopPropagation();
                    this._submitPlanConfirm();
                    return;
                case 'Escape':
                    e.preventDefault();
                    e.stopPropagation();
                    this._cancelPlanConfirm();
                    return;
            }
            if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
                // Ctrl+L during confirm: clear panel + cancel confirm
                e.preventDefault();
                e.stopPropagation();
                this._cancelPlanConfirm();
                this._clear();
                return;
            }
            if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
                e.preventDefault();
                e.stopPropagation();
                this._cancelPlanConfirm();
                return;
            }
            e.preventDefault();
            return;
        }
        const ctrl = e.ctrlKey; // Control only — Cmd/Meta passes through for OS shortcuts
        const el = this._inputEl;
        const ss = el.selectionStart;
        const se = el.selectionEnd;
        const v = el.value;
        // Helper: accumulate kills (consecutive same-type kills append, different type overwrites)
        const doKill = (type, text) => {
            if (this._lastKill === type && this._killRing) {
                this._killRing += text;
            }
            else {
                this._killRing = text;
            }
            this._lastKill = type;
        };
        // ---- Emacs-style Ctrl shortcuts ----
        if (ctrl && !e.altKey) {
            switch (e.key) {
                case 'a':
                    e.preventDefault();
                    el.selectionStart = el.selectionEnd = 0;
                    return;
                case 'b':
                    e.preventDefault();
                    el.selectionStart = el.selectionEnd = Math.max(0, ss - 1);
                    return;
                case 'e':
                    e.preventDefault();
                    el.selectionStart = el.selectionEnd = v.length;
                    return;
                case 'f':
                    e.preventDefault();
                    el.selectionStart = el.selectionEnd = Math.min(v.length, ss + 1);
                    return;
                case 'h':
                    e.preventDefault();
                    if (ss !== se) {
                        el.value = v.slice(0, ss) + v.slice(se);
                        el.selectionStart = el.selectionEnd = ss;
                    }
                    else if (ss > 0) {
                        el.value = v.slice(0, ss - 1) + v.slice(ss);
                        el.selectionStart = el.selectionEnd = ss - 1;
                    }
                    this._resizeInput();
                    return;
                case 'n':
                    if (this._navigateHistory(1)) {
                        e.preventDefault();
                    }
                    return;
                case 'p':
                    if (this._navigateHistory(-1)) {
                        e.preventDefault();
                    }
                    return;
                case 'k': {
                    e.preventDefault();
                    if (ss !== se) {
                        el.value = v.slice(0, ss) + v.slice(se);
                        el.selectionStart = el.selectionEnd = ss;
                    }
                    const cur = el.selectionStart;
                    const lineEnd = el.value.indexOf('\n', cur);
                    if (lineEnd !== -1) {
                        // Kill to end of current line (including the newline)
                        doKill('k', el.value.slice(cur, lineEnd + 1));
                        el.value = el.value.slice(0, cur) + el.value.slice(lineEnd + 1);
                    }
                    else if (cur < el.value.length) {
                        // Last line, no trailing newline: kill to end of text
                        doKill('k', el.value.slice(cur));
                        el.value = el.value.slice(0, cur);
                    }
                    el.selectionStart = el.selectionEnd = cur;
                    this._resizeInput();
                    return;
                }
                case 'u': {
                    e.preventDefault();
                    if (ss !== se) {
                        el.value = v.slice(0, ss) + v.slice(se);
                        el.selectionStart = el.selectionEnd = ss;
                    }
                    const cur = el.selectionStart;
                    if (cur > 0) {
                        doKill('u', el.value.slice(0, cur));
                        el.value = el.value.slice(cur);
                        el.selectionStart = el.selectionEnd = 0;
                        this._resizeInput();
                    }
                    return;
                }
                case 'w': {
                    e.preventDefault();
                    // Clear selection first
                    if (ss !== se) {
                        el.value = v.slice(0, ss) + v.slice(se);
                        el.selectionStart = el.selectionEnd = ss;
                    }
                    const cur = el.selectionStart;
                    const wordStart = this._prevWordPos(el.value, cur);
                    if (wordStart < cur) {
                        doKill('w', el.value.slice(wordStart, cur));
                        el.value = el.value.slice(0, wordStart) + el.value.slice(cur);
                        el.selectionStart = el.selectionEnd = wordStart;
                        this._resizeInput();
                    }
                    return;
                }
                case 'd': {
                    e.preventDefault();
                    if (ss !== se) {
                        el.value = v.slice(0, ss) + v.slice(se);
                        el.selectionStart = el.selectionEnd = ss;
                        this._resizeInput();
                    }
                    else if (v.length === 0) {
                        el.value = '';
                        this._historyIdx = -1;
                        this._historyDraft = '';
                        this._resizeInput();
                    }
                    else if (ss < v.length) {
                        el.value = v.slice(0, ss) + v.slice(ss + 1);
                        el.selectionStart = el.selectionEnd = ss;
                        this._resizeInput();
                    }
                    return;
                }
                case 'y': {
                    e.preventDefault();
                    if (this._killRing) {
                        // Replace selection if any, then insert yanked text
                        if (ss !== se) {
                            el.value = v.slice(0, ss) + v.slice(se);
                            el.selectionStart = el.selectionEnd = ss;
                        }
                        const cur = el.selectionStart;
                        el.value = el.value.slice(0, cur) + this._killRing + el.value.slice(el.selectionEnd);
                        el.selectionStart = el.selectionEnd = cur + this._killRing.length;
                        this._resizeInput();
                    }
                    return;
                }
                case 'c': {
                    e.preventDefault();
                    if (ss !== se)
                        return; // has selection → let browser handle copy (Cmd+C)
                    if (v.length > 0) {
                        // Clear input (same as Escape)
                        el.value = '';
                        this._historyIdx = -1;
                        this._historyDraft = '';
                        this._killRing = '';
                        this._lastKill = '';
                        this._resizeInput();
                    }
                    // On empty input, Ctrl+C is a no-op (panel stays open)
                    return;
                }
                case 'l':
                    e.preventDefault();
                    this._clear();
                    return;
            }
        }
        // ---- Alt shortcuts (word navigation) ----
        if (e.altKey && !ctrl) {
            switch (e.key) {
                case 'b':
                case 'ArrowLeft':
                    e.preventDefault();
                    el.selectionStart = el.selectionEnd = this._prevWordPos(v, ss);
                    return;
                case 'f':
                case 'ArrowRight':
                    e.preventDefault();
                    el.selectionStart = el.selectionEnd = this._nextWordPos(v, ss);
                    return;
                case 'd': {
                    e.preventDefault();
                    const end = this._nextWordPos(v, ss);
                    if (end > ss) {
                        doKill('d', v.slice(ss, end));
                        el.value = v.slice(0, ss) + v.slice(end);
                        el.selectionStart = el.selectionEnd = ss;
                        this._resizeInput();
                    }
                    return;
                }
            }
        }
        // ---- Enter / Shift+Enter / Meta+Enter ----
        if (e.key === 'Enter' && !e.isComposing) {
            this._killRing = '';
            this._lastKill = '';
            if (e.shiftKey || e.metaKey || e.altKey) {
                e.preventDefault();
                // Clear selection before inserting newline
                if (ss !== se) {
                    el.value = v.slice(0, ss) + v.slice(se);
                    el.selectionStart = el.selectionEnd = ss;
                }
                const cur = el.selectionStart;
                el.value = el.value.slice(0, cur) + '\n' + el.value.slice(el.selectionEnd);
                el.selectionStart = el.selectionEnd = cur + 1;
                this._resizeInput();
            }
            else {
                e.preventDefault();
                this._sendPrompt();
            }
            return;
        }
        // ---- Arrow keys: history at visual boundaries, line nav otherwise ----
        if (e.key === 'ArrowUp' && !ctrl && !e.altKey) {
            if (this._isOnFirstVisualLine(v, ss) && this._navigateHistory(-1)) {
                e.preventDefault();
                return;
            }
            // Not on first visual line → let textarea handle natively
        }
        if (e.key === 'ArrowDown' && !ctrl && !e.altKey) {
            if (this._isOnLastVisualLine(v, ss) && this._navigateHistory(1)) {
                e.preventDefault();
                return;
            }
        }
        // ---- Escape ----
        if (e.key === 'Escape') {
            el.value = '';
            this._historyIdx = -1;
            this._historyDraft = '';
            this._killRing = '';
            this._lastKill = '';
            this._resizeInput();
            return;
        }
        // ---- Tab ----
        if (e.key === 'Tab') {
            this._killRing = '';
            this._lastKill = '';
            e.preventDefault();
            if (e.shiftKey) {
                this._cycleMode();
            }
            else {
                this._tabComplete();
            }
            return;
        }
        // Reset kill ring on printable character input
        if (e.key.length === 1 && !ctrl && !e.altKey) {
            this._killRing = '';
            this._lastKill = '';
        }
    }
    _prevWordPos(text, pos) {
        // Skip trailing whitespace
        let i = pos - 1;
        while (i >= 0 && /\s/.test(text[i]))
            i--;
        // Skip the word
        while (i >= 0 && !/\s/.test(text[i]))
            i--;
        return i + 1;
    }
    _nextWordPos(text, pos) {
        let i = pos;
        // Skip current word
        while (i < text.length && !/\s/.test(text[i]))
            i++;
        // Skip whitespace
        while (i < text.length && /\s/.test(text[i]))
            i++;
        return i;
    }
    _resizeInput() {
        const el = this._inputEl;
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 200) + 'px';
        this._recalcCharsPerLine();
    }
    _recalcCharsPerLine() {
        const el = this._inputEl;
        if (el.clientWidth <= 0)
            return;
        try {
            const style = getComputedStyle(el);
            const padL = parseFloat(style.paddingLeft) || 0;
            const padR = parseFloat(style.paddingRight) || 0;
            const cw = el.clientWidth - padL - padR - 2; // -2 for border
            // Measure monospace char width using canvas
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            ctx.font = style.font;
            const charW = ctx.measureText('W').width;
            this._charsPerLine = Math.max(1, Math.floor(cw / charW));
        }
        catch (_) {
            // Fallback: ~7.8px per char at 13px for SF Mono
            this._charsPerLine = Math.max(1, Math.floor((el.clientWidth - 18) / 7.8));
        }
    }
    // Visual line number at text position (accounts for both \n and word-wrap)
    _visualLineAt(text, pos) {
        let line = 0, col = 0;
        const limit = Math.min(pos, text.length);
        for (let i = 0; i < limit; i++) {
            if (text[i] === '\n') {
                line++;
                col = 0;
            }
            else if (++col >= this._charsPerLine) {
                line++;
                col = 0;
            }
        }
        return line;
    }
    _isOnFirstVisualLine(text, pos) {
        return this._visualLineAt(text, pos) === 0;
    }
    _isOnLastVisualLine(text, pos) {
        const cursorLine = this._visualLineAt(text, pos);
        const lastLine = this._visualLineAt(text, text.length);
        return cursorLine >= lastLine;
    }
    _navigateHistory(direction) {
        const v = this._inputEl.value;
        // Save draft on first entry into history
        if (this._historyIdx === -1 && v) {
            this._historyDraft = v;
        }
        this._killRing = '';
        this._lastKill = '';
        const newIdx = this._historyIdx - direction; // direction: -1 = older (↑), 1 = newer (↓)
        if (newIdx >= -1 && newIdx < this._history.length) {
            this._historyIdx = newIdx;
            if (this._historyIdx === -1) {
                this._inputEl.value = this._historyDraft;
                this._historyDraft = '';
            }
            else {
                this._inputEl.value = this._history[this._history.length - 1 - this._historyIdx];
            }
            // Place cursor at start so next ArrowUp immediately triggers more history
            this._inputEl.selectionStart = this._inputEl.selectionEnd = 0;
            this._resizeInput();
            return true;
        }
        return false;
    }
    _tabComplete() {
        const val = this._inputEl.value;
        for (const c of ['/confirm ', '/clear']) {
            if (c.startsWith(val) && c !== val) {
                this._inputEl.value = c;
                this._inputEl.selectionStart = this._inputEl.selectionEnd = c.length;
                this._resizeInput();
                return;
            }
        }
    }
    _cycleMode() {
        const idx = AgentPanel.MODE_ORDER.indexOf(this._mode);
        this._mode = AgentPanel.MODE_ORDER[(idx + 1) % AgentPanel.MODE_ORDER.length];
        this._updateModeInfo();
        this._saveState();
        // notify backend silently — no agent execution
        if (this._kernel) {
            this._kernel.requestExecute({
                code: `get_ipython().user_ns['_panel_set_mode']("${this._mode}")`,
                store_history: false,
            });
        }
    }
    // info bar + input area: persistent mode indicator
    _updateModeInfo() {
        if (this._infoTimer)
            clearTimeout(this._infoTimer);
        const color = AgentPanel.MODE_COLOR[this._mode];
        const symbol = AgentPanel.MODE_SYMBOL[this._mode];
        // Update input marker and placeholder
        if (this._markerEl) {
            this._markerEl.textContent = symbol ? `${symbol} ` : '❯ ';
            this._markerEl.style.color = symbol && color ? color : '';
        }
        this._inputEl.placeholder = this._mode === 'plan'
            ? 'describe the task you want to plan...'
            : 'ask the agent...';
        // Update info bar
        if (this._mode === 'default') {
            this._infoEl.innerHTML = '';
        }
        else {
            const hints = AgentPanel.MODE_INFO[this._mode] || [];
            const hint = hints[Math.floor(Math.random() * hints.length)];
            this._infoEl.innerHTML = `<span style="color:${color}">${symbol} ${hint}</span>`;
            // Fade back to persistent indicator after 4 seconds
            this._infoTimer = setTimeout(() => {
                this._infoEl.innerHTML = `<span style="color:${color}">${symbol} ${this._mode}</span>`;
            }, 4000);
        }
        this._infoEl.style.opacity = '1';
    }
    // ---- prompt -------------------------------------------------------------
    _sendPrompt() {
        if (this._planConfirmActive)
            return;
        const text = this._inputEl.value.trim();
        if (!text)
            return;
        if (this._history.length === 0 || this._history[this._history.length - 1] !== text) {
            this._history.push(text);
        }
        this._historyIdx = -1;
        this._startBlock();
        this._renderPrompt(text);
        this._startSpinner();
        this._setStatus('…', 'thinking');
        if (this._kernel) {
            // send unexecuted cell content to namespace before the prompt
            if (this._tracker) {
                const nb = this._tracker.currentWidget;
                if (nb) {
                    const activeCell = nb.content.activeCell;
                    if (activeCell) {
                        const src = activeCell.model.sharedModel.getSource();
                        if (src.trim()) {
                            this._kernel.requestExecute({
                                code: `get_ipython().user_ns['_panel_track_cell_edit'](${JSON.stringify(src)})`,
                                store_history: false,
                            });
                        }
                    }
                }
            }
            const code = `get_ipython().user_ns['_panel_input'](${JSON.stringify(text)}, mode="${this._mode}")`;
            const future = this._kernel.requestExecute({ code, store_history: false });
            let firstStdout = true;
            future.onIOPub = (msg) => {
                var _a;
                if (msg.header.msg_type === 'stream' && ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.name) === 'stdout') {
                    if (firstStdout) {
                        this._renderResponseText(this._stripAnsi(msg.content.text));
                        firstStdout = false;
                    }
                    else {
                        this._appendTextChunk(this._stripAnsi(msg.content.text));
                    }
                }
            };
        }
        this._inputEl.value = '';
        this._historyDraft = '';
        this._resizeInput();
    }
    // ---- block management ---------------------------------------------------
    _startBlock() {
        this._currentBlock = document.createElement('div');
        this._currentBlock.className = 'skillbot-msg-block';
        this._outputEl.appendChild(this._currentBlock);
        this._streaming = true;
        this._responseStarted = false;
        this._textEl = null;
    }
    _appendToBlock(el) {
        const target = this._currentBlock || this._outputEl;
        target.appendChild(el);
        this._scrollBottom();
    }
    // ---- renderers ----------------------------------------------------------
    _ensureResponsePrefix() {
        if (!this._responseStarted) {
            this._responseStarted = true;
            const prefix = document.createElement('div');
            prefix.className = 'skillbot-response-prefix';
            prefix.textContent = '  ⎿ ';
            this._appendToBlock(prefix);
        }
    }
    _renderPrompt(text) {
        const div = document.createElement('div');
        div.className = 'skillbot-prompt-line';
        div.innerHTML = `<span class="skillbot-prompt-prefix">❯</span><span class="skillbot-prompt-text">${this._esc(text)}</span>`;
        this._appendToBlock(div);
    }
    _renderResponseText(content) {
        this._ensureResponsePrefix();
        this._textEl = null; // new text stream, reset accumulator
        this._appendTextChunk(content);
    }
    _appendTextChunk(content) {
        if (!this._textEl || !this._textEl.parentElement) {
            this._textEl = document.createElement('div');
            this._textEl.className = 'skillbot-response-text';
            this._textEl.textContent = content;
            this._appendToBlock(this._textEl);
        }
        else {
            this._textEl.textContent += content;
        }
    }
    _renderTool(name) {
        this._ensureResponsePrefix();
        this._textEl = null; // tool line breaks text accumulation
        const div = document.createElement('div');
        div.className = 'skillbot-tool-line';
        div.textContent = `⬢ ${name}`;
        this._appendToBlock(div);
    }
    _renderThinking(content) {
        this._ensureResponsePrefix();
        this._textEl = null; // thinking line breaks text accumulation
        const div = document.createElement('div');
        div.className = 'skillbot-thinking-line';
        div.textContent = `∴ ${content}`;
        this._appendToBlock(div);
    }
    _renderCodeBlock(_language, code) {
        this._ensureResponsePrefix();
        this._textEl = null;
        const wrapper = document.createElement('div');
        wrapper.className = 'skillbot-code-block';
        wrapper.innerHTML = `<pre><code>${this._esc(code)}</code></pre>`;
        this._appendToBlock(wrapper);
    }
    _renderPlanBlock(text) {
        this._ensureResponsePrefix();
        this._textEl = null;
        const wrapper = document.createElement('div');
        wrapper.className = 'skillbot-plan-block';
        wrapper.innerHTML = `<div class="skillbot-plan-header">⏸ Plan</div>${this._esc(text)}`;
        this._appendToBlock(wrapper);
    }
    _renderResult(summary) {
        this._ensureResponsePrefix();
        this._textEl = null;
        const div = document.createElement('div');
        div.className = 'skillbot-result-line';
        div.innerHTML = `<span style="color:${CC.success}">✓</span> ${this._esc(summary)}`;
        this._appendToBlock(div);
        this._stopSpinner();
        this._setStatus('✓', 'done');
        this._streaming = false;
        this._saveState();
    }
    _clear() {
        this._outputEl.innerHTML = '';
        this._currentBlock = null;
        this._textEl = null;
        this._streaming = false;
        this._stopSpinner();
        this._setStatus('○', 'idle');
        this._closeConfirm(); // ensure confirm UI is dismissed
        this._saveState();
        this._inputEl.value = '';
        this._historyIdx = -1;
        this._historyDraft = '';
        this._resizeInput();
    }
    // ---- persistence (localStorage) ----
    _saveState() {
        try {
            localStorage.setItem(AgentPanel.STORAGE_KEY, JSON.stringify({
                output: this._outputEl.innerHTML,
                history: this._history,
                mode: this._mode,
                status: this._statusEl.innerHTML,
            }));
        }
        catch (_) { }
    }
    _restoreState() {
        try {
            const raw = localStorage.getItem(AgentPanel.STORAGE_KEY);
            if (!raw)
                return;
            const s = JSON.parse(raw);
            if (s.output) {
                this._outputEl.innerHTML = s.output;
                this._scrollBottom();
            }
            if (s.history)
                this._history = s.history;
            if (s.mode) {
                this._mode = s.mode;
                this._updateModeInfo();
            }
            if (s.status)
                this._statusEl.innerHTML = s.status;
        }
        catch (_) { }
    }
    // ---- spinner -------------------------------------------------------------
    _startSpinner() {
        if (this._spinnerEl)
            return;
        const wrapper = document.createElement('span');
        wrapper.style.whiteSpace = 'nowrap';
        this._spinnerEl = document.createElement('span');
        this._spinnerEl.className = 'skillbot-spinner';
        this._spinnerEl.textContent = '✻';
        wrapper.appendChild(this._spinnerEl);
        const label = document.createElement('span');
        label.className = 'skillbot-spinner-label';
        label.textContent = 'Thinking...';
        wrapper.appendChild(label);
        this._appendToBlock(wrapper);
    }
    _stopSpinner() {
        if (this._spinnerEl) {
            const wrapper = this._spinnerEl.parentElement;
            if (wrapper)
                wrapper.remove();
            this._spinnerEl = null;
        }
    }
    // ---- status bar ----------------------------------------------------------
    _setStatus(icon, label) {
        this._statusIcon = icon;
        this._statusLabel = label;
        // Start timer for running states, stop for idle/done
        if (icon === '…') {
            if (!this._statusTimer) {
                this._execStartTime = Date.now();
                this._statusTimer = setInterval(() => this._updateStatusDisplay(), 1000);
            }
        }
        else {
            this._stopStatusTimer();
        }
        this._updateStatusDisplay();
    }
    _stopStatusTimer() {
        if (this._statusTimer) {
            clearInterval(this._statusTimer);
            this._statusTimer = null;
        }
    }
    _updateStatusDisplay() {
        const icon = this._statusIcon;
        const label = this._statusLabel;
        if (icon === '…' && this._execStartTime > 0) {
            const elapsed = Math.floor((Date.now() - this._execStartTime) / 1000);
            this._statusEl.innerHTML = `<span>${icon} ${label} (${elapsed}s)</span><span>skillbot</span>`;
        }
        else {
            this._statusEl.innerHTML = `<span>${icon} ${label}</span><span>skillbot</span>`;
        }
    }
    // ---- plan confirmation ---------------------------------------------------
    _renderPlanConfirm(summary) {
        this._planCurrentSummary = summary;
        this._planConfirmOptionIdx = 0;
        this._planConfirmFeedbackMode = false;
        this._planConfirmActive = true;
        this._renderConfirmOptions();
        this._inputWrapper.style.display = 'none';
        this._confirmWrapper.style.display = 'flex';
        this._confirmWrapper.focus();
    }
    _getConfirmHint() {
        if (this._planConfirmFeedbackMode) {
            return 'Enter submit · Esc back to options';
        }
        return 'Tab/↑↓ select · Enter confirm · Esc cancel · Ctrl+C discard';
    }
    _renderConfirmOptions() {
        // Save feedback text before re-render (innerHTML destroys old textarea)
        const oldTa = this._confirmWrapper.querySelector('.skillbot-confirm-feedback');
        const savedFeedback = oldTa ? oldTa.value : '';
        const options = [
            'Yes, accept edits (code cells generated, manual review)',
            'Yes, auto-execute (code cells generated and run)',
            'No, revise this plan',
        ];
        const optionsHtml = options.map((label, i) => {
            const cls = i === this._planConfirmOptionIdx
                ? 'skillbot-confirm-option skillbot-confirm-option-active'
                : 'skillbot-confirm-option';
            return `<div class="${cls}">${label}</div>`;
        }).join('');
        const feedbackStyle = this._planConfirmFeedbackMode ? '' : 'display:none;';
        this._confirmWrapper.innerHTML = `
      <div class="skillbot-confirm-label">Plan preview</div>
      <div class="skillbot-plan-preview">${this._esc(this._planCurrentSummary)}</div>
      <div class="skillbot-confirm-label">Approve this plan?</div>
      ${optionsHtml}
      <textarea class="skillbot-confirm-feedback" style="${feedbackStyle}"
                placeholder="Type your revision feedback, then press Enter..."></textarea>
      <div class="skillbot-confirm-hint">${this._getConfirmHint()}</div>
    `;
        // Restore saved feedback text
        if (savedFeedback) {
            const newTa = this._confirmWrapper.querySelector('.skillbot-confirm-feedback');
            if (newTa)
                newTa.value = savedFeedback;
        }
        if (this._planConfirmFeedbackMode) {
            const ta = this._confirmWrapper.querySelector('.skillbot-confirm-feedback');
            if (ta)
                ta.focus();
        }
    }
    _closeConfirm() {
        this._planConfirmActive = false;
        this._planConfirmFeedbackMode = false;
        this._planConfirmOptionIdx = 0;
        this._planCurrentSummary = '';
        this._confirmWrapper.style.display = 'none';
        this._inputWrapper.style.display = 'flex';
    }
    _sendConfirmToBackend(cmd) {
        this._startBlock();
        this._renderPrompt(cmd);
        this._startSpinner();
        this._setStatus('…', 'implementing');
        if (this._kernel) {
            const code = `get_ipython().user_ns['_panel_input'](${JSON.stringify(cmd)})`;
            const future = this._kernel.requestExecute({ code, store_history: false });
            let firstStdout = true;
            future.onIOPub = (msg) => {
                var _a;
                if (msg.header.msg_type === 'stream' && ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.name) === 'stdout') {
                    if (firstStdout) {
                        this._renderResponseText(this._stripAnsi(msg.content.text));
                        firstStdout = false;
                    }
                    else {
                        this._appendTextChunk(this._stripAnsi(msg.content.text));
                    }
                }
            };
        }
        this._inputEl.focus();
    }
    _submitPlanConfirm() {
        if (this._planConfirmFeedbackMode) {
            // Submit revision feedback
            const ta = this._confirmWrapper.querySelector('.skillbot-confirm-feedback');
            const feedback = ta ? ta.value.trim() : '';
            if (!feedback) {
                // Empty feedback: return to options with brief hint
                this._planConfirmFeedbackMode = false;
                const hint = this._confirmWrapper.querySelector('.skillbot-confirm-hint');
                this._renderConfirmOptions();
                if (hint) {
                    const newHint = this._confirmWrapper.querySelector('.skillbot-confirm-hint');
                    if (newHint)
                        newHint.textContent = 'Type feedback first, or select an option above';
                    setTimeout(() => {
                        const h = this._confirmWrapper.querySelector('.skillbot-confirm-hint');
                        if (h)
                            h.textContent = this._getConfirmHint();
                    }, 2000);
                }
                this._confirmWrapper.focus();
                return;
            }
            this._closeConfirm();
            this._sendConfirmToBackend(`/confirm ${feedback}`);
            return;
        }
        switch (this._planConfirmOptionIdx) {
            case 0: // Accept edits (inject cells, don't auto-execute)
                this._closeConfirm();
                this._sendConfirmToBackend('/confirm accept_edits');
                break;
            case 1: // Auto-execute (inject cells + run)
                this._closeConfirm();
                this._sendConfirmToBackend('/confirm yes');
                break;
            case 2: // Revise (show feedback textarea)
                this._planConfirmFeedbackMode = true;
                this._renderConfirmOptions();
                break;
        }
    }
    _cancelPlanConfirm() {
        this._closeConfirm();
        this._inputEl.focus();
        this._setStatus('○', 'idle');
        if (this._kernel) {
            this._kernel.requestExecute({
                code: `get_ipython().user_ns['_panel_input']("/confirm no")`,
                store_history: false,
            });
        }
    }
    // ---- helpers -------------------------------------------------------------
    _scrollBottom() {
        this._outputEl.scrollTop = this._outputEl.scrollHeight;
    }
    _stripAnsi(s) {
        return s.replace(/\x1b\[[0-9;]*m/g, '');
    }
    _esc(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }
    setTracker(tracker) {
        this._tracker = tracker;
    }
    _handleCellComm(comm, msg) {
        try {
            this._handleCellCommImpl(comm, msg);
        }
        catch (e) {
            console.error('[panel] _handleCellComm failed:', e);
        }
    }
    _handleCellCommImpl(comm, msg) {
        var _a, _b;
        const data = ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.data) || {};
        const nb = (_b = this._tracker) === null || _b === void 0 ? void 0 : _b.currentWidget;
        if (!nb)
            return;
        const model = nb.model;
        if (!model)
            return;
        const code = data.code || '';
        const auto = data.auto !== false;
        const cellType = data.cell_type || 'code';
        const replaceId = data.replace_cell_id || '';
        if (!code)
            return;
        const notebook = nb.content;
        if (replaceId) {
            const cells = model.sharedModel.cells;
            for (let i = cells.length - 1; i >= 0; i--) {
                if (cells[i].id === replaceId) {
                    cells[i].source = code;
                    notebook.activeCellIndex = i;
                    comm.send({ cell_id: cells[i].id });
                    if (cellType !== 'markdown' && auto) {
                        notebook_1.NotebookActions.run(notebook, nb.context.sessionContext);
                    }
                    return;
                }
            }
        }
        // Insert new cell + execute
        const activeIndex = notebook.activeCellIndex;
        model.sharedModel.insertCell(activeIndex + 1, {
            cell_type: cellType,
            source: code,
            metadata: {},
        });
        const newCell = model.sharedModel.cells[activeIndex + 1];
        notebook.activeCellIndex = activeIndex + 1;
        comm.send({ cell_id: newCell.id });
        if (cellType === 'markdown' || !auto)
            return;
        notebook_1.NotebookActions.run(notebook, nb.context.sessionContext);
    }
    // ---- kernel / comm -------------------------------------------------------
    resetComm() {
        if (this._comm) {
            try {
                this._comm.close();
            }
            catch (_) { }
            this._comm = null;
        }
        this._kernel = null;
        this._stopStatusTimer();
    }
    connectKernel(kernel) {
        this._kernel = kernel;
        // Re-register cell-execution target (needed on kernel restart)
        try {
            kernel.registerCommTarget('skillbot:execute-cell', (comm, msg) => {
                this._handleCellComm(comm, msg);
            });
        }
        catch (e) {
            console.error('[panel] registerCommTarget failed:', e);
        }
        if (this._comm)
            return;
        try {
            this._comm = kernel.createComm(TARGET);
            this._comm.open();
            this._comm.onMsg = (m) => {
                var _a;
                const d = ((_a = m.content) === null || _a === void 0 ? void 0 : _a.data) || {};
                switch (d.action) {
                    case 'text':
                        this._appendTextChunk(this._stripAnsi(d.content || ''));
                        break;
                    case 'tool':
                        this._renderTool(d.name || '');
                        break;
                    case 'thinking':
                        this._renderThinking(d.content || '');
                        break;
                    case 'code_block':
                        this._renderCodeBlock(d.language || '', d.code || '');
                        break;
                    case 'result':
                        this._renderResult(d.summary || '');
                        break;
                    case 'plan_confirm':
                        if (this._planConfirmActive)
                            this._closeConfirm();
                        this._stopSpinner();
                        this._streaming = false;
                        this._responseStarted = false;
                        this._setStatus('⏸', 'plan');
                        this._renderPlanBlock(d.summary || '');
                        this._renderPlanConfirm(d.summary || '');
                        this._saveState();
                        break;
                    case 'clear':
                        this._clear();
                        break;
                }
            };
        }
        catch (e) {
            console.error('[panel] createComm failed:', e);
        }
    }
}
AgentPanel.STORAGE_KEY = 'skillbot-panel';
// ---- mode cycling (cc-haha: Shift+Tab) ----
AgentPanel.MODE_ORDER = ['default', 'plan', 'auto'];
AgentPanel.MODE_COLOR = {
    default: '',
    plan: 'rgb(0,102,102)', // cyan, cc-haha planMode
    auto: 'rgb(135,0,255)', // purple, cc-haha autoAccept
};
AgentPanel.MODE_SYMBOL = {
    default: '',
    plan: '⏸',
    auto: '⏵⏵',
};
AgentPanel.MODE_INFO = {
    plan: ['Plan mode — I\'ll explore first, then design a plan for your approval',
        'Plan mode — describe your task, I\'ll research & propose an approach',
        'Plan mode — no code is written until you approve the plan'],
    auto: ['Auto mode — cells are generated and executed automatically',
        'Auto mode — I\'ll write code and run it without asking'],
    default: ['Default mode — cells are generated but need manual execution',
        'Default mode — I decide whether to plan first or write code directly'],
};
// ===========================================================================
// Plugin
// ===========================================================================
exports.panelPlugin = {
    id: 'skillbot:tui',
    autoStart: true,
    requires: [notebook_1.INotebookTracker],
    activate: (_app, tracker) => {
        const panel = new AgentPanel();
        panel.setTracker(tracker);
        _app.shell.add(panel, 'right', { rank: 100 });
        _panelInstance = panel;
        let _panelOpened = false;
        let _currentCtx = null;
        const onKernelChanged = (_sender, args) => {
            if (args.oldValue) {
                panel.resetComm();
                panel._clear();
            }
            if (args.newValue)
                panel.connectKernel(args.newValue);
        };
        const register = () => {
            var _a;
            const nb = tracker.currentWidget;
            if (!nb)
                return;
            const ctx = nb.context.sessionContext;
            if (!ctx)
                return;
            // wire kernel restart handler when context changes
            if (ctx !== _currentCtx) {
                if (_currentCtx)
                    _currentCtx.kernelChanged.disconnect(onKernelChanged);
                _currentCtx = ctx;
                ctx.kernelChanged.connect(onKernelChanged);
            }
            const kernel = (_a = ctx.session) === null || _a === void 0 ? void 0 : _a.kernel;
            if (kernel) {
                // register cell-execution target directly (not through connectKernel)
                try {
                    kernel.registerCommTarget('skillbot:execute-cell', (comm, msg) => {
                        panel._handleCellComm(comm, msg);
                    });
                }
                catch (e) {
                    console.error('[panel] registerCommTarget failed:', e);
                }
                panel.connectKernel(kernel);
            }
            // open panel once, after layout restore settles (avoid flash-close)
            if (!_panelOpened) {
                _panelOpened = true;
                setTimeout(() => _app.shell.activateById(panel.id), 300);
            }
        };
        tracker.currentChanged.connect(() => register());
        setTimeout(register, 500);
    },
};
