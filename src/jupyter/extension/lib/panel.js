"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.panelPlugin = void 0;
const widgets_1 = require("@lumino/widgets");
const notebook_1 = require("@jupyterlab/notebook");
const panelStyles_1 = require("./panelStyles");
const R = __importStar(require("./panelRenderer"));
const PC = __importStar(require("./panelPlanConfirm"));
const TARGET = 'skillbot:tui';
let _panelInstance = null;
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
        this._thinkingEl = null; // accumulated thinking element
        this._thinkingCollapsed = true; // Ctrl+T: default collapsed (150 chars)
        this._busy = false; // agent is working → queue new prompts
        this._promptQueue = [];
        this._skillsMode = false; // skills view active → input hidden
        // ---- skill rendering ----
        this._skillRows = [];
        this._skillSelectedIdx = 0;
        this._skillListWrapper = null;
        this._skillData = [];
        this._expandedIdx = -1; // -1=list, >=0=info view
        this._fullBodyIdx = -1; // -1=not in full body, >=0=full body view
        this._installMode = false; // showing install path input
        this._installError = ''; // error message from last install
        this._configPending = false; // waiting for config confirm (y/n)
        this.id = 'skillbot:tui';
        this.title.label = 'Agent';
        this.title.closable = true;
        // Light-DOM min styles (just enough for JupyterLab to lay out the panel)
        this.node.style.display = 'flex';
        this.node.style.flexDirection = 'column';
        this.node.style.minWidth = '300px';
        this.node.style.backgroundColor = panelStyles_1.CC.bg;
        this.node.style.color = panelStyles_1.CC.text;
        // Shadow DOM — isolates all CSS from JupyterLab
        this._root = this.node.attachShadow({ mode: 'open' });
        const style = document.createElement('style');
        style.textContent = panelStyles_1.STYLES;
        this._root.appendChild(style);
        // welcome banner
        const welcome = document.createElement('div');
        welcome.className = 'skillbot-welcome';
        welcome.innerHTML = `
      <div style="font-size:14px;font-weight:600;color:${panelStyles_1.CC.text};margin-bottom:4px;">Agent Panel</div>
      <div style="font-size:12px;font-weight:500;color:rgb(180,180,180);">Enter send · Shift+↵ newline · ↑↓ history · Shift+Tab mode · Ctrl+T thinking · Ctrl+C interrupt · /skills manage</div>
    `;
        this._root.appendChild(welcome);
        // output — click to focus input + keyboard for Ctrl+T
        this._outputEl = document.createElement('div');
        this._outputEl.className = 'skillbot-output';
        this._outputEl.tabIndex = 0;
        this._outputEl.addEventListener('keydown', (e) => {
            var _a, _b;
            if (document.activeElement === this._inputEl)
                return;
            if (e.ctrlKey && !e.altKey) {
                switch (e.key) {
                    case 't':
                        e.preventDefault();
                        this._toggleThinkingCollapse();
                        break;
                    case 'c':
                        e.preventDefault();
                        (_a = this._kernel) === null || _a === void 0 ? void 0 : _a.interrupt();
                        this._setStatus('⏏', 'interrupted');
                        break;
                }
            }
            // Esc exits skills mode even when list is not focused
            if (e.key === 'Escape' && this._skillsMode && this._expandedIdx === -1) {
                e.preventDefault();
                this._exitSkillsMode();
            }
            // Esc cancels config pending when output is focused
            if (e.key === 'Escape' && this._configPending) {
                e.preventDefault();
                if (this._kernel) {
                    this._kernel.requestExecute({
                        code: `get_ipython().user_ns['_panel_input']('/config --no')`,
                        store_history: false,
                    });
                }
                this._configPending = false;
                this._infoEl.innerHTML = '';
            }
            // Trap Tab within panel when in skills mode
            if (e.key === 'Tab' && this._skillsMode) {
                e.preventDefault();
                (_b = this._skillListWrapper) === null || _b === void 0 ? void 0 : _b.focus();
            }
        });
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
        var _a;
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
                        // First Ctrl+C: clear input
                        el.value = '';
                        this._historyIdx = -1;
                        this._historyDraft = '';
                        this._killRing = '';
                        this._lastKill = '';
                        this._resizeInput();
                    }
                    else {
                        // Second Ctrl+C (or first on empty input): interrupt agent
                        (_a = this._kernel) === null || _a === void 0 ? void 0 : _a.interrupt();
                        this._setStatus('⏏', 'interrupted');
                    }
                    return;
                }
                case 'l':
                    e.preventDefault();
                    this._clear();
                    return;
                case 't':
                    e.preventDefault();
                    this._toggleThinkingCollapse();
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
            if (this._configPending && this._kernel) {
                this._kernel.requestExecute({
                    code: `get_ipython().user_ns['_panel_input']('/config --no')`,
                    store_history: false,
                });
            }
            this._configPending = false;
            this._infoEl.innerHTML = '';
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
        // Config confirmation: y/n without Ctrl (skip if IME is composing)
        if (this._configPending && !ctrl && !e.altKey && (e.key === 'y' || e.key === 'n')) {
            e.preventDefault();
            e.stopPropagation();
            const cmd = e.key === 'y' ? '/config --yes' : '/config --no';
            this._configPending = false;
            this._infoEl.innerHTML = '';
            if (this._kernel) {
                const future = this._kernel.requestExecute({
                    code: `get_ipython().user_ns['_panel_input']('${cmd}')`,
                    store_history: false,
                });
            }
            return;
        }
        // Reset kill ring on printable character input
        if (e.key.length === 1 && !ctrl && !e.altKey) {
            this._killRing = '';
            this._lastKill = '';
            // Any other key cancels config pending (send --no to backend)
            if (!e.isComposing && this._configPending && e.key !== 'y' && e.key !== 'n') {
                this._configPending = false;
                this._infoEl.innerHTML = '';
                if (this._kernel) {
                    this._kernel.requestExecute({
                        code: `get_ipython().user_ns['_panel_input']('/config --no')`,
                        store_history: false,
                    });
                }
            }
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
        for (const c of ['/confirm ', '/clear', '/mode ', '/skills ', '/config ']) {
            if (c.startsWith(val) && c !== val) {
                this._inputEl.value = c;
                this._inputEl.selectionStart = this._inputEl.selectionEnd = c.length;
                this._resizeInput();
                return;
            }
        }
        // /skills subcommands
        if (val.startsWith('/skills ')) {
            const sub = val.slice(8);
            for (const c of ['list', 'info ', 'enable ', 'disable ', 'install ', 'uninstall ']) {
                if (c.startsWith(sub) && c !== sub) {
                    this._inputEl.value = '/skills ' + c;
                    this._inputEl.selectionStart = this._inputEl.selectionEnd = ('/skills ' + c).length;
                    this._resizeInput();
                    return;
                }
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
    _isDisplayCommand(text) {
        return AgentPanel.DISPLAY_COMMANDS.some(c => text === c || text.startsWith(c + ' '));
    }
    _sendPrompt() {
        if (this._planConfirmActive)
            return;
        const text = this._inputEl.value.trim();
        if (!text)
            return;
        // Defensive: if config was pending and user somehow sent 'y'/'n' as query, ignore
        if ((text === 'y' || text === 'n') && !this._configPending) {
            this._inputEl.value = '';
            this._historyDraft = '';
            this._resizeInput();
            return;
        }
        // Slash commands bypass queue
        const isSlash = text.startsWith('/');
        if (this._busy && !isSlash) {
            this._promptQueue.push({ text, mode: this._mode });
            this._updateStatusDisplay();
            this._inputEl.value = '';
            this._historyDraft = '';
            this._resizeInput();
            return;
        }
        if (this._history.length === 0 || this._history[this._history.length - 1] !== text) {
            this._history.push(text);
        }
        this._historyIdx = -1;
        const isDisplay = this._isDisplayCommand(text);
        if (!isSlash) {
            this._busy = true;
        }
        if (isDisplay) {
            // Skills commands enter dedicated view
            if (text === '/skills' || text.startsWith('/skills ')) {
                this._enterSkillsMode();
            }
            // Config outside skills mode — exit if needed
            if ((text === '/config' || text.startsWith('/config ')) && this._skillsMode) {
                this._exitSkillsMode();
            }
        }
        else {
            this._startBlock();
            this._renderPrompt(text);
            this._startSpinner();
            this._setStatus('…', 'thinking');
        }
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
        this._thinkingEl = null;
    }
    _appendToBlock(el) {
        const target = this._currentBlock || this._outputEl;
        target.appendChild(el);
        this._scrollBottom();
    }
    // ---- renderers ----------------------------------------------------------
    _ensureResponsePrefix() { R.ensureResponsePrefix(this); }
    _renderPrompt(text) { R.renderPrompt(this, text); }
    _renderResponseText(content) { R.renderResponseText(this, content); }
    _appendTextChunk(content) { R.appendTextChunk(this, content); }
    _renderTool(name) { R.renderTool(this, name); }
    _renderThinking(content) { R.renderThinking(this, content); }
    _renderCodeBlock(l, c) { R.renderCodeBlock(this, l, c); }
    _renderPlanBlock(text) { R.renderPlanBlock(this, text); }
    _renderResult(summary) { R.renderResult(this, summary); }
    _enterSkillsMode() {
        this._skillsMode = true;
        this._inputWrapper.style.display = 'none';
        this._outputEl.querySelectorAll('.skillbot-skill-list').forEach(el => el.remove());
    }
    _exitSkillsMode() {
        this._skillsMode = false;
        this._inputWrapper.style.display = '';
        this._skillRows = [];
        this._skillSelectedIdx = 0;
        this._expandedIdx = -1;
        this._outputEl.querySelectorAll('.skillbot-skill-list').forEach(el => el.remove());
        this._inputEl.focus();
        // Reset textarea height (lost during display:none)
        setTimeout(() => this._resizeInput(), 0);
    }
    _renderSkillList(skills) {
        this._skillData = skills.map(s => ({ ...s, body: s.body || '' }));
        this._skillRows = [];
        this._skillSelectedIdx = 0;
        this._expandedIdx = -1;
        this._fullBodyIdx = -1;
        this._installMode = false;
        this._installError = '';
        // Remove old list, rebuild
        this._outputEl.querySelectorAll('.skillbot-skill-list').forEach(el => el.remove());
        const wrapper = document.createElement('div');
        wrapper.className = 'skillbot-skill-list';
        wrapper.tabIndex = 0;
        wrapper.style.outline = 'none';
        wrapper.innerHTML = `<div style="font-size:13px;font-weight:600;color:${panelStyles_1.CC.text};margin-bottom:4px;padding:0 4px;">Skills</div>`;
        const listEl = document.createElement('div');
        listEl.className = 'skillbot-skill-items';
        wrapper.appendChild(listEl);
        const hint = document.createElement('div');
        hint.className = 'skillbot-skill-hint';
        hint.style.cssText = `font-size:10px;color:rgb(120,120,120);margin-top:4px;padding:0 4px;`;
        hint.textContent = skills.length === 0
            ? 'Press i to install from .zip  Esc close'
            : '↑↓ select  Enter details  Space toggle  d uninstall  i install  Esc close';
        wrapper.appendChild(hint);
        wrapper.addEventListener('keydown', (e) => this._onSkillKeydown(e));
        this._skillListWrapper = wrapper;
        this._outputEl.appendChild(wrapper);
        this._scrollBottom();
        this._refreshSkillRows();
        // Focus wrapper so keyboard nav works (input is hidden in skills mode)
        setTimeout(() => wrapper.focus(), 50);
        // Focus the list so keyboard nav works (input is hidden in skills mode)
        setTimeout(() => wrapper.focus(), 50);
    }
    _onSkillKeydown(e) {
        var _a;
        // Install mode handled separately
        if (this._installMode) {
            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                this._installMode = false;
                this._refreshSkillRows();
                setTimeout(() => { var _a; return (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.focus(); }, 0);
            }
            return;
        }
        // Level 3: full body view — only Esc → back to info
        if (this._fullBodyIdx !== -1) {
            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                this._fullBodyIdx = -1;
                this._refreshSkillRows();
                setTimeout(() => { var _a; return (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.focus(); }, 0);
            }
            return;
        }
        // Level 2: info view — Enter → full body, Esc → list
        if (this._expandedIdx !== -1) {
            if (e.key === 'Enter') {
                e.preventDefault();
                e.stopPropagation();
                this._fullBodyIdx = this._expandedIdx;
                this._refreshSkillRows();
                setTimeout(() => { var _a; return (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.focus(); }, 0);
                return;
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                this._expandedIdx = -1;
                this._fullBodyIdx = -1;
                this._refreshSkillRows();
                setTimeout(() => { var _a; return (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.focus(); }, 0);
            }
            return;
        }
        const skills = this._skillData;
        // Allow install + exit even when list is empty
        if (!skills.length) {
            if (e.key === 'i') {
                e.preventDefault();
                e.stopPropagation();
                this._installMode = true;
                this._installError = '';
                this._refreshSkillRows();
            }
            else if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                this._exitSkillsMode();
            }
            return;
        }
        switch (e.key) {
            case 'i':
                // Install — show inline path input
                e.preventDefault();
                e.stopPropagation();
                this._installMode = true;
                this._installError = '';
                this._refreshSkillRows();
                // Focus the input after render
                setTimeout(() => {
                    var _a;
                    const inp = (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.querySelector('.skillbot-install-input');
                    inp === null || inp === void 0 ? void 0 : inp.focus();
                }, 50);
                break;
            case 'd':
                // Uninstall — requires double-tap for safety
                e.preventDefault();
                e.stopPropagation();
                const toRemove = skills[this._skillSelectedIdx];
                if (!toRemove)
                    break;
                // Show confirmation hint
                const hintEl = (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.querySelector('.skillbot-skill-hint');
                if (hintEl) {
                    hintEl.textContent = `Press d again to confirm uninstall of "${toRemove.name}" (any other key to cancel)`;
                    hintEl.style.color = 'rgb(220,120,100)';
                }
                // Wait for second keypress (auto-cancel after 3s)
                let cancelled = false;
                const cancelTimer = setTimeout(() => {
                    var _a;
                    cancelled = true;
                    (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.removeEventListener('keydown', onConfirm);
                    if (hintEl) {
                        hintEl.style.color = '';
                    }
                    this._refreshSkillRows();
                }, 3000);
                const onConfirm = (e2) => {
                    var _a;
                    if (cancelled)
                        return;
                    clearTimeout(cancelTimer);
                    (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.removeEventListener('keydown', onConfirm);
                    if (hintEl) {
                        hintEl.style.color = '';
                    }
                    if (e2.key === 'd') {
                        if (this._kernel) {
                            this._kernel.requestExecute({
                                code: `get_ipython().user_ns['_panel_input']('/skills uninstall ${toRemove.name}')`,
                                store_history: false,
                            });
                        }
                        this._skillData.splice(this._skillSelectedIdx, 1);
                        this._skillSelectedIdx = Math.min(this._skillSelectedIdx, this._skillData.length - 1);
                        this._refreshSkillRows();
                    }
                    else {
                        this._refreshSkillRows(); // reset hint
                    }
                };
                setTimeout(() => {
                    var _a;
                    (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.addEventListener('keydown', onConfirm, { once: false });
                }, 0);
                break;
            case 'Tab':
            case 'ArrowDown':
                e.preventDefault();
                e.stopPropagation();
                this._skillSelectedIdx = Math.min(skills.length - 1, this._skillSelectedIdx + 1);
                this._refreshSkillRows();
                break;
            case 'ArrowUp':
                e.preventDefault();
                e.stopPropagation();
                this._skillSelectedIdx = Math.max(0, this._skillSelectedIdx - 1);
                this._refreshSkillRows();
                break;
            case 'Enter':
                e.preventDefault();
                e.stopPropagation();
                this._expandedIdx = this._skillSelectedIdx;
                this._refreshSkillRows();
                break;
            case ' ':
                e.preventDefault();
                e.stopPropagation();
                const s = skills[this._skillSelectedIdx];
                if (s && this._kernel) {
                    s.enabled = !s.enabled;
                    this._refreshSkillRows();
                    this._kernel.requestExecute({
                        code: `get_ipython().user_ns['_panel_input']('/skills toggle ${s.name}')`,
                        store_history: false,
                    });
                }
                break;
            case 'Escape':
                e.preventDefault();
                e.stopPropagation();
                this._exitSkillsMode();
                break;
        }
    }
    _refreshSkillRows() {
        var _a, _b;
        const listEl = (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.querySelector('.skillbot-skill-items');
        if (!listEl)
            return;
        listEl.innerHTML = '';
        this._skillRows = [];
        // Empty state in list area
        if (!this._installMode && this._skillData.length === 0) {
            const empty = document.createElement('div');
            empty.style.cssText = `padding:12px 4px;font-size:12px;color:rgb(120,120,120);text-align:center;`;
            empty.textContent = 'No skills installed';
            listEl.appendChild(empty);
        }
        // Install mode: show input row
        if (this._installMode) {
            const row = document.createElement('div');
            row.style.cssText = `padding:4px;display:flex;gap:6px;align-items:center;`;
            const input = document.createElement('input');
            input.className = 'skillbot-install-input';
            input.type = 'text';
            input.placeholder = 'path/to/skill.zip';
            input.style.cssText = `flex:1;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:${panelStyles_1.CC.text};padding:4px 8px;border-radius:3px;font-size:12px;outline:none;`;
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    e.stopPropagation();
                    const path = input.value.trim();
                    if (path && this._kernel) {
                        this._kernel.requestExecute({
                            code: `get_ipython().user_ns['_panel_input']('/skills install ${path.replace(/'/g, "\\'")}')`,
                            store_history: false,
                        });
                    }
                    // Close input, wait for skill_list refresh
                    this._installMode = false;
                    this._refreshSkillRows();
                    setTimeout(() => { var _a; return (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.focus(); }, 0);
                }
                if (e.key === 'Escape') {
                    e.preventDefault();
                    e.stopPropagation();
                    this._installMode = false;
                    this._refreshSkillRows();
                    setTimeout(() => { var _a; return (_a = this._skillListWrapper) === null || _a === void 0 ? void 0 : _a.focus(); }, 0);
                }
            });
            row.appendChild(input);
            const label = document.createElement('span');
            label.style.cssText = `font-size:10px;color:rgb(140,140,140);white-space:nowrap;`;
            label.textContent = 'Enter to install';
            row.appendChild(label);
            listEl.appendChild(row);
            // Show last error
            if (this._installError) {
                const errRow = document.createElement('div');
                errRow.style.cssText = `padding:4px;font-size:11px;color:rgb(220,120,100);`;
                errRow.textContent = this._installError;
                listEl.appendChild(errRow);
            }
        }
        this._skillData.forEach((s, i) => {
            const selected = i === this._skillSelectedIdx;
            const expanded = i === this._expandedIdx;
            const row = document.createElement('div');
            row.style.cssText = `padding:2px 4px;border-radius:3px;background:${selected ? 'rgba(255,255,255,0.08)' : ''};`;
            const header = document.createElement('div');
            header.style.cssText = `display:flex;align-items:center;gap:8px;cursor:pointer;`;
            const dot = s.enabled
                ? `<span style="color:rgb(100,200,100);font-size:14px;">●</span>`
                : `<span style="color:rgb(200,100,100);font-size:14px;">●</span>`;
            const status = s.enabled ? 'enabled' : 'disabled';
            const statusColor = s.enabled ? 'rgb(100,200,100)' : 'rgb(200,100,100)';
            header.innerHTML = `${dot} <span style="color:${panelStyles_1.CC.text};font-size:12px;">${this._esc(s.name)}</span> <span style="color:${statusColor};font-size:10px;margin-left:auto;">${status}</span>`;
            row.appendChild(header);
            if (expanded) {
                const showFull = this._fullBodyIdx === i;
                const detail = document.createElement('div');
                detail.style.cssText = `margin:6px 0 4px 22px;font-size:11px;color:rgb(180,180,180);line-height:1.5;`;
                if (showFull) {
                    // Level 3: full SKILL.md body
                    detail.innerHTML = `<div style="color:${panelStyles_1.CC.text};background:rgba(255,255,255,0.04);padding:8px;border-radius:3px;max-height:350px;overflow-y:auto;white-space:pre-wrap;font-size:11px;line-height:1.4;">${this._esc(s.body || '')}</div>`;
                }
                else {
                    // Level 2: info view (description + truncated body)
                    detail.innerHTML = `<div style="margin-bottom:4px;">${this._esc(s.description)}</div>`;
                    if (s.body) {
                        const bodyText = s.body.slice(0, 1000);
                        detail.innerHTML += `<div style="color:${panelStyles_1.CC.text};background:rgba(255,255,255,0.03);padding:6px;border-radius:3px;max-height:150px;overflow-y:auto;white-space:pre-wrap;font-size:11px;">${this._esc(bodyText)}${s.body.length > 1000 ? '...' : ''}</div>`;
                    }
                }
                row.appendChild(detail);
            }
            listEl.appendChild(row);
            this._skillRows.push(row);
        });
        const hintEl = (_b = this._skillListWrapper) === null || _b === void 0 ? void 0 : _b.querySelector('.skillbot-skill-hint');
        if (hintEl) {
            if (this._installMode) {
                hintEl.textContent = 'Enter install path to skill.zip  Esc cancel';
            }
            else if (this._skillData.length === 0) {
                hintEl.textContent = 'Press i to install from .zip  Esc close';
            }
            else if (this._fullBodyIdx !== -1) {
                hintEl.textContent = 'Esc back to info';
            }
            else if (this._expandedIdx !== -1) {
                hintEl.textContent = 'Enter full body  Esc back to list';
            }
            else {
                hintEl.textContent = '↑↓ select  Enter details  Space toggle  d uninstall  i install  Esc close';
            }
        }
    }
    _renderSkillInfo(skill) {
        const wrapper = document.createElement('div');
        wrapper.className = 'skillbot-skill-info';
        const dot = skill.enabled
            ? `<span style="color:rgb(100,200,100);font-size:16px;">●</span>`
            : `<span style="color:rgb(200,100,100);font-size:16px;">●</span>`;
        const header = document.createElement('div');
        header.style.cssText = `font-size:14px;font-weight:600;color:${panelStyles_1.CC.text};margin-bottom:4px;`;
        header.innerHTML = `${dot} ${this._esc(skill.name)}`;
        const meta = document.createElement('div');
        meta.style.cssText = `font-size:12px;color:rgb(180,180,180);margin-bottom:8px;line-height:1.5;`;
        meta.innerHTML = `
      ${this._esc(skill.description)}<br>
      <span style="color:rgb(140,140,140);">Status:</span> ${skill.enabled ? 'enabled' : 'disabled'}<br>
      <span style="color:rgb(140,140,140);">Path:</span> ${this._esc(skill.path)}
    `;
        const bodyText = (skill.body || '').slice(0, 1500);
        const bodyWrap = document.createElement('div');
        bodyWrap.style.cssText = `font-size:12px;color:${panelStyles_1.CC.text};background:rgba(255,255,255,0.04);padding:8px;border-radius:4px;max-height:200px;overflow-y:auto;white-space:pre-wrap;line-height:1.4;`;
        bodyWrap.textContent = bodyText;
        if ((skill.body || '').length > 1500) {
            bodyWrap.textContent += '\n\n... (truncated)';
        }
        wrapper.appendChild(header);
        wrapper.appendChild(meta);
        wrapper.appendChild(bodyWrap);
        this._appendToBlock(wrapper);
    }
    // ---- thinking collapse (Ctrl+T) ----
    _toggleThinkingCollapse() {
        this._thinkingCollapsed = !this._thinkingCollapsed;
        this._applyThinkingCollapse();
        const status = this._thinkingCollapsed ? 'collapsed' : 'expanded';
        this._infoEl.innerHTML = `<span style="color:rgb(0,180,180)">thinking ${status} · ctrl+t to toggle</span>`;
        if (this._infoTimer)
            clearTimeout(this._infoTimer);
        this._infoTimer = setTimeout(() => { this._infoEl.innerHTML = ''; }, 4000);
    }
    _applyThinkingCollapse() {
        // Use live _thinkingEl during streaming, DOM search for Ctrl+T toggle
        const els = (this._thinkingEl && this._thinkingEl.parentElement)
            ? [this._thinkingEl]
            : Array.from(this._outputEl.querySelectorAll('.skillbot-thinking-line'));
        els.forEach((el) => {
            if (this._thinkingCollapsed) {
                const currentFull = el.getAttribute('data-full') || el.textContent || '';
                el.setAttribute('data-full', currentFull);
                const truncated = currentFull.length > 150 ? currentFull.slice(0, 150) + '...' : currentFull;
                if (el.textContent !== truncated)
                    el.textContent = truncated;
                el.style.cursor = 'pointer';
                el.title = 'ctrl+t to expand';
            }
            else {
                const fullText = el.getAttribute('data-full');
                if (fullText) {
                    el.textContent = fullText;
                    el.removeAttribute('data-full');
                }
                el.style.cursor = '';
                el.title = '';
            }
        });
    }
    _clear() {
        this._outputEl.innerHTML = '';
        this._currentBlock = null;
        this._textEl = null;
        this._thinkingEl = null;
        this._thinkingCollapsed = true;
        this._streaming = false;
        this._busy = false;
        this._promptQueue = [];
        if (this._configPending) {
            this._configPending = false;
            this._infoEl.innerHTML = '';
            if (this._kernel) {
                this._kernel.requestExecute({
                    code: `get_ipython().user_ns['_panel_input']('/config --no')`,
                    store_history: false,
                });
            }
        }
        this._stopSpinner();
        this._setStatus('○', 'idle');
        this._closeConfirm(); // ensure confirm UI is dismissed
        this._saveState();
        this._inputEl.value = '';
        this._historyIdx = -1;
        this._historyDraft = '';
        this._resizeInput();
    }
    _dequeueNext() {
        if (this._promptQueue.length === 0) {
            this._updateStatusDisplay();
            return;
        }
        const next = this._promptQueue.shift();
        // Cancel any active plan confirm — dequeued prompt takes priority
        if (this._planConfirmActive) {
            this._cancelPlanConfirm();
        }
        // Temporarily switch mode for the queued prompt
        const savedMode = this._mode;
        this._mode = next.mode;
        this._inputEl.value = next.text;
        this._busy = false;
        this._sendPrompt();
        this._mode = savedMode;
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
        const q = this._promptQueue.length > 0
            ? ` <span style="color:rgb(215,119,87)">queued:${this._promptQueue.length}</span>`
            : '';
        if (icon === '…' && this._execStartTime > 0) {
            const elapsed = Math.floor((Date.now() - this._execStartTime) / 1000);
            this._statusEl.innerHTML = `<span>${icon} ${label} (${elapsed}s)${q}</span><span>skillbot</span>`;
        }
        else {
            this._statusEl.innerHTML = `<span>${icon} ${label}${q}</span><span>skillbot</span>`;
        }
    }
    // ---- plan confirmation (delegates to panelPlanConfirm) ------------------
    _renderPlanConfirm(s) { PC.renderPlanConfirm(this, s); }
    _getConfirmHint() { return PC.getConfirmHint(this); }
    _renderConfirmOptions() { PC.renderConfirmOptions(this); }
    _closeConfirm() { PC.closeConfirm(this); }
    _sendConfirmToBackend(c) { PC.sendConfirmToBackend(this, c); }
    _submitPlanConfirm() { PC.submitPlanConfirm(this); }
    _cancelPlanConfirm() { PC.cancelPlanConfirm(this); }
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
            this._comm.onMsg = (m) => {
                var _a;
                const d = ((_a = m.content) === null || _a === void 0 ? void 0 : _a.data) || {};
                switch (d.action) {
                    case 'text':
                        if (this._skillsMode) {
                            const txt = this._stripAnsi(d.content || '');
                            if (txt.includes('✗'))
                                this._installError = txt.trim();
                        }
                        else {
                            const txt = this._stripAnsi(d.content || '');
                            this._appendTextChunk(txt);
                            // Backend sent config confirmation → enable y/n
                            if (txt.includes('Press y to apply')) {
                                this._configPending = true;
                                this._infoEl.innerHTML = '<span style=\"color:rgb(0,180,180)\">Press y to apply  n to cancel</span>';
                                if (this._infoTimer)
                                    clearTimeout(this._infoTimer);
                            }
                        }
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
                        if (this._planConfirmActive)
                            this._closeConfirm();
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
                    case 'skill_list':
                        if (!this._skillsMode)
                            this._enterSkillsMode();
                        this._installMode = false;
                        this._installError = '';
                        this._renderSkillList(d.skills || []);
                        break;
                    case 'ready':
                        this._busy = false;
                        this._dequeueNext();
                        break;
                    case 'clear':
                        this._clear();
                        break;
                }
            };
            this._comm.open();
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
// ---- prompt -------------------------------------------------------------
AgentPanel.DISPLAY_COMMANDS = ['/clear', '/mode', '/skills', '/config'];
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
        let _cellsChangedModel = null;
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
            // Wire cell deletion tracking (disconnect old on notebook change)
            const model = nb.model;
            if (model && model.sharedModel !== _cellsChangedModel) {
                _cellsChangedModel = model.sharedModel;
                model.sharedModel.cellsChanged.connect((_sender, args) => {
                    var _a;
                    if (args.type === 'remove' && args.oldValues) {
                        for (const cell of args.oldValues) {
                            const src = cell.source || ((_a = cell.getSource) === null || _a === void 0 ? void 0 : _a.call(cell)) || '';
                            if (src.trim()) {
                                kernel === null || kernel === void 0 ? void 0 : kernel.requestExecute({
                                    code: `get_ipython().user_ns['_panel_track_cell_delete'](${JSON.stringify(src)})`,
                                    store_history: false,
                                });
                            }
                        }
                    }
                });
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
