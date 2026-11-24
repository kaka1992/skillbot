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
const apputils_1 = require("@jupyterlab/apputils");
const notebook_1 = require("@jupyterlab/notebook");
const rendermime_1 = require("@jupyterlab/rendermime");
const widgets_2 = require("@lumino/widgets");
const panelStyles_1 = require("./panelStyles");
const R = __importStar(require("./panelRenderer"));
const PC = __importStar(require("./panelPlanConfirm"));
const SS = __importStar(require("./panelSessions"));
const SK = __importStar(require("./panelSkills"));
const TARGET = 'skillbot:tui';
let _panelInstance = null;
// ===========================================================================
// AgentPanel
// ===========================================================================
class AgentPanel extends widgets_1.Widget {
    constructor(_rendermime) {
        super();
        this._rendermime = _rendermime;
        this._killRing = ''; // for Ctrl+Y yank
        this._lastKill = ''; // track consecutive kill type for accumulation
        this._charsPerLine = 80; // computed from textarea width / monospace char width
        this._topDotEl = null;
        this._statusTimer = null;
        this._execStartTime = 0;
        this._statusIcon = '○';
        this._statusLabel = 'idle';
        this._tracker = null;
        this._kernel = null; // public — accessed by plugin commands
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
        // continue confirmation (plan/default mode loop)
        this._continueConfirmActive = false;
        this._continueOptionIdx = 0;
        this._continueSummary = '';
        // message block
        this._currentBlock = null;
        this._streaming = false;
        this._responseStarted = false;
        this._textEl = null; // accumulated text element for streaming
        this._thinkingEl = null; // accumulated thinking element
        this._thinkingCollapsed = true; // Ctrl+T to toggle collapse
        this._workflowState = 'IDLE'; // backend-authoritative workflow projection
        this._workflowRevision = 0;
        this._steerTarget = null;
        this._promptQueue = [];
        this._cellReferences = [];
        this._cellCandidates = [];
        this._dropdownKind = null;
        this._skillsMode = false; // skills view active → input hidden
        // multi-session management (per-notebook conversation buffers + switcher)
        this._currentPath = ''; // notebook path bound to the shown conversation
        this._sessionsCollapsed = false; // switcher collapsed state (persisted)
        this._app = null; // app handle for docmanager:open / newUntitled
        this._markdownRendering = new WeakSet();
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
        this._commandIdx = -1;
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
        // restore session switcher collapsed state
        try {
            this._sessionsCollapsed = localStorage.getItem(SS.COLLAPSE_KEY) === '1';
        }
        catch (_) { }
        const style = document.createElement('style');
        style.textContent = panelStyles_1.STYLES;
        this._root.appendChild(style);
        // welcome banner
        const welcome = document.createElement('div');
        welcome.className = 'skillbot-welcome';
        welcome.innerHTML = `
      <div class="skillbot-welcome-header">
        <span class="skillbot-status-dot skillbot-status-dot--idle" id="skillbot-topdot"></span>
        <span class="skillbot-welcome-title">Agent Panel</span>
      </div>
      <div class="skillbot-welcome-hint">Enter send · Shift+↵ newline · ↑↓ history · Shift+Tab mode · Ctrl+T thinking · Ctrl+C interrupt · /skills manage · /continue loop · /stop task</div>
    `;
        this._root.appendChild(welcome);
        this._topDotEl = welcome.querySelector('#skillbot-topdot');
        // session switcher bar — one tab per known notebook conversation
        this._sessionBarEl = document.createElement('div');
        this._sessionBarEl.className = 'skillbot-session-bar';
        this._root.appendChild(this._sessionBarEl);
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
        // action bar — visible buttons for common agent controls
        this._actionBarEl = document.createElement('div');
        this._actionBarEl.className = 'skillbot-action-bar';
        this._root.appendChild(this._actionBarEl);
        this._renderActionBar();
        // Explicit notebook Cell references attached to the next prompt.
        this._cellReferencesEl = document.createElement('div');
        this._cellReferencesEl.className = 'skillbot-cell-references';
        this._cellReferencesEl.style.display = 'none';
        this._root.appendChild(this._cellReferencesEl);
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
        this._inputEl.addEventListener('input', () => { this._resizeInput(); this._updateCommandDropdown(); });
        this._inputEl.addEventListener('blur', () => { setTimeout(() => { this._commandDropdown.style.display = 'none'; }, 200); });
        this._inputWrapper.appendChild(this._inputEl);
        // Command dropdown
        this._commandDropdown = document.createElement('div');
        this._commandDropdown.className = 'skillbot-command-dropdown';
        this._commandDropdown.style.cssText = `display:none;position:absolute;bottom:100%;left:0;right:0;max-height:180px;overflow-y:auto;z-index:10;margin-bottom:4px;`;
        this._inputWrapper.style.position = 'relative';
        this._inputWrapper.appendChild(this._commandDropdown);
        this._commands = ['/confirm ', '/clear', '/continue ', '/mode ', '/skills ', '/config ', '/snapshot', '/stop'];
        this._commandIdx = -1;
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
        this._renderSessionBar();
    }
    // ---- keyboard -----------------------------------------------------------
    _onKeydown(e) {
        var _a;
        // continue confirm: Yes/No selection (plan-style overlay)
        if (this._continueConfirmActive) {
            if (e.key === 'ArrowUp' || (e.key === 'Tab' && e.shiftKey)) {
                e.preventDefault();
                e.stopPropagation();
                this._continueOptionIdx = (this._continueOptionIdx === 0 ? 1 : 0);
                this._renderContinueOptions();
                return;
            }
            if (e.key === 'ArrowDown' || e.key === 'Tab') {
                e.preventDefault();
                e.stopPropagation();
                this._continueOptionIdx = (this._continueOptionIdx === 0 ? 1 : 0);
                this._renderContinueOptions();
                return;
            }
            if (e.key === 'Enter') {
                e.preventDefault();
                e.stopPropagation();
                this._submitContinue();
                return;
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                this._continueOptionIdx = 1;
                this._submitContinue();
                return;
            }
            e.preventDefault();
            return;
        }
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
            if (this._commandDropdown.style.display !== 'none'
                && !e.shiftKey
                && !e.metaKey
                && !e.altKey) {
                e.preventDefault();
                this._commitCommand();
                return;
            }
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
                this._commandDropdown.style.display = 'none';
                this._sendPrompt();
            }
            return;
        }
        // ---- Command dropdown: arrows to select, Tab/Enter to commit, Esc to close ----
        if (this._commandDropdown.style.display !== 'none') {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                this._selectCommand(1);
                return;
            }
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                this._selectCommand(-1);
                return;
            }
            if (e.key === 'Enter') {
                e.preventDefault();
                this._commitCommand();
                return;
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                this._commandDropdown.style.display = 'none';
                this._commandIdx = -1;
                return;
            }
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
    _updateCommandDropdown() {
        const val = this._inputEl.value;
        const beforeCursor = val.slice(0, this._inputEl.selectionStart);
        const mention = beforeCursor.match(/(^|\s)@([^\s@]*)$/);
        if (mention) {
            const query = mention[2].toLowerCase();
            this._cellCandidates = this._collectCellReferences().filter(ref => `${ref.label} ${ref.code}`.toLowerCase().includes(query));
            this._dropdownKind = 'cell';
            this._renderCellCandidates();
            return;
        }
        if (!val.startsWith('/') || val.includes(' ')) {
            this._commandDropdown.style.display = 'none';
            this._commandIdx = -1;
            this._dropdownKind = null;
            return;
        }
        const matches = this._commands.filter(c => c.startsWith(val) && c !== val);
        if (matches.length === 0) {
            this._commandDropdown.style.display = 'none';
            this._commandIdx = -1;
            this._dropdownKind = null;
            return;
        }
        this._dropdownKind = 'command';
        if (this._commandIdx < 0 || this._commandIdx >= matches.length)
            this._commandIdx = 0;
        this._commandDropdown.innerHTML = '';
        matches.forEach((cmd, i) => {
            const item = document.createElement('div');
            item.className = i === this._commandIdx ? 'skillbot-command-item active' : 'skillbot-command-item';
            item.textContent = cmd;
            item.addEventListener('click', () => { this._inputEl.value = cmd; this._inputEl.focus(); this._commandDropdown.style.display = 'none'; });
            this._commandDropdown.appendChild(item);
        });
        this._commandDropdown.style.display = 'block';
    }
    _renderCellCandidates() {
        if (this._cellCandidates.length === 0) {
            this._commandDropdown.style.display = 'none';
            this._commandIdx = -1;
            return;
        }
        if (this._commandIdx < 0
            || this._commandIdx >= this._cellCandidates.length) {
            this._commandIdx = 0;
        }
        this._commandDropdown.innerHTML = '';
        this._cellCandidates.forEach((ref, index) => {
            var _a;
            const item = document.createElement('div');
            item.className = index === this._commandIdx
                ? 'skillbot-command-item active'
                : 'skillbot-command-item';
            const firstLine = ((_a = ref.code.split('\n').find(line => line.trim())) === null || _a === void 0 ? void 0 : _a.trim()) || '(empty)';
            item.textContent = `${ref.label}  ${firstLine.slice(0, 80)}`;
            item.title = firstLine;
            item.addEventListener('click', () => this._commitCellReference(index));
            this._commandDropdown.appendChild(item);
        });
        this._commandDropdown.style.display = 'block';
    }
    _selectCommand(delta) {
        if (this._commandDropdown.style.display === 'none')
            return;
        if (this._dropdownKind === 'cell') {
            if (this._cellCandidates.length === 0)
                return;
            this._commandIdx = (this._commandIdx + delta + this._cellCandidates.length) % this._cellCandidates.length;
            this._renderCellCandidates();
            return;
        }
        const val = this._inputEl.value;
        const matches = this._commands.filter(c => c.startsWith(val) && c !== val);
        if (matches.length === 0)
            return;
        this._commandIdx = (this._commandIdx + delta + matches.length) % matches.length;
        this._updateCommandDropdown();
    }
    _commitCommand() {
        if (this._commandDropdown.style.display === 'none')
            return;
        if (this._dropdownKind === 'cell') {
            this._commitCellReference(this._commandIdx >= 0 ? this._commandIdx : 0);
            return;
        }
        const val = this._inputEl.value;
        const matches = this._commands.filter(c => c.startsWith(val) && c !== val);
        if (matches.length === 0)
            return;
        const idx = this._commandIdx >= 0 ? this._commandIdx : 0;
        if (idx < matches.length) {
            this._inputEl.value = matches[idx];
            this._inputEl.selectionStart = this._inputEl.selectionEnd = matches[idx].length;
            this._commandDropdown.style.display = 'none';
            this._commandIdx = -1;
            this._resizeInput();
        }
    }
    _collectCellReferences() {
        var _a;
        const notebook = (_a = this._tracker) === null || _a === void 0 ? void 0 : _a.currentWidget;
        if (!(notebook === null || notebook === void 0 ? void 0 : notebook.content))
            return [];
        return notebook.content.widgets.map((cell, index) => {
            var _a, _b, _c, _d;
            const code = String(((_b = (_a = cell.model.sharedModel).getSource) === null || _b === void 0 ? void 0 : _b.call(_a)) || '');
            let output = '';
            let error = '';
            try {
                const outputs = cell.model.outputs;
                const serialized = ((_c = outputs === null || outputs === void 0 ? void 0 : outputs.toJSON) === null || _c === void 0 ? void 0 : _c.call(outputs)) || [];
                for (const item of serialized) {
                    if (item.output_type === 'error') {
                        const traceback = Array.isArray(item.traceback)
                            ? item.traceback.join('\n')
                            : '';
                        error = traceback || `${item.ename || 'Error'}: ${item.evalue || ''}`;
                    }
                    else if (item.output_type === 'stream') {
                        output += Array.isArray(item.text) ? item.text.join('') : String(item.text || '');
                    }
                    else {
                        const plain = (_d = item.data) === null || _d === void 0 ? void 0 : _d['text/plain'];
                        if (plain)
                            output += Array.isArray(plain) ? plain.join('') : String(plain);
                    }
                }
            }
            catch (_) { }
            return {
                cell_id: String(cell.model.id),
                label: `Cell ${index + 1}`,
                cell_type: String(cell.model.type || 'code'),
                code: code.slice(0, 5000),
                output: output.slice(0, 2000),
                error: error.slice(0, 2000),
            };
        });
    }
    _commitCellReference(index) {
        const ref = this._cellCandidates[index];
        if (!ref)
            return;
        this._addCellReference(ref);
        const value = this._inputEl.value;
        const cursor = this._inputEl.selectionStart;
        const before = value.slice(0, cursor);
        const match = before.match(/(^|\s)@([^\s@]*)$/);
        if (match) {
            const start = cursor - match[0].length + match[1].length;
            this._inputEl.value = value.slice(0, start) + value.slice(cursor);
            this._inputEl.selectionStart = this._inputEl.selectionEnd = start;
        }
        this._commandDropdown.style.display = 'none';
        this._dropdownKind = null;
        this._commandIdx = -1;
        this._inputEl.focus();
        this._resizeInput();
    }
    _addCellReference(ref) {
        const existing = this._cellReferences.findIndex(item => item.cell_id === ref.cell_id);
        if (existing >= 0)
            this._cellReferences.splice(existing, 1);
        this._cellReferences.push(ref);
        this._renderCellReferences();
    }
    _renderCellReferences() {
        this._cellReferencesEl.innerHTML = '';
        this._cellReferencesEl.style.display = this._cellReferences.length
            ? 'flex'
            : 'none';
        this._cellReferences.forEach(ref => {
            const chip = document.createElement('span');
            chip.className = 'skillbot-cell-reference';
            chip.title = ref.code.split('\n')[0] || ref.label;
            const label = document.createElement('span');
            label.textContent = `@${ref.label}`;
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.textContent = '×';
            remove.title = `Remove ${ref.label}`;
            remove.addEventListener('click', () => {
                this._cellReferences = this._cellReferences.filter(item => item.cell_id !== ref.cell_id);
                this._renderCellReferences();
            });
            chip.append(label, remove);
            this._cellReferencesEl.appendChild(chip);
        });
    }
    addActiveCellReference() {
        var _a, _b;
        const notebook = (_a = this._tracker) === null || _a === void 0 ? void 0 : _a.currentWidget;
        const active = notebook === null || notebook === void 0 ? void 0 : notebook.content.activeCell;
        if (!notebook || !active)
            return;
        const index = notebook.content.widgets.indexOf(active);
        const ref = this._collectCellReferences()[index];
        if (!ref)
            return;
        this._addCellReference(ref);
        (_b = this._app) === null || _b === void 0 ? void 0 : _b.shell.activateById(this.id);
        this._inputEl.focus();
    }
    _openCellPicker() {
        const prefix = this._inputEl.value && !/\s$/.test(this._inputEl.value)
            ? ' @'
            : '@';
        const cursor = this._inputEl.selectionStart;
        this._inputEl.value = (this._inputEl.value.slice(0, cursor)
            + prefix
            + this._inputEl.value.slice(this._inputEl.selectionEnd));
        const nextCursor = cursor + prefix.length;
        this._inputEl.selectionStart = this._inputEl.selectionEnd = nextCursor;
        this._inputEl.focus();
        this._updateCommandDropdown();
    }
    _tabComplete() {
        // Dropdown visible: commit current selection (or first match if no selection)
        if (this._commandDropdown.style.display !== 'none') {
            this._commitCommand();
            return;
        }
        // Fallback to old behavior for /skills subcommands
        const val = this._inputEl.value;
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
        this._renderActionBar();
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
    get _hasActiveWorkflow() {
        return this._workflowState !== 'IDLE';
    }
    get _canInterrupt() {
        return [
            'AGENT_STREAMING',
            'CELL_DISPATCHING',
            'CELL_EXECUTING',
            'AUTO_FIXING',
        ].includes(this._workflowState);
    }
    get _canSteer() {
        return ['AGENT_STREAMING', 'AUTO_FIXING'].includes(this._workflowState);
    }
    _sendPrompt() {
        if (this._planConfirmActive)
            return;
        const text = this._inputEl.value.trim();
        if (!text)
            return;
        const cellReferences = this._cellReferences.map(ref => ({ ...ref }));
        const isStop = text === '/stop' || text.startsWith('/stop ');
        if (isStop && this._canInterrupt) {
            this._interruptAgent();
        }
        // Defensive: if config was pending and user somehow sent 'y'/'n' as query, ignore
        if ((text === 'y' || text === 'n') && !this._configPending) {
            this._inputEl.value = '';
            this._historyDraft = '';
            this._resizeInput();
            return;
        }
        // Slash commands bypass queue
        const isSlash = text.startsWith('/');
        if (this._hasActiveWorkflow && !isSlash && this._canSteer && this._steerTarget) {
            if (this._history.length === 0 || this._history[this._history.length - 1] !== text) {
                this._history.push(text);
            }
            this._historyIdx = -1;
            void this._sendSteer(text, cellReferences);
            this._inputEl.value = '';
            this._cellReferences = [];
            this._renderCellReferences();
            this._historyDraft = '';
            this._resizeInput();
            return;
        }
        if (this._hasActiveWorkflow && !isSlash) {
            this._promptQueue.push({
                text,
                mode: this._mode,
                cellReferences,
            });
            this._updateStatusDisplay();
            this._inputEl.value = '';
            this._cellReferences = [];
            this._renderCellReferences();
            this._historyDraft = '';
            this._resizeInput();
            return;
        }
        // No kernel — sending would lose the prompt and leave a stuck spinner
        if (!this._kernel) {
            this._setStatus('⚠', 'idle');
            this._renderResponseText('[no kernel connected — start a kernel in the notebook first]');
            this._updateStatusDisplay();
            return;
        }
        if (this._history.length === 0 || this._history[this._history.length - 1] !== text) {
            this._history.push(text);
        }
        this._historyIdx = -1;
        const isDisplay = this._isDisplayCommand(text);
        if (!isSlash) {
            // Optimistic projection closes the small gap before the backend snapshot arrives.
            this._workflowState = 'AGENT_STREAMING';
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
            this._renderPrompt(text, cellReferences);
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
            const referencesJson = JSON.stringify(cellReferences);
            const code = `get_ipython().user_ns['_panel_input'](${JSON.stringify(text)}, mode="${this._mode}", cell_references=${JSON.stringify(referencesJson)})`;
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
        this._cellReferences = [];
        this._renderCellReferences();
        this._historyDraft = '';
        this._resizeInput();
    }
    async _sendSteer(text, refs) {
        var _a, _b;
        const target = this._steerTarget;
        if (!target)
            return;
        let message = text;
        if (refs.length) {
            message += '\n\n[Referenced Notebook Cells]\n' + refs.map(ref => JSON.stringify({
                cell_id: ref.cell_id,
                label: ref.label,
                cell_type: ref.cell_type,
                code: ref.code,
                output: ref.output,
                error: ref.error,
            })).join('\n');
        }
        this._renderPrompt(text, refs);
        this._textEl = null;
        this._thinkingEl = null;
        const messageId = ((_b = (_a = globalThis.crypto) === null || _a === void 0 ? void 0 : _a.randomUUID) === null || _b === void 0 ? void 0 : _b.call(_a))
            || `steer-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        try {
            const url = new URL(target.url);
            if (url.protocol !== 'http:'
                || url.hostname !== '127.0.0.1'
                || url.port !== '9000') {
                throw new Error('invalid steering endpoint');
            }
            const response = await fetch(url.toString(), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message_id: messageId,
                    message,
                    control_token: target.control_token,
                }),
            });
            if (!response.ok) {
                const detail = await response.text();
                throw new Error(`${response.status}: ${detail}`);
            }
            const receipt = await response.json();
            this._infoEl.innerHTML =
                `<span style="color:rgb(0,180,180)">direction queued #${Number(receipt.seq || 0)}</span>`;
        }
        catch (error) {
            this._appendTextChunk(`\nDirection not delivered: ${String(error)}\n`);
        }
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
    _renderPrompt(text, refs = []) {
        R.renderPrompt(this, text, refs);
    }
    _renderResponseText(content) { R.renderResponseText(this, content); }
    _appendTextChunk(content) { R.appendTextChunk(this, content); }
    _renderTool(name) { R.renderTool(this, name); }
    _renderThinking(content) { R.renderThinking(this, content); }
    _renderCodeBlock(l, c) { R.renderCodeBlock(this, l, c); }
    _renderPlanBlock(text) { R.renderPlanBlock(this, text); }
    _renderResult(summary) { R.renderResult(this, summary); }
    _enterSkillsMode() { SK.enterSkillsMode(this); }
    _exitSkillsMode() { SK.exitSkillsMode(this); }
    _renderSkillList(skills) { SK.renderSkillList(this, skills); }
    _onSkillKeydown(e) { SK.onSkillKeydown(this, e); }
    _refreshSkillRows() { SK.refreshSkillRows(this); }
    _renderSkillInfo(skill) { SK.renderSkillInfo(this, skill); }
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
                const collapsed = '∴ Thinking…';
                if (el.textContent !== collapsed)
                    el.textContent = collapsed;
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
        this._promptQueue = [];
        this._cellReferences = [];
        this._renderCellReferences();
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
        this._cellReferences = next.cellReferences;
        this._renderCellReferences();
        this._sendPrompt();
        this._mode = savedMode;
    }
    // ---- persistence (localStorage) ----
    // ---- session persistence + switcher (see panelSessions.ts) --------------
    _storageKey(path) { return SS.storageKey(this, path); }
    _saveState() { SS.saveState(this); }
    _restoreState() { SS.restoreState(this); }
    _loadBuffer(path) { SS.loadBuffer(this, path); }
    _applyBuffer(raw) { SS.applyBuffer(this, raw); }
    _loadRegistry() { return SS.loadRegistry(this); }
    _saveRegistry(reg) { SS.saveRegistry(this, reg); }
    _registerSession(path) { SS.registerSession(this, path); }
    _renderSessionBar() { SS.renderSessionBar(this); }
    /** Bind the JupyterLab app so the switcher can open / create notebooks. */
    setApp(app) { this._app = app; }
    /**
     * Mark a notebook path as the active conversation. Registers it in the
     * switcher and, if it differs from the currently shown one, saves the old
     * buffer and loads the target buffer. Returns true if the path changed.
     */
    setActivePath(path, kernel = this._kernel) {
        this._registerSession(path);
        if (path === this._currentPath) {
            if (!kernel && this._kernel)
                this.resetComm();
            if (kernel)
                this.connectKernel(kernel);
            return false;
        }
        if (this._currentPath)
            this._saveState(); // persist buffer we're leaving
        this._currentPath = path;
        if (!kernel && this._kernel)
            this.resetComm();
        if (kernel)
            this.connectKernel(kernel);
        this._loadBuffer(path);
        this._renderSessionBar();
        return true;
    }
    /** Tell the backend the active notebook changed so it resets agent memory. */
    notifyNotebookSwitch(path) {
        if (!this._kernel)
            return;
        try {
            this._kernel.requestExecute({
                code: `get_ipython().user_ns['_panel_switch_notebook'](${JSON.stringify(path)})`,
                store_history: false,
            });
        }
        catch (_) { }
    }
    /** Public: called by the plugin when a notebook file is deleted from disk. */
    onNotebookFileDeleted(path) { SS.onNotebookFileDeleted(this, path); }
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
        this._updateTopDot(icon);
        this._syncActionBar();
    }
    /** Map the current status icon to the top-bar dot state modifier. */
    _updateTopDot(icon) {
        if (!this._topDotEl)
            return;
        const state = icon === '…' ? 'thinking' :
            icon === '✓' ? 'done' :
                icon === '⏏' ? 'interrupted' :
                    icon === '⏸' ? 'plan' :
                        'idle';
        this._topDotEl.className = `skillbot-status-dot skillbot-status-dot--${state}`;
    }
    // ---- agent action bar ---------------------------------------------------
    /** Run a slash command from a button without disturbing the user's draft/history. */
    _dispatchCommand(cmd) {
        const draft = this._inputEl.value;
        const references = this._cellReferences.map(ref => ({ ...ref }));
        const histLen = this._history.length;
        this._inputEl.value = cmd;
        this._sendPrompt();
        // _sendPrompt pushes to history — button-issued commands shouldn't pollute it.
        if (this._history.length > histLen && this._history[this._history.length - 1] === cmd) {
            this._history.pop();
            this._historyIdx = -1;
        }
        // Restore whatever the user was typing (input is hidden in skills mode).
        if (cmd !== '/clear') {
            if (draft)
                this._inputEl.value = draft;
            this._cellReferences = references;
            this._renderCellReferences();
            if (!this._skillsMode)
                this._resizeInput();
        }
    }
    /** Interrupt the running kernel immediately (same as Ctrl+C twice). */
    _interruptAgent() {
        var _a;
        (_a = this._kernel) === null || _a === void 0 ? void 0 : _a.interrupt();
        this._setStatus('⏏', 'interrupted');
        this._stopSpinner();
        this._workflowState = 'INTERRUPTING';
        this._promptQueue = [];
        this._updateStatusDisplay();
    }
    /** Plan button: toggle between plan and default (same sync path as Shift+Tab). */
    _togglePlanMode() {
        this._mode = this._mode === 'plan' ? 'default' : 'plan';
        this._updateModeInfo();
        this._renderActionBar();
        this._saveState();
        if (this._kernel) {
            this._kernel.requestExecute({
                code: `get_ipython().user_ns['_panel_set_mode']("${this._mode}")`,
                store_history: false,
            });
        }
    }
    /** Render the visible agent controls; enable/disable by busy state. */
    _renderActionBar() {
        if (!this._actionBarEl)
            return;
        this._actionBarEl.innerHTML = '';
        const mk = (label, title, cls, on) => {
            const b = document.createElement('span');
            b.className = 'skillbot-action-btn' + (cls ? ' ' + cls : '');
            b.textContent = label;
            b.title = title;
            b.addEventListener('click', (e) => { e.preventDefault(); on(); });
            return b;
        };
        // Stop is prominent while busy, muted otherwise.
        const stop = mk('■ Stop', '停止当前任务 (/stop)', 'skillbot-action-stop', () => {
            this._dispatchCommand('/stop');
        });
        if (!this._canInterrupt)
            stop.classList.add('disabled');
        this._actionBarEl.appendChild(stop);
        // Plan is a toggle: switch into plan mode, or back to default if active.
        const plan = mk('⏸ Plan', 'Plan 模式开关 (Shift+Tab)', 'skillbot-action-plan', () => this._togglePlanMode());
        if (this._mode === 'plan')
            plan.classList.add('active');
        this._actionBarEl.appendChild(plan);
        this._actionBarEl.appendChild(mk('🗑 Clear', '清空当前会话对话', '', () => this._dispatchCommand('/clear')));
        this._actionBarEl.appendChild(mk('@', '引用 Notebook 单元格', 'skillbot-action-reference', () => {
            this._openCellPicker();
        }));
        // Skills is a toggle: open the manager, or close it if already open.
        const skills = mk('≣ Skills', '管理技能 (/skills)', 'skillbot-action-skills', () => {
            if (this._skillsMode)
                this._exitSkillsMode();
            else
                this._dispatchCommand('/skills');
        });
        if (this._skillsMode)
            skills.classList.add('active');
        this._actionBarEl.appendChild(skills);
    }
    /** Keep the Stop button's enabled/prominent state in sync with busy. */
    _syncActionBar() {
        var _a;
        const stop = (_a = this._actionBarEl) === null || _a === void 0 ? void 0 : _a.querySelector('.skillbot-action-stop');
        if (!stop)
            return;
        if (this._canInterrupt)
            stop.classList.remove('disabled');
        else
            stop.classList.add('disabled');
    }
    _applyWorkflowState(data) {
        const revision = Number(data.revision || 0);
        if (revision && revision <= this._workflowRevision)
            return;
        this._workflowRevision = revision;
        this._workflowState = String(data.state || 'IDLE');
        const display = {
            IDLE: ['✓', 'ready'],
            AGENT_STREAMING: ['…', 'thinking'],
            PLAN_REVIEW: ['⏸', 'plan'],
            WAITING_CONFIRM: ['⏸', 'confirm'],
            CELL_DISPATCHING: ['…', 'preparing cells'],
            CELL_EXECUTING: ['…', 'running cells'],
            AUTO_FIXING: ['…', 'fixing'],
            INTERRUPTING: ['⏏', 'interrupting'],
        };
        const [icon, label] = display[this._workflowState] || ['…', 'working'];
        this._setStatus(icon, label);
        if (this._workflowState === 'IDLE') {
            this._stopSpinner();
            this._dequeueNext();
        }
        else if (this._workflowState === 'PLAN_REVIEW'
            || this._workflowState === 'WAITING_CONFIRM') {
            this._stopSpinner();
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
    // ---- continue confirmation (plan-style overlay) --------------------------
    _renderContinueButtons(summary) {
        this._continueConfirmActive = true;
        this._continueOptionIdx = 0;
        this._continueSummary = summary;
        this._renderContinueOptions();
        this._inputWrapper.style.display = 'none';
        this._confirmWrapper.style.display = 'flex';
        this._confirmWrapper.focus();
    }
    _renderContinueOptions() {
        const summary = this._continueSummary;
        const options = [
            'Yes — generate and execute cells',
            'No — finish here',
        ];
        const optionsHtml = options.map((label, i) => {
            const cls = i === this._continueOptionIdx
                ? 'skillbot-confirm-option skillbot-confirm-option-active'
                : 'skillbot-confirm-option';
            return `<div class="${cls}">${label}</div>`;
        }).join('');
        this._confirmWrapper.innerHTML = `
      <div class="skillbot-confirm-label">${this._esc(summary)}</div>
      ${optionsHtml}
      <div class="skillbot-confirm-hint">↑↓ select · Enter confirm · Esc cancel</div>
    `;
    }
    _submitContinue() {
        const arg = this._continueOptionIdx === 0 ? 'yes' : 'no';
        this._continueConfirmActive = false;
        this._confirmWrapper.style.display = 'none';
        this._confirmWrapper.innerHTML = '';
        this._inputWrapper.style.display = '';
        this._inputEl.focus();
        if (this._kernel) {
            this._kernel.requestExecute({
                code: `get_ipython().user_ns['_panel_input']('/continue ${arg}')`,
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
    _renderMarkdown(host, source) {
        host.dataset.markdown = source;
        if (this._markdownRendering.has(host))
            return;
        this._markdownRendering.add(host);
        const renderLatest = async () => {
            const current = host.dataset.markdown || '';
            try {
                await (0, rendermime_1.renderMarkdown)({
                    host,
                    source: current,
                    trusted: false,
                    sanitizer: this._rendermime.sanitizer,
                    resolver: this._rendermime.resolver,
                    linkHandler: this._rendermime.linkHandler,
                    shouldTypeset: true,
                    latexTypesetter: this._rendermime.latexTypesetter,
                    markdownParser: this._rendermime.markdownParser,
                });
            }
            catch (_) {
                host.textContent = current;
            }
            if (host.dataset.markdown !== current && host.isConnected) {
                await renderLatest();
            }
            else {
                this._markdownRendering.delete(host);
            }
        };
        void renderLatest();
    }
    _ansiToHtml(s) {
        // escape raw text first so ANSI conversion can't inject markup
        s = this._esc(s);
        return s.replace(/\x1b\[32m/g, '<span style="color:#4ade80">')
            .replace(/\x1b\[31m/g, '<span style="color:#f87171">')
            .replace(/\x1b\[90m/g, '<span style="color:#999">')
            .replace(/\x1b\[0m/g, '</span>')
            .replace(/\x1b\[[0-9;]*m/g, '');
    }
    _esc(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }
    setTracker(tracker) {
        this._tracker = tracker;
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
        this._workflowState = 'IDLE';
        this._workflowRevision = 0;
        this._steerTarget = null;
        this._stopStatusTimer();
    }
    connectKernel(kernel) {
        var _a, _b;
        if (this._kernel && this._kernel !== kernel) {
            this.resetComm();
        }
        this._kernel = kernel;
        // Notify kernel of active notebook path for snapshot file isolation.
        // Must happen BEFORE `if (this._comm) return` so it fires on every
        // notebook switch and lazy kernel start (via onKernelChanged).
        const nb = (_a = this._tracker) === null || _a === void 0 ? void 0 : _a.currentWidget;
        const nbPath = ((_b = nb === null || nb === void 0 ? void 0 : nb.context) === null || _b === void 0 ? void 0 : _b.path) || '';
        if (nbPath) {
            kernel.requestExecute({
                code: `from jupyter.magic import _set_active_notebook_path; _set_active_notebook_path(${JSON.stringify(nbPath)})`,
                store_history: false,
            });
        }
        if (this._comm)
            return;
        try {
            this._comm = kernel.createComm(TARGET);
            this._comm.onMsg = (m) => {
                var _a, _b;
                const d = ((_a = m.content) === null || _a === void 0 ? void 0 : _a.data) || {};
                switch (d.action) {
                    case 'text':
                        if (this._skillsMode) {
                            const txt = this._ansiToHtml(d.content || '');
                            if (txt.includes('✗'))
                                this._installError = txt.trim();
                        }
                        else {
                            const txt = this._stripAnsi(d.content || '');
                            if (this._responseStarted) {
                                this._appendTextChunk(txt);
                            }
                            else {
                                this._renderResponseText(txt);
                            }
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
                        this._stopSpinner();
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
                    case 'skill_info': {
                        const info = d.skill || {};
                        if (!info.name)
                            break;
                        this._renderSkillInfo(info);
                        break;
                    }
                    case 'continue_confirm':
                        this._stopSpinner();
                        this._renderContinueButtons(d.summary || '');
                        break;
                    case 'ready':
                        // Compatibility fallback for older kernels without workflow_state.
                        this._stopSpinner();
                        if (this._workflowRevision === 0) {
                            this._workflowState = 'IDLE';
                            this._dequeueNext();
                        }
                        break;
                    case 'workflow_state':
                        this._applyWorkflowState(d);
                        break;
                    case 'steer_target':
                        this._steerTarget = {
                            url: String(d.url || ''),
                            run_id: String(d.run_id || ''),
                            control_token: String(d.control_token || ''),
                        };
                        break;
                    case 'steer_receipt':
                        this._infoEl.innerHTML =
                            `<span style="color:rgb(74,222,128)">direction applied #${Number(d.seq || 0)}</span>`;
                        break;
                    case 'steer_closed':
                        if (!d.run_id || ((_b = this._steerTarget) === null || _b === void 0 ? void 0 : _b.run_id) === String(d.run_id)) {
                            this._steerTarget = null;
                        }
                        break;
                    case 'clear':
                        this._clear();
                        break;
                    case 'restore_conversation':
                        // Disk copy arrived for a path with no localStorage cache.
                        if ((d.path || '') === this._currentPath && d.buffer) {
                            this._applyBuffer(d.buffer);
                            try {
                                localStorage.setItem(this._storageKey(this._currentPath), d.buffer);
                            }
                            catch (_) { }
                        }
                        break;
                    case 'conversation_list':
                        // Merge disk-persisted sessions into the switcher registry.
                        if (Array.isArray(d.sessions)) {
                            const reg = this._loadRegistry();
                            for (const s of d.sessions) {
                                if (s.path && !(s.path in reg)) {
                                    reg[s.path] = s.path.split('/').pop() || s.path;
                                }
                            }
                            this._saveRegistry(reg);
                            this._renderSessionBar();
                        }
                        break;
                }
            };
            this._comm.open();
            // Pull disk-persisted sessions into the switcher (covers fresh browsers).
            try {
                this._kernel.requestExecute({
                    code: `get_ipython().user_ns['_panel_list_conversations']()`,
                    store_history: false,
                });
            }
            catch (_) { }
        }
        catch (e) {
            console.error('[panel] createComm failed:', e);
        }
    }
}
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
AgentPanel.DISPLAY_COMMANDS = ['/clear', '/mode', '/skills', '/config', '/continue', '/stop'];
// ===========================================================================
// Notebook Snapshot Dialog
// ===========================================================================
function _jpBtn(text, kind) {
    const b = document.createElement('button');
    b.textContent = text;
    b.className = kind ? `jp-mod-styled jp-mod-${kind}` : 'jp-mod-styled';
    b.style.cssText = 'padding:4px 12px;font-size:12px;';
    return b;
}
function _showSnapshotDialog(snapshots, panel, nb, cellRestored, nbPath) {
    const container = document.createElement('div');
    container.style.cssText = `min-width:520px;max-height:550px;overflow-y:auto;font-size:13px;color:${panelStyles_1.CC.text};background:${panelStyles_1.CC.bg};padding:12px;border-radius:10px;`;
    const title = document.createElement('div');
    title.style.cssText = 'font-weight:600;margin-bottom:10px;font-size:14px;';
    const label = nbPath || '(unsaved notebook)';
    title.textContent = `Notebook Snapshots — ${label} (${snapshots.length})`;
    container.appendChild(title);
    if (cellRestored) {
        const warning = document.createElement('div');
        warning.style.cssText = `padding:6px 8px;margin-bottom:10px;background:rgba(255,107,128,0.12);border-left:2px solid ${panelStyles_1.CC.error};border-radius:0 6px 6px 0;font-size:12px;color:rgb(255,160,175);`;
        warning.textContent = '⚠ Cells have been individually restored in this session. Notebook restore will overwrite those changes.';
        container.appendChild(warning);
    }
    let selectedId = '';
    const previewPanel = document.createElement('div');
    previewPanel.style.cssText = `background:${panelStyles_1.CC.raised};padding:10px;border-radius:8px;margin-top:10px;max-height:280px;overflow-y:auto;white-space:pre-wrap;font-family:monospace;font-size:12px;color:${panelStyles_1.CC.inactive};line-height:1.5;`;
    previewPanel.textContent = 'Select a snapshot to preview';
    container.appendChild(previewPanel);
    const updateSelection = (s, row) => {
        selectedId = s.id;
        container.querySelectorAll('.snapshot-row').forEach((el) => el.style.background = '');
        row.style.background = 'rgba(0,200,200,0.14)';
        // Show preview
        const previews = s.preview || [];
        if (previews.length > 0) {
            previewPanel.textContent = previews.map((p, i) => `[${i + 1}] ${p}`).join('\n');
        }
        else {
            previewPanel.textContent = '(no code preview)';
        }
    };
    snapshots.forEach((s, i) => {
        const row = document.createElement('div');
        row.className = 'snapshot-row';
        row.style.cssText = `padding:6px 10px;cursor:pointer;border-radius:6px;display:flex;justify-content:space-between;${i === 0 ? 'background:rgba(0,200,200,0.14);' : ''}`;
        const ts = new Date((s.timestamp || 0) * 1000).toLocaleString();
        row.innerHTML = `<span style="font-size:13px;"><b>${ts}</b></span><span style="color:${panelStyles_1.CC.subtle};font-size:12px;">${s.cells_count} cells</span>`;
        row.addEventListener('click', () => updateSelection(s, row));
        container.appendChild(row);
        if (i === 0) {
            selectedId = s.id;
            previewPanel.textContent = (s.preview || []).map((p, j) => `[${j + 1}] ${p}`).join('\n') || '(no code preview)';
        }
    });
    const btnRow = document.createElement('div');
    btnRow.style.cssText = 'margin-top:10px;display:flex;gap:8px;';
    const restoreBtn = _jpBtn('Restore Notebook', 'accept');
    restoreBtn.addEventListener('click', () => {
        if (!selectedId || !panel._kernel)
            return;
        // Fetch snapshot cells, then restore directly via notebook model
        const future = panel._kernel.requestExecute({
            code: `from jupyter.notebook_snapshot import get_snapshot; import json; sid=${JSON.stringify(selectedId)}; np=${JSON.stringify(nbPath)}; print(json.dumps(get_snapshot(sid, nb_path=np).get("cells",[]) if get_snapshot(sid, nb_path=np) else []))`,
            store_history: false,
        });
        let stdout = '';
        future.onIOPub = (msg) => {
            var _a;
            if (msg.header.msg_type === 'stream' && ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.name) === 'stdout')
                stdout += msg.content.text;
        };
        future.done.then(() => {
            try {
                const cells = JSON.parse(stdout.trim());
                if (!cells || !cells.length) {
                    restoreBtn.textContent = 'No cells';
                    return;
                }
                const model = nb.model;
                if (!model) {
                    restoreBtn.textContent = 'No model';
                    return;
                }
                // Clear and repopulate
                const sharedModel = model.sharedModel;
                while (sharedModel.cells.length > 0) {
                    sharedModel.deleteCell(0);
                }
                for (const c of cells) {
                    sharedModel.insertCell(sharedModel.cells.length, {
                        cell_type: 'code',
                        source: c.code || '',
                        metadata: {},
                    });
                }
                restoreBtn.textContent = 'Restored';
                restoreBtn.className = 'jp-mod-styled';
                restoreBtn.style.cssText = 'padding:4px 12px;font-size:12px;background:var(--jp-success-color1, #1a7f37);color:var(--jp-ui-inverse-font-color1, #fff);border:1px solid var(--jp-success-color2, #1a7f37);';
            }
            catch (e) {
                console.error(e);
                restoreBtn.textContent = 'Failed';
                restoreBtn.className = 'jp-mod-styled jp-mod-warn';
            }
        });
    });
    btnRow.appendChild(restoreBtn);
    container.appendChild(btnRow);
    const bodyWidget = new widgets_1.Widget();
    bodyWidget.node.appendChild(container);
    (0, apputils_1.showDialog)({
        title: 'Notebook Snapshots',
        body: bodyWidget,
        buttons: [apputils_1.Dialog.okButton({ label: 'Close' })],
    });
}
// ===========================================================================
// Cell Snapshots Dialog
// ===========================================================================
function _stripHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}
function _showCellSnapshotsDialog(cell, versions, panel) {
    if (!versions || versions.length === 0) {
        alert('No version history for this cell.');
        return;
    }
    const container = document.createElement('div');
    container.style.cssText = `min-width:520px;max-height:550px;overflow-y:auto;font-size:13px;color:${panelStyles_1.CC.text};background:${panelStyles_1.CC.bg};padding:12px;border-radius:10px;`;
    const title = document.createElement('div');
    title.style.cssText = 'font-weight:600;margin-bottom:10px;font-size:14px;';
    title.textContent = `Cell Snapshots (${versions.length})`;
    container.appendChild(title);
    let selectedIdx = 0;
    const preview = document.createElement('div');
    preview.style.cssText = `background:${panelStyles_1.CC.raised};padding:10px;border-radius:8px;margin-top:10px;max-height:300px;overflow-y:auto;white-space:pre-wrap;font-family:monospace;font-size:12px;color:${panelStyles_1.CC.inactive};line-height:1.5;`;
    container.appendChild(preview);
    const updatePreview = (idx) => {
        const v = versions[idx];
        if (!v)
            return;
        preview.textContent = `[${v.version}] ${new Date((v.timestamp || 0) * 1000).toLocaleString()}\n\nCode:\n${v.code || ''}\n\nOutput:\n${v.output || '(none)'}`;
    };
    updatePreview(0);
    versions.forEach((v, i) => {
        const row = document.createElement('div');
        row.style.cssText = `padding:6px 10px;cursor:pointer;border-radius:6px;display:flex;justify-content:space-between;${i === 0 ? 'background:rgba(0,200,200,0.14);' : ''}`;
        const ts = new Date((v.timestamp || 0) * 1000).toLocaleString();
        const code = (v.code || '').replace(/\n/g, ' ').substring(0, 80);
        row.innerHTML = `<span style="font-size:13px;"><b>${v.version}</b> ${ts}</span><span style="color:${panelStyles_1.CC.subtle};font-size:12px;">${_stripHtml(code)}</span>`;
        row.addEventListener('click', () => {
            selectedIdx = i;
            container.querySelectorAll('div[style]').forEach((el) => el.style.background = '');
            row.style.background = 'rgba(0,200,200,0.14)';
            updatePreview(i);
        });
        container.appendChild(row);
    });
    const btnRow = document.createElement('div');
    btnRow.style.cssText = 'margin-top:10px;display:flex;gap:8px;';
    const restoreBtn = _jpBtn('Restore Selected', 'accept');
    restoreBtn.addEventListener('click', () => {
        const v = versions[selectedIdx];
        if (!v || !panel._kernel)
            return;
        const future = panel._kernel.requestExecute({
            code: `get_ipython().user_ns['_panel_input']('/cell-snapshot-restore ${cell.model.id} ${v.version}')`,
            store_history: false,
        });
        future.done.then((reply) => {
            if (reply.content.status === 'ok') {
                restoreBtn.textContent = 'Restored';
                restoreBtn.className = 'jp-mod-styled';
                restoreBtn.style.cssText = 'padding:4px 12px;font-size:12px;background:var(--jp-success-color1, #1a7f37);color:var(--jp-ui-inverse-font-color1, #fff);border:1px solid var(--jp-success-color2, #1a7f37);';
                setTimeout(() => {
                    var _a, _b;
                    // Close dialog
                    const dlg = document.querySelector('.jp-Dialog');
                    if (dlg)
                        (_b = (_a = dlg).remove) === null || _b === void 0 ? void 0 : _b.call(_a);
                }, 500);
            }
            else {
                restoreBtn.textContent = 'Failed';
                restoreBtn.className = 'jp-mod-styled jp-mod-warn';
            }
        });
    });
    btnRow.appendChild(restoreBtn);
    container.appendChild(btnRow);
    const bodyWidget = new widgets_1.Widget();
    bodyWidget.node.appendChild(container);
    (0, apputils_1.showDialog)({
        title: 'Cell History',
        body: bodyWidget,
        buttons: [apputils_1.Dialog.okButton({ label: 'Close' })],
    });
}
// ===========================================================================
// Plugin
// ===========================================================================
exports.panelPlugin = {
    id: 'skillbot:tui',
    autoStart: true,
    requires: [notebook_1.INotebookTracker, rendermime_1.IRenderMimeRegistry],
    activate: (_app, tracker, rendermime) => {
        var _a, _b;
        const panel = new AgentPanel(rendermime);
        panel.setTracker(tracker);
        panel.setApp(_app);
        _app.shell.add(panel, 'right', { rank: 100 });
        _panelInstance = panel;
        let _panelOpened = false;
        let _currentCtx = null;
        let _cellsChangedModel = null;
        const onCellsChanged = (_sender, args) => {
            var _a, _b, _c, _d, _e;
            if (args.type !== 'remove' || !args.oldValues)
                return;
            const kernel = (_b = (_a = tracker.currentWidget) === null || _a === void 0 ? void 0 : _a.context.sessionContext.session) === null || _b === void 0 ? void 0 : _b.kernel;
            for (const cell of args.oldValues) {
                const src = ((_d = (_c = cell === null || cell === void 0 ? void 0 : cell.sharedModel) === null || _c === void 0 ? void 0 : _c.getSource) === null || _d === void 0 ? void 0 : _d.call(_c)) || ((_e = cell === null || cell === void 0 ? void 0 : cell.value) === null || _e === void 0 ? void 0 : _e.text) || '';
                if (src.trim()) {
                    kernel === null || kernel === void 0 ? void 0 : kernel.requestExecute({
                        code: `get_ipython().user_ns['_panel_track_cell_delete'](${JSON.stringify(src)})`,
                        store_history: false,
                    });
                }
            }
        };
        const onKernelChanged = (_sender, args) => {
            // Always reset the comm: a kernel change (restart, switch, or lazy start
            // where oldValue is null) must never leave _comm bound to an old kernel.
            panel.resetComm();
            if (args.oldValue) {
                panel._clear();
            }
            if (args.newValue)
                panel.connectKernel(args.newValue);
        };
        const register = () => {
            var _a, _b;
            const nb = tracker.currentWidget;
            if (!nb)
                return;
            const ctx = nb.context.sessionContext;
            if (!ctx)
                return;
            // Save the old buffer on its kernel; load the new buffer on the target kernel.
            const kernel = ((_a = ctx.session) === null || _a === void 0 ? void 0 : _a.kernel) || null;
            const pathChanged = panel.setActivePath(nb.context.path || '', kernel);
            // wire kernel restart handler when context changes
            if (ctx !== _currentCtx) {
                if (_currentCtx)
                    _currentCtx.kernelChanged.disconnect(onKernelChanged);
                _currentCtx = ctx;
                ctx.kernelChanged.connect(onKernelChanged);
            }
            if (kernel && pathChanged)
                panel.notifyNotebookSwitch(nb.context.path || '');
            // Wire cell deletion tracking (disconnect old on notebook change)
            const cells = (_b = nb.model) === null || _b === void 0 ? void 0 : _b.cells;
            if (cells && cells !== _cellsChangedModel) {
                _cellsChangedModel === null || _cellsChangedModel === void 0 ? void 0 : _cellsChangedModel.changed.disconnect(onCellsChanged);
                _cellsChangedModel = cells;
                cells.changed.connect(onCellsChanged);
            }
            // open panel once, after layout restore settles (avoid flash-close)
            if (!_panelOpened) {
                _panelOpened = true;
                setTimeout(() => _app.shell.activateById(panel.id), 300);
            }
        };
        _app.commands.addCommand('skillbot:cell-reference', {
            label: 'Reference in Agent Chat',
            execute: () => panel.addActiveCellReference(),
        });
        // Cell optimization — right-click → agent improve
        _app.commands.addCommand('skillbot:cell-optimize', {
            label: 'Optimize with Agent',
            execute: async () => {
                var _a;
                const nb = tracker.currentWidget;
                if (!nb || !panel._kernel)
                    return;
                const cell = nb.content.activeCell;
                if (!cell)
                    return;
                const cellId = cell.model.id;
                const cellType = cell.model.type || 'code';
                if (cellType === 'markdown') {
                    alert('Cell optimization only works for code cells.');
                    return;
                }
                const code = cell.model.sharedModel.getSource();
                if (!code.trim()) {
                    alert('Cell is empty.');
                    return;
                }
                let output = '';
                let cellError = '';
                try {
                    const outputs = cell.model.outputs;
                    if ((outputs === null || outputs === void 0 ? void 0 : outputs.length) > 0) {
                        const last = outputs.get(outputs.length - 1);
                        if ((last === null || last === void 0 ? void 0 : last.output_type) === 'error') {
                            cellError = `${last.ename || 'Error'}: ${last.evalue || ''}`;
                        }
                        else {
                            output = ((_a = last === null || last === void 0 ? void 0 : last.data) === null || _a === void 0 ? void 0 : _a['text/plain']) || '';
                        }
                    }
                }
                catch (_) { }
                const input = document.createElement('textarea');
                input.placeholder = 'e.g. optimize query, fix bug, improve readability...';
                input.style.cssText = `width:100%;min-height:60px;background:${panelStyles_1.CC.raised};color:${panelStyles_1.CC.text};border:1px solid ${panelStyles_1.CC.border};border-radius:8px;padding:8px;font-size:12px;resize:vertical;font-family:inherit;box-sizing:border-box;`;
                const hint = document.createElement('div');
                hint.style.cssText = `font-size:11px;color:${panelStyles_1.CC.subtle};margin-top:4px;`;
                hint.textContent = 'Enter → Optimize    Shift+Enter → Optimize & Run';
                const body = new widgets_1.Widget();
                body.node.appendChild(input);
                body.node.appendChild(hint);
                // Build dialog manually for keyboard control
                let autoRun = false;
                const dialog = new apputils_1.Dialog({
                    title: 'Cell Optimization',
                    body,
                    buttons: [
                        apputils_1.Dialog.cancelButton(),
                        apputils_1.Dialog.okButton({ label: 'Optimize & Run' }),
                        apputils_1.Dialog.okButton({ label: 'Optimize' }),
                    ],
                });
                // After render, hijack the dialog's keyboard handling
                dialog.node.addEventListener('keydown', (e) => {
                    var _a;
                    if (e.key !== 'Enter' || e.isComposing)
                        return;
                    if (((_a = document.activeElement) === null || _a === void 0 ? void 0 : _a.tagName) === 'TEXTAREA') {
                        e.preventDefault();
                        e.stopPropagation();
                        autoRun = e.shiftKey;
                        const btns = dialog.node.querySelectorAll('.jp-Dialog-button');
                        const btn = e.shiftKey
                            ? btns[btns.length - 2]
                            : btns[btns.length - 1];
                        btn === null || btn === void 0 ? void 0 : btn.click();
                    }
                }, true);
                setTimeout(() => input.focus(), 10);
                const dlgResult = await dialog.launch();
                const clicked = dlgResult.button.label;
                if (clicked === 'Cancel')
                    return;
                const userRequest = input.value.trim() || 'improve this code';
                const autoExec = autoRun || clicked === 'Optimize & Run';
                const payloadJson = JSON.stringify({
                    cellId, code, output,
                    error: cellError,
                    cellType,
                    request: userRequest,
                    auto: autoExec,
                });
                panel._kernel.requestExecute({
                    code: `get_ipython().user_ns['_panel_input']('/cell-optimize ' + ${JSON.stringify(payloadJson)})`,
                    store_history: false,
                });
            },
        });
        // Unified "History" submenu on cell right-click
        _app.commands.addCommand('skillbot:cell-history', {
            label: 'Cell Snapshots',
            execute: async () => {
                const nb = tracker.currentWidget;
                if (!nb)
                    return;
                const cell = nb.content.activeCell;
                if (!cell)
                    return;
                const cellId = cell.model.id;
                if (!panel._kernel)
                    return;
                const nbPath = nb.context.path || nb.context.localPath || '';
                const future = panel._kernel.requestExecute({
                    code: `from jupyter.cell_snapshot import list_versions; import json; d={"versions":list_versions(${JSON.stringify(cellId)}, nb_path=${JSON.stringify(nbPath)}),"cell_id":${JSON.stringify(cellId)}}; print(json.dumps(d))`,
                    store_history: false,
                });
                let stdout = '';
                future.onIOPub = (msg) => {
                    var _a;
                    if (msg.header.msg_type === 'stream' && ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.name) === 'stdout')
                        stdout += msg.content.text;
                };
                future.done.then(() => {
                    try {
                        const text = stdout.trim();
                        const data = JSON.parse(text);
                        const versions = data.versions || [];
                        if (!versions.length) {
                            alert('No cell snapshots yet. Execute cells first.');
                            return;
                        }
                        _showCellSnapshotsDialog(cell, versions, panel);
                    }
                    catch (e) {
                        console.error(e);
                        alert('Failed to load cell snapshots.');
                    }
                });
            },
        });
        _app.commands.addCommand('skillbot:notebook-snapshots', {
            label: 'Notebook Snapshots',
            execute: async () => {
                const nb = tracker.currentWidget;
                if (!nb)
                    return;
                if (!panel._kernel)
                    return;
                const nbPath = nb.context.path || nb.context.localPath || '';
                const future = panel._kernel.requestExecute({
                    code: `from jupyter.notebook_snapshot import list_snapshots_for; from jupyter.magic import _get_magic; import json; inst=_get_magic(); d={"snapshots":list_snapshots_for(${JSON.stringify(nbPath)}),"cell_restored":inst._cell_restored if inst else False}; print(json.dumps(d))`,
                    store_history: false,
                });
                let stdout = '';
                future.onIOPub = (msg) => {
                    var _a;
                    if (msg.header.msg_type === 'stream' && ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.name) === 'stdout')
                        stdout += msg.content.text;
                };
                future.done.then(() => {
                    try {
                        const text = stdout.trim();
                        const data = JSON.parse(text);
                        const snapshots = data.snapshots || [];
                        if (!snapshots.length) {
                            alert('No notebook snapshots yet. Execute cells first.');
                            return;
                        }
                        _showSnapshotDialog(snapshots, panel, nb, data.cell_restored || false, nbPath);
                    }
                    catch (e) {
                        console.error(e);
                        alert('Failed to load snapshots.');
                    }
                });
            },
        });
        // Submenu on both .jp-Cell and .jp-Notebook
        const historyMenu = new widgets_2.Menu({ commands: _app.commands });
        historyMenu.title.label = 'Agent';
        historyMenu.addItem({ command: 'skillbot:cell-reference' });
        historyMenu.addItem({ command: 'skillbot:cell-optimize' });
        historyMenu.addItem({ type: 'separator' });
        historyMenu.addItem({ command: 'skillbot:cell-history' });
        historyMenu.addItem({ command: 'skillbot:notebook-snapshots' });
        _app.contextMenu.addItem({
            selector: '.jp-Notebook',
            type: 'submenu',
            submenu: historyMenu,
            rank: 50,
        });
        tracker.currentChanged.connect(() => register());
        setTimeout(register, 500);
        // When a notebook file is deleted from the file browser, purge its
        // conversation record so stale sessions don't linger in the switcher.
        try {
            const contents = (_a = _app.serviceManager) === null || _a === void 0 ? void 0 : _a.contents;
            (_b = contents === null || contents === void 0 ? void 0 : contents.fileChanged) === null || _b === void 0 ? void 0 : _b.connect((_sender, change) => {
                var _a;
                if ((change === null || change === void 0 ? void 0 : change.type) === 'delete') {
                    const p = ((_a = change.oldValue) === null || _a === void 0 ? void 0 : _a.path) || '';
                    if (p && /\.ipynb$/.test(p))
                        panel.onNotebookFileDeleted(p);
                }
            });
        }
        catch (e) {
            console.error('[panel] fileChanged wiring failed:', e);
        }
    },
};
