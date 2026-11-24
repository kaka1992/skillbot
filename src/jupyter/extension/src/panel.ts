import { Widget } from '@lumino/widgets';
import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';
import { showDialog, Dialog } from '@jupyterlab/apputils';
import { INotebookTracker, NotebookActions } from '@jupyterlab/notebook';
import { IRenderMimeRegistry, renderMarkdown } from '@jupyterlab/rendermime';
import { Menu } from '@lumino/widgets';
import { CC, STYLES } from './panelStyles';
import * as R from './panelRenderer';
import * as PC from './panelPlanConfirm';
import * as SS from './panelSessions';
import * as SK from './panelSkills';

const TARGET = 'skillbot:tui';
let _panelInstance: AgentPanel | null = null;

interface CellReference {
  cell_id: string;
  label: string;
  cell_type: string;
  code: string;
  output: string;
  error: string;
}

interface SteerTarget {
  url: string;
  run_id: string;
  control_token: string;
}

// ===========================================================================
// AgentPanel
// ===========================================================================

class AgentPanel extends Widget {
  private _root: ShadowRoot;
  private _outputEl: HTMLElement;
  private _inputEl: HTMLTextAreaElement;
  private _killRing: string = '';  // for Ctrl+Y yank
  private _lastKill: string = '';   // track consecutive kill type for accumulation
  private _charsPerLine: number = 80;  // computed from textarea width / monospace char width
  private _inputWrapper: HTMLElement;
  private _confirmWrapper: HTMLElement;
  private _statusEl: HTMLElement;
  private _topDotEl: HTMLElement | null = null;
  private _statusTimer: any = null;
  private _execStartTime: number = 0;
  private _statusIcon: string = '○';
  private _statusLabel: string = 'idle';
  private _tracker: INotebookTracker | null = null;
  _kernel: any = null;  // public — accessed by plugin commands
  private _comm: any = null;
  private _history: string[] = [];
  private _historyIdx: number = -1;
  private _historyDraft: string = '';  // saved original input when navigating history

  // spinner
  private _spinnerEl: HTMLElement | null = null;

  // info bar (mode switch messages)
  private _infoEl: HTMLElement;
  private _infoTimer: any = null;

  // mode (cc-haha style: Shift+Tab to cycle)
  private _mode: 'default' | 'plan' | 'auto' = 'default';

  // input marker (❯ / ⏸) — updated per mode
  private _markerEl: HTMLElement;

  // plan confirmation
  private _planConfirmActive = false;
  private _planConfirmOptionIdx: 0 | 1 | 2 = 0;
  private _planConfirmFeedbackMode = false;
  private _planCurrentSummary = '';

  // continue confirmation (plan/default mode loop)
  private _continueConfirmActive = false;
  private _continueOptionIdx: 0 | 1 = 0;
  private _continueSummary = '';

  // message block
  private _currentBlock: HTMLElement | null = null;
  private _streaming = false;
  private _responseStarted = false;
  private _textEl: HTMLElement | null = null;  // accumulated text element for streaming
  _thinkingEl: HTMLElement | null = null;      // accumulated thinking element
  private _thinkingCollapsed = true;            // Ctrl+T to toggle collapse
  _workflowState = 'IDLE';                      // backend-authoritative workflow projection
  private _workflowRevision = 0;
  private _steerTarget: SteerTarget | null = null;
  private _promptQueue: Array<{
    text: string;
    mode: 'default' | 'plan' | 'auto';
    cellReferences: CellReference[];
    notebookPath: string;
    kernelId: string;
  }> = [];
  private _cellReferences: CellReference[] = [];
  private _cellReferencesEl!: HTMLElement;
  private _cellCandidates: CellReference[] = [];
  private _dropdownKind: 'command' | 'cell' | null = null;
  private _skillsMode = false;                   // skills view active → input hidden
  private _actionBarEl!: HTMLElement;             // visible agent controls (stop / plan / clear / skills)

  // multi-session management (per-notebook conversation buffers + switcher)
  _currentPath = '';                             // notebook path bound to the shown conversation
  private _sessionBarEl!: HTMLElement;            // session switcher UI
  _sessionsCollapsed = false;                    // switcher collapsed state (persisted)
  _app: JupyterFrontEnd | null = null;           // app handle for docmanager:open / newUntitled
  private _markdownRendering = new WeakSet<HTMLElement>();

  constructor(private _rendermime: IRenderMimeRegistry) {
    super();
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

    // restore session switcher collapsed state
    try { this._sessionsCollapsed = localStorage.getItem(SS.COLLAPSE_KEY) === '1'; } catch (_) {}

    const style = document.createElement('style');
    style.textContent = STYLES;
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
      if (document.activeElement === this._inputEl) return;
      if (e.ctrlKey && !e.altKey) {
        switch (e.key) {
          case 't': e.preventDefault(); this._toggleThinkingCollapse(); break;
          case 'c': e.preventDefault(); this._kernel?.interrupt(); this._setStatus('⏏', 'interrupted'); break;
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
        this._skillListWrapper?.focus();
      }
    });
    this._outputEl.addEventListener('click', () => {
      // Don't steal focus if user was selecting text (drag, double-click, etc.)
      const sel = document.getSelection();
      if (sel && sel.type !== 'None' && sel.toString().length > 0) return;
      if (this._planConfirmActive) {
        this._confirmWrapper.focus();
      } else {
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

  private _onKeydown(e: KeyboardEvent): void {
    // continue confirm: Yes/No selection (plan-style overlay)
    if (this._continueConfirmActive) {
      if (e.key === 'ArrowUp' || (e.key === 'Tab' && e.shiftKey)) {
        e.preventDefault(); e.stopPropagation();
        this._continueOptionIdx = (this._continueOptionIdx === 0 ? 1 : 0);
        this._renderContinueOptions();
        return;
      }
      if (e.key === 'ArrowDown' || e.key === 'Tab') {
        e.preventDefault(); e.stopPropagation();
        this._continueOptionIdx = (this._continueOptionIdx === 0 ? 1 : 0);
        this._renderContinueOptions();
        return;
      }
      if (e.key === 'Enter') {
        e.preventDefault(); e.stopPropagation();
        this._submitContinue();
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault(); e.stopPropagation();
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
          e.preventDefault(); e.stopPropagation();
          this._submitPlanConfirm();
          return;
        }
        if (e.key === 'Escape') {
          e.preventDefault(); e.stopPropagation();
          this._planConfirmFeedbackMode = false;
          this._renderConfirmOptions();
          this._confirmWrapper.focus();
          return;
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
          e.preventDefault(); e.stopPropagation();
          this._cancelPlanConfirm();
          return;
        }
        // Shift+Enter, Arrow keys, etc. pass through to textarea natively
        return;
      }

      // Option selection mode
      switch (e.key) {
        case 'ArrowUp':
          e.preventDefault(); e.stopPropagation();
          this._planConfirmOptionIdx = (this._planConfirmOptionIdx === 0 ? 2 : this._planConfirmOptionIdx - 1) as 0|1|2;
          this._renderConfirmOptions();
          this._confirmWrapper.focus();
          return;
        case 'ArrowDown':
        case 'Tab':
          e.preventDefault(); e.stopPropagation();
          this._planConfirmOptionIdx = ((this._planConfirmOptionIdx + 1) % 3) as 0|1|2;
          this._renderConfirmOptions();
          this._confirmWrapper.focus();
          return;
        case 'Enter':
          e.preventDefault(); e.stopPropagation();
          this._submitPlanConfirm();
          return;
        case 'Escape':
          e.preventDefault(); e.stopPropagation();
          this._cancelPlanConfirm();
          return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        // Ctrl+L during confirm: clear panel + cancel confirm
        e.preventDefault(); e.stopPropagation();
        this._cancelPlanConfirm();
        this._clear();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
        e.preventDefault(); e.stopPropagation();
        this._cancelPlanConfirm();
        return;
      }
      e.preventDefault();
      return;
    }

    const ctrl = e.ctrlKey;  // Control only — Cmd/Meta passes through for OS shortcuts
    const el = this._inputEl;
    const ss = el.selectionStart;
    const se = el.selectionEnd;
    const v = el.value;

    // Helper: accumulate kills (consecutive same-type kills append, different type overwrites)
    const doKill = (type: string, text: string) => {
      if (this._lastKill === type && this._killRing) {
        this._killRing += text;
      } else {
        this._killRing = text;
      }
      this._lastKill = type;
    };

    // ---- Emacs-style Ctrl shortcuts ----
    if (ctrl && !e.altKey) {
      switch (e.key) {
        case 'a': e.preventDefault(); el.selectionStart = el.selectionEnd = 0; return;
        case 'b': e.preventDefault(); el.selectionStart = el.selectionEnd = Math.max(0, ss - 1); return;
        case 'e': e.preventDefault(); el.selectionStart = el.selectionEnd = v.length; return;
        case 'f': e.preventDefault(); el.selectionStart = el.selectionEnd = Math.min(v.length, ss + 1); return;
        case 'h': e.preventDefault();
          if (ss !== se) { el.value = v.slice(0, ss) + v.slice(se); el.selectionStart = el.selectionEnd = ss; }
          else if (ss > 0) { el.value = v.slice(0, ss - 1) + v.slice(ss); el.selectionStart = el.selectionEnd = ss - 1; }
          this._resizeInput(); return;
        case 'n': if (this._navigateHistory(1)) { e.preventDefault(); } return;
        case 'p': if (this._navigateHistory(-1)) { e.preventDefault(); } return;
        case 'k': {
          e.preventDefault();
          if (ss !== se) { el.value = v.slice(0, ss) + v.slice(se); el.selectionStart = el.selectionEnd = ss; }
          const cur = el.selectionStart;
          const lineEnd = el.value.indexOf('\n', cur);
          if (lineEnd !== -1) {
            // Kill to end of current line (including the newline)
            doKill('k', el.value.slice(cur, lineEnd + 1));
            el.value = el.value.slice(0, cur) + el.value.slice(lineEnd + 1);
          } else if (cur < el.value.length) {
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
          if (ss !== se) { el.value = v.slice(0, ss) + v.slice(se); el.selectionStart = el.selectionEnd = ss; }
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
          if (ss !== se) { el.value = v.slice(0, ss) + v.slice(se); el.selectionStart = el.selectionEnd = ss; }
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
          } else if (v.length === 0) {
            el.value = ''; this._historyIdx = -1; this._historyDraft = ''; this._resizeInput();
          } else if (ss < v.length) {
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
            if (ss !== se) { el.value = v.slice(0, ss) + v.slice(se); el.selectionStart = el.selectionEnd = ss; }
            const cur = el.selectionStart;
            el.value = el.value.slice(0, cur) + this._killRing + el.value.slice(el.selectionEnd);
            el.selectionStart = el.selectionEnd = cur + this._killRing.length;
            this._resizeInput();
          }
          return;
        }
        case 'c': {
          e.preventDefault();
          if (ss !== se) return;  // has selection → let browser handle copy (Cmd+C)
          if (v.length > 0) {
            // First Ctrl+C: clear input
            el.value = '';
            this._historyIdx = -1;
            this._historyDraft = '';
            this._killRing = ''; this._lastKill = '';
            this._resizeInput();
          } else {
            // Second Ctrl+C (or first on empty input): interrupt agent
            this._kernel?.interrupt();
            this._setStatus('⏏', 'interrupted');
          }
          return;
        }
        case 'l': e.preventDefault(); this._clear(); return;
        case 't': e.preventDefault(); this._toggleThinkingCollapse(); return;
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
      this._killRing = ''; this._lastKill = '';
      if (
        this._commandDropdown.style.display !== 'none'
        && !e.shiftKey
        && !e.metaKey
        && !e.altKey
      ) {
        e.preventDefault();
        this._commitCommand();
        return;
      }
      if (e.shiftKey || e.metaKey || e.altKey) {
        e.preventDefault();
        // Clear selection before inserting newline
        if (ss !== se) { el.value = v.slice(0, ss) + v.slice(se); el.selectionStart = el.selectionEnd = ss; }
        const cur = el.selectionStart;
        el.value = el.value.slice(0, cur) + '\n' + el.value.slice(el.selectionEnd);
        el.selectionStart = el.selectionEnd = cur + 1;
        this._resizeInput();
      } else {
        e.preventDefault();
        this._commandDropdown.style.display = 'none';
        this._sendPrompt();
      }
      return;
    }

    // ---- Command dropdown: arrows to select, Tab/Enter to commit, Esc to close ----
    if (this._commandDropdown.style.display !== 'none') {
      if (e.key === 'ArrowDown') { e.preventDefault(); this._selectCommand(1); return; }
      if (e.key === 'ArrowUp')   { e.preventDefault(); this._selectCommand(-1); return; }
      if (e.key === 'Enter')     { e.preventDefault(); this._commitCommand(); return; }
      if (e.key === 'Escape')    { e.preventDefault(); this._commandDropdown.style.display = 'none'; this._commandIdx = -1; return; }
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
      this._killRing = ''; this._lastKill = '';
      this._resizeInput();
      return;
    }

    // ---- Tab ----
    if (e.key === 'Tab') {
      this._killRing = ''; this._lastKill = '';
      e.preventDefault();
      if (e.shiftKey) {
        this._cycleMode();
      } else {
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
      this._killRing = ''; this._lastKill = '';
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

  private _prevWordPos(text: string, pos: number): number {
    // Skip trailing whitespace
    let i = pos - 1;
    while (i >= 0 && /\s/.test(text[i])) i--;
    // Skip the word
    while (i >= 0 && !/\s/.test(text[i])) i--;
    return i + 1;
  }

  private _nextWordPos(text: string, pos: number): number {
    let i = pos;
    // Skip current word
    while (i < text.length && !/\s/.test(text[i])) i++;
    // Skip whitespace
    while (i < text.length && /\s/.test(text[i])) i++;
    return i;
  }

  private _resizeInput(): void {
    const el = this._inputEl;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    this._recalcCharsPerLine();
  }

  private _recalcCharsPerLine(): void {
    const el = this._inputEl;
    if (el.clientWidth <= 0) return;
    try {
      const style = getComputedStyle(el);
      const padL = parseFloat(style.paddingLeft) || 0;
      const padR = parseFloat(style.paddingRight) || 0;
      const cw = el.clientWidth - padL - padR - 2; // -2 for border
      // Measure monospace char width using canvas
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d')!;
      ctx.font = style.font;
      const charW = ctx.measureText('W').width;
      this._charsPerLine = Math.max(1, Math.floor(cw / charW));
    } catch (_) {
      // Fallback: ~7.8px per char at 13px for SF Mono
      this._charsPerLine = Math.max(1, Math.floor((el.clientWidth - 18) / 7.8));
    }
  }

  // Visual line number at text position (accounts for both \n and word-wrap)
  private _visualLineAt(text: string, pos: number): number {
    let line = 0, col = 0;
    const limit = Math.min(pos, text.length);
    for (let i = 0; i < limit; i++) {
      if (text[i] === '\n') { line++; col = 0; }
      else if (++col >= this._charsPerLine) { line++; col = 0; }
    }
    return line;
  }

  private _isOnFirstVisualLine(text: string, pos: number): boolean {
    return this._visualLineAt(text, pos) === 0;
  }

  private _isOnLastVisualLine(text: string, pos: number): boolean {
    const cursorLine = this._visualLineAt(text, pos);
    const lastLine = this._visualLineAt(text, text.length);
    return cursorLine >= lastLine;
  }

  private _navigateHistory(direction: -1 | 1): boolean {
    const v = this._inputEl.value;
    // Save draft on first entry into history
    if (this._historyIdx === -1 && v) {
      this._historyDraft = v;
    }
    this._killRing = ''; this._lastKill = '';
    const newIdx = this._historyIdx - direction;  // direction: -1 = older (↑), 1 = newer (↓)
    if (newIdx >= -1 && newIdx < this._history.length) {
      this._historyIdx = newIdx;
      if (this._historyIdx === -1) {
        this._inputEl.value = this._historyDraft;
        this._historyDraft = '';
      } else {
        this._inputEl.value = this._history[this._history.length - 1 - this._historyIdx];
      }
      // Place cursor at start so next ArrowUp immediately triggers more history
      this._inputEl.selectionStart = this._inputEl.selectionEnd = 0;
      this._resizeInput();
      return true;
    }
    return false;
  }

  private _updateCommandDropdown(): void {
    const val = this._inputEl.value;
    const beforeCursor = val.slice(0, this._inputEl.selectionStart);
    const mention = beforeCursor.match(/(^|\s)@([^\s@]*)$/);
    if (mention) {
      const query = mention[2].toLowerCase();
      this._cellCandidates = this._collectCellReferences().filter(ref =>
        `${ref.label} ${ref.code}`.toLowerCase().includes(query),
      );
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
    if (this._commandIdx < 0 || this._commandIdx >= matches.length) this._commandIdx = 0;
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

  private _renderCellCandidates(): void {
    if (this._cellCandidates.length === 0) {
      this._commandDropdown.style.display = 'none';
      this._commandIdx = -1;
      return;
    }
    if (
      this._commandIdx < 0
      || this._commandIdx >= this._cellCandidates.length
    ) {
      this._commandIdx = 0;
    }
    this._commandDropdown.innerHTML = '';
    this._cellCandidates.forEach((ref, index) => {
      const item = document.createElement('div');
      item.className = index === this._commandIdx
        ? 'skillbot-command-item active'
        : 'skillbot-command-item';
      const firstLine = ref.code.split('\n').find(line => line.trim())?.trim() || '(empty)';
      item.textContent = `${ref.label}  ${firstLine.slice(0, 80)}`;
      item.title = firstLine;
      item.addEventListener('click', () => this._commitCellReference(index));
      this._commandDropdown.appendChild(item);
    });
    this._commandDropdown.style.display = 'block';
  }

  private _selectCommand(delta: number): void {
    if (this._commandDropdown.style.display === 'none') return;
    if (this._dropdownKind === 'cell') {
      if (this._cellCandidates.length === 0) return;
      this._commandIdx = (
        this._commandIdx + delta + this._cellCandidates.length
      ) % this._cellCandidates.length;
      this._renderCellCandidates();
      return;
    }
    const val = this._inputEl.value;
    const matches = this._commands.filter(c => c.startsWith(val) && c !== val);
    if (matches.length === 0) return;
    this._commandIdx = (this._commandIdx + delta + matches.length) % matches.length;
    this._updateCommandDropdown();
  }

  private _commitCommand(): void {
    if (this._commandDropdown.style.display === 'none') return;
    if (this._dropdownKind === 'cell') {
      this._commitCellReference(this._commandIdx >= 0 ? this._commandIdx : 0);
      return;
    }
    const val = this._inputEl.value;
    const matches = this._commands.filter(c => c.startsWith(val) && c !== val);
    if (matches.length === 0) return;
    const idx = this._commandIdx >= 0 ? this._commandIdx : 0;
    if (idx < matches.length) {
      this._inputEl.value = matches[idx];
      this._inputEl.selectionStart = this._inputEl.selectionEnd = matches[idx].length;
      this._commandDropdown.style.display = 'none';
      this._commandIdx = -1;
      this._resizeInput();
    }
  }

  private _collectCellReferences(): CellReference[] {
    const notebook = this._tracker?.currentWidget;
    if (!notebook?.content) return [];
    return notebook.content.widgets.map((cell: any, index: number) => {
      const code = String(cell.model.sharedModel.getSource?.() || '');
      let output = '';
      let error = '';
      try {
        const outputs = cell.model.outputs;
        const serialized = outputs?.toJSON?.() || [];
        for (const item of serialized) {
          if (item.output_type === 'error') {
            const traceback = Array.isArray(item.traceback)
              ? item.traceback.join('\n')
              : '';
            error = traceback || `${item.ename || 'Error'}: ${item.evalue || ''}`;
          } else if (item.output_type === 'stream') {
            output += Array.isArray(item.text) ? item.text.join('') : String(item.text || '');
          } else {
            const plain = item.data?.['text/plain'];
            if (plain) output += Array.isArray(plain) ? plain.join('') : String(plain);
          }
        }
      } catch (_) {}
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

  private _commitCellReference(index: number): void {
    const ref = this._cellCandidates[index];
    if (!ref) return;
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

  private _addCellReference(ref: CellReference): void {
    const existing = this._cellReferences.findIndex(
      item => item.cell_id === ref.cell_id,
    );
    if (existing >= 0) this._cellReferences.splice(existing, 1);
    this._cellReferences.push(ref);
    this._renderCellReferences();
  }

  private _renderCellReferences(): void {
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
        this._cellReferences = this._cellReferences.filter(
          item => item.cell_id !== ref.cell_id,
        );
        this._renderCellReferences();
      });
      chip.append(label, remove);
      this._cellReferencesEl.appendChild(chip);
    });
  }

  addActiveCellReference(): void {
    const notebook = this._tracker?.currentWidget;
    const active = notebook?.content.activeCell;
    if (!notebook || !active) return;
    const index = notebook.content.widgets.indexOf(active);
    const ref = this._collectCellReferences()[index];
    if (!ref) return;
    this._addCellReference(ref);
    this._app?.shell.activateById(this.id);
    this._inputEl.focus();
  }

  private _openCellPicker(): void {
    const prefix = this._inputEl.value && !/\s$/.test(this._inputEl.value)
      ? ' @'
      : '@';
    const cursor = this._inputEl.selectionStart;
    this._inputEl.value = (
      this._inputEl.value.slice(0, cursor)
      + prefix
      + this._inputEl.value.slice(this._inputEl.selectionEnd)
    );
    const nextCursor = cursor + prefix.length;
    this._inputEl.selectionStart = this._inputEl.selectionEnd = nextCursor;
    this._inputEl.focus();
    this._updateCommandDropdown();
  }

  private _tabComplete(): void {
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

  // ---- mode cycling (cc-haha: Shift+Tab) ----

  private static MODE_ORDER: Array<'default' | 'plan' | 'auto'> = ['default', 'plan', 'auto'];
  private static MODE_COLOR: Record<string, string> = {
    default: '',
    plan:    'rgb(0,102,102)',   // cyan, cc-haha planMode
    auto:    'rgb(135,0,255)',   // purple, cc-haha autoAccept
  };
  private static MODE_SYMBOL: Record<string, string> = {
    default: '',
    plan:    '⏸',
    auto:    '⏵⏵',
  };

  private static MODE_INFO: Record<string, string[]> = {
    plan:    ['Plan mode — I\'ll explore first, then design a plan for your approval',
              'Plan mode — describe your task, I\'ll research & propose an approach',
              'Plan mode — no code is written until you approve the plan'],
    auto:    ['Auto mode — cells are generated and executed automatically',
              'Auto mode — I\'ll write code and run it without asking'],
    default: ['Default mode — cells are generated but need manual execution',
              'Default mode — I decide whether to plan first or write code directly'],
  };

  private _cycleMode(): void {
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
  private _updateModeInfo(): void {
    if (this._infoTimer) clearTimeout(this._infoTimer);
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
    } else {
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

  private static DISPLAY_COMMANDS = ['/clear', '/mode', '/skills', '/config', '/continue', '/stop'];

  private _isDisplayCommand(text: string): boolean {
    return AgentPanel.DISPLAY_COMMANDS.some(c => text === c || text.startsWith(c + ' '));
  }

  private get _hasActiveWorkflow(): boolean {
    return this._workflowState !== 'IDLE';
  }

  private get _canInterrupt(): boolean {
    return [
      'AGENT_STREAMING',
      'CELL_DISPATCHING',
      'CELL_EXECUTING',
      'AUTO_FIXING',
    ].includes(this._workflowState);
  }

  private get _canSteer(): boolean {
    return ['AGENT_STREAMING', 'AUTO_FIXING'].includes(this._workflowState);
  }

  private _sendPrompt(): void {
    if (this._planConfirmActive) return;
    const text = this._inputEl.value.trim();
    if (!text) return;
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
      const notebookPath = this._currentPath;
      const kernelId = this._kernel?.id;
      if (!notebookPath || !kernelId) {
        this._renderResponseText('[cannot queue without a notebook and kernel]');
        return;
      }
      this._promptQueue.push({
        text,
        mode: this._mode,
        cellReferences,
        notebookPath,
        kernelId,
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
    } else {
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
      future.onIOPub = (msg: any) => {
        if (msg.header.msg_type === 'stream' && msg.content?.name === 'stdout') {
          if (firstStdout) {
            this._renderResponseText(this._stripAnsi(msg.content.text));
            firstStdout = false;
          } else {
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

  private async _sendSteer(text: string, refs: CellReference[]): Promise<void> {
    const target = this._steerTarget;
    if (!target) return;

    let message = text;
    if (refs.length) {
      message += '\n\n[Referenced Notebook Cells]\n' + refs.map(ref =>
        JSON.stringify({
          cell_id: ref.cell_id,
          label: ref.label,
          cell_type: ref.cell_type,
          code: ref.code,
          output: ref.output,
          error: ref.error,
        })
      ).join('\n');
    }

    this._renderPrompt(text, refs);
    this._textEl = null;
    this._thinkingEl = null;
    const messageId = globalThis.crypto?.randomUUID?.()
      || `steer-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    try {
      const url = new URL(target.url);
      if (
        url.protocol !== 'http:'
        || url.hostname !== '127.0.0.1'
        || url.port !== '9000'
      ) {
        throw new Error('invalid steering endpoint');
      }
      const response = await fetch(url.toString(), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
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
    } catch (error) {
      this._appendTextChunk(`\nDirection not delivered: ${String(error)}\n`);
    }
  }

  // ---- block management ---------------------------------------------------

  private _startBlock(): void {
    this._currentBlock = document.createElement('div');
    this._currentBlock.className = 'skillbot-msg-block';
    this._outputEl.appendChild(this._currentBlock);
    this._streaming = true;
    this._responseStarted = false;
    this._textEl = null;
    this._thinkingEl = null;
  }

  private _appendToBlock(el: HTMLElement): void {
    const target = this._currentBlock || this._outputEl;
    target.appendChild(el);
    this._scrollBottom();
  }

  // ---- renderers ----------------------------------------------------------

  private _ensureResponsePrefix(): void { R.ensureResponsePrefix(this); }
  private _renderPrompt(text: string, refs: CellReference[] = []): void {
    R.renderPrompt(this, text, refs);
  }
  private _renderResponseText(content: string): void { R.renderResponseText(this, content); }
  private _appendTextChunk(content: string): void { R.appendTextChunk(this, content); }
  private _renderTool(name: string): void { R.renderTool(this, name); }
  private _renderThinking(content: string): void { R.renderThinking(this, content); }
  private _renderCodeBlock(l: string, c: string): void { R.renderCodeBlock(this, l, c); }
  private _renderPlanBlock(text: string): void { R.renderPlanBlock(this, text); }
  private _renderResult(summary: string): void { R.renderResult(this, summary); }

  // ---- skill rendering ----

  private _skillRows: HTMLElement[] = [];
  private _skillSelectedIdx: number = 0;
  private _skillListWrapper: HTMLElement | null = null;
  private _skillData: Array<{name: string, description: string, enabled: boolean, body: string}> = [];
  private _expandedIdx: number = -1;   // -1=list, >=0=info view
  private _fullBodyIdx: number = -1;   // -1=not in full body, >=0=full body view
  private _installMode = false;        // showing install path input
  private _installError = '';          // error message from last install
  private _configPending = false;      // waiting for config confirm (y/n)
  private _commandDropdown: HTMLElement;  // slash command autocomplete
  private _commands: string[];
  private _commandIdx: number = -1;

  private _enterSkillsMode(): void { SK.enterSkillsMode(this); }
  private _exitSkillsMode(): void { SK.exitSkillsMode(this); }
  private _renderSkillList(skills: Array<{name: string, description: string, enabled: boolean, body?: string}>): void { SK.renderSkillList(this, skills); }
  private _onSkillKeydown(e: KeyboardEvent): void { SK.onSkillKeydown(this, e); }
  private _refreshSkillRows(): void { SK.refreshSkillRows(this); }
  private _renderSkillInfo(skill: {name: string, description: string, enabled: boolean, body: string, path: string}): void { SK.renderSkillInfo(this, skill); }

  // ---- thinking collapse (Ctrl+T) ----

  private _toggleThinkingCollapse(): void {
    this._thinkingCollapsed = !this._thinkingCollapsed;
    this._applyThinkingCollapse();
    const status = this._thinkingCollapsed ? 'collapsed' : 'expanded';
    this._infoEl.innerHTML = `<span style="color:rgb(0,180,180)">thinking ${status} · ctrl+t to toggle</span>`;
    if (this._infoTimer) clearTimeout(this._infoTimer);
    this._infoTimer = setTimeout(() => { this._infoEl.innerHTML = ''; }, 4000);
  }

  private _applyThinkingCollapse(): void {
    // Use live _thinkingEl during streaming, DOM search for Ctrl+T toggle
    const els = (this._thinkingEl && this._thinkingEl.parentElement)
      ? [this._thinkingEl]
      : Array.from(this._outputEl.querySelectorAll('.skillbot-thinking-line') as NodeListOf<HTMLElement>);
    els.forEach((el: HTMLElement) => {
      if (this._thinkingCollapsed) {
        const currentFull = el.getAttribute('data-full') || el.textContent || '';
        el.setAttribute('data-full', currentFull);
        const collapsed = '∴ Thinking…';
        if (el.textContent !== collapsed) el.textContent = collapsed;
        el.style.cursor = 'pointer';
        el.title = 'ctrl+t to expand';
      } else {
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

  _clear(): void {
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
    this._closeConfirm();  // ensure confirm UI is dismissed
    this._saveState();
    this._inputEl.value = '';
    this._historyIdx = -1;
    this._historyDraft = '';
    this._resizeInput();
  }

  private _dequeueNext(): void {
    if (this._promptQueue.length === 0) {
      this._updateStatusDisplay();
      return;
    }
    const next = this._promptQueue.shift()!;
    if (next.notebookPath !== this._currentPath || next.kernelId !== this._kernel?.id) {
      this._discardQueuedPrompts(1);
      return;
    }
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

  private _discardQueuedPrompts(alreadyRemoved = 0): void {
    const count = this._promptQueue.length + alreadyRemoved;
    this._promptQueue = [];
    if (!count) return;
    this._showQueueDiscard(count);
    this._updateStatusDisplay();
  }

  private _showQueueDiscard(count: number): void {
    if (!count) return;
    if (this._infoTimer) clearTimeout(this._infoTimer);
    this._infoEl.textContent = `${count} queued prompt(s) discarded after notebook or kernel change.`;
  }

  // ---- persistence (localStorage) ----

  // ---- session persistence + switcher (see panelSessions.ts) --------------
  private _storageKey(path?: string): string { return SS.storageKey(this, path); }
  private _saveState(): void { SS.saveState(this); }
  private _restoreState(): void { SS.restoreState(this); }
  private _loadBuffer(path: string): void { SS.loadBuffer(this, path); }
  private _applyBuffer(raw: string): void { SS.applyBuffer(this, raw); }
  private _loadRegistry(): Record<string, string> { return SS.loadRegistry(this); }
  private _saveRegistry(reg: Record<string, string>): void { SS.saveRegistry(this, reg); }
  private _registerSession(path: string): void { SS.registerSession(this, path); }
  private _renderSessionBar(): void { SS.renderSessionBar(this); }

  /** Bind the JupyterLab app so the switcher can open / create notebooks. */
  setApp(app: JupyterFrontEnd): void { this._app = app; }

  /**
   * Mark a notebook path as the active conversation. Registers it in the
   * switcher and, if it differs from the currently shown one, saves the old
   * buffer and loads the target buffer. Returns true if the path changed.
   */
  setActivePath(path: string, kernel: any = this._kernel): boolean {
    this._registerSession(path);
    if (path === this._currentPath) {
      if (!kernel && this._kernel) this.resetComm();
      if (kernel) this.connectKernel(kernel);
      return false;
    }
    if (this._currentPath) this._saveState();  // persist buffer we're leaving
    const discarded = this._promptQueue.length;
    this._promptQueue = [];
    this._currentPath = path;
    if (!kernel && this._kernel) this.resetComm();
    if (kernel) this.connectKernel(kernel);
    this._loadBuffer(path);
    this._renderSessionBar();
    this._showQueueDiscard(discarded);
    this._updateStatusDisplay();
    return true;
  }

  /** Tell the backend the active notebook changed so it resets agent memory. */
  notifyNotebookSwitch(path: string): void {
    if (!this._kernel) return;
    try {
      this._kernel.requestExecute({
        code: `get_ipython().user_ns['_panel_switch_notebook'](${JSON.stringify(path)})`,
        store_history: false,
      });
    } catch (_) {}
  }

  /** Public: called by the plugin when a notebook file is deleted from disk. */
  onNotebookFileDeleted(path: string): void { SS.onNotebookFileDeleted(this, path); }

  // ---- spinner -------------------------------------------------------------

  private _startSpinner(): void {
    if (this._spinnerEl) return;
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

  private _stopSpinner(): void {
    if (this._spinnerEl) {
      const wrapper = this._spinnerEl.parentElement;
      if (wrapper) wrapper.remove();
      this._spinnerEl = null;
    }
  }

  // ---- status bar ----------------------------------------------------------

  private _setStatus(icon: string, label: string): void {
    this._statusIcon = icon;
    this._statusLabel = label;
    // Start timer for running states, stop for idle/done
    if (icon === '…') {
      if (!this._statusTimer) {
        this._execStartTime = Date.now();
        this._statusTimer = setInterval(() => this._updateStatusDisplay(), 1000);
      }
    } else {
      this._stopStatusTimer();
    }
    this._updateStatusDisplay();
  }

  private _stopStatusTimer(): void {
    if (this._statusTimer) {
      clearInterval(this._statusTimer);
      this._statusTimer = null;
    }
  }

  private _updateStatusDisplay(): void {
    const icon = this._statusIcon;
    const label = this._statusLabel;
    const q = this._promptQueue.length > 0
      ? ` <span style="color:rgb(215,119,87)">queued:${this._promptQueue.length}</span>`
      : '';
    if (icon === '…' && this._execStartTime > 0) {
      const elapsed = Math.floor((Date.now() - this._execStartTime) / 1000);
      this._statusEl.innerHTML = `<span>${icon} ${label} (${elapsed}s)${q}</span><span>skillbot</span>`;
    } else {
      this._statusEl.innerHTML = `<span>${icon} ${label}${q}</span><span>skillbot</span>`;
    }
    this._updateTopDot(icon);
    this._syncActionBar();
  }

  /** Map the current status icon to the top-bar dot state modifier. */
  private _updateTopDot(icon: string): void {
    if (!this._topDotEl) return;
    const state =
      icon === '…' ? 'thinking' :
      icon === '✓' ? 'done' :
      icon === '⏏' ? 'interrupted' :
      icon === '⏸' ? 'plan' :
      'idle';
    this._topDotEl.className = `skillbot-status-dot skillbot-status-dot--${state}`;
  }

  // ---- agent action bar ---------------------------------------------------

  /** Run a slash command from a button without disturbing the user's draft/history. */
  private _dispatchCommand(cmd: string): void {
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
      if (draft) this._inputEl.value = draft;
      this._cellReferences = references;
      this._renderCellReferences();
      if (!this._skillsMode) this._resizeInput();
    }
  }

  /** Interrupt the running kernel immediately (same as Ctrl+C twice). */
  private _interruptAgent(): void {
    this._kernel?.interrupt();
    this._setStatus('⏏', 'interrupted');
    this._stopSpinner();
    this._workflowState = 'INTERRUPTING';
    this._promptQueue = [];
    this._updateStatusDisplay();
  }

  /** Plan button: toggle between plan and default (same sync path as Shift+Tab). */
  private _togglePlanMode(): void {
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
  private _renderActionBar(): void {
    if (!this._actionBarEl) return;
    this._actionBarEl.innerHTML = '';

    const mk = (label: string, title: string, cls: string, on: () => void): HTMLElement => {
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
    if (!this._canInterrupt) stop.classList.add('disabled');
    this._actionBarEl.appendChild(stop);

    // Plan is a toggle: switch into plan mode, or back to default if active.
    const plan = mk('⏸ Plan', 'Plan 模式开关 (Shift+Tab)', 'skillbot-action-plan', () => this._togglePlanMode());
    if (this._mode === 'plan') plan.classList.add('active');
    this._actionBarEl.appendChild(plan);

    this._actionBarEl.appendChild(mk('🗑 Clear', '清空当前会话对话', '', () => this._dispatchCommand('/clear')));

    this._actionBarEl.appendChild(
      mk('@', '引用 Notebook 单元格', 'skillbot-action-reference', () => {
        this._openCellPicker();
      }),
    );

    // Skills is a toggle: open the manager, or close it if already open.
    const skills = mk('≣ Skills', '管理技能 (/skills)', 'skillbot-action-skills', () => {
      if (this._skillsMode) this._exitSkillsMode();
      else this._dispatchCommand('/skills');
    });
    if (this._skillsMode) skills.classList.add('active');
    this._actionBarEl.appendChild(skills);
  }

  /** Keep the Stop button's enabled/prominent state in sync with busy. */
  private _syncActionBar(): void {
    const stop = this._actionBarEl?.querySelector('.skillbot-action-stop');
    if (!stop) return;
    if (this._canInterrupt) stop.classList.remove('disabled');
    else stop.classList.add('disabled');
  }

  private _applyWorkflowState(data: any): void {
    const revision = Number(data.revision || 0);
    if (revision && revision <= this._workflowRevision) return;
    this._workflowRevision = revision;
    this._workflowState = String(data.state || 'IDLE');

    const display: Record<string, [string, string]> = {
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
    } else if (
      this._workflowState === 'PLAN_REVIEW'
      || this._workflowState === 'WAITING_CONFIRM'
    ) {
      this._stopSpinner();
    }
  }

  // ---- plan confirmation (delegates to panelPlanConfirm) ------------------

  private _renderPlanConfirm(s: string): void { PC.renderPlanConfirm(this, s); }
  private _getConfirmHint(): string { return PC.getConfirmHint(this); }
  private _renderConfirmOptions(): void { PC.renderConfirmOptions(this); }
  private _closeConfirm(): void { PC.closeConfirm(this); }
  private _sendConfirmToBackend(c: string): void { PC.sendConfirmToBackend(this, c); }
  private _submitPlanConfirm(): void { PC.submitPlanConfirm(this); }
  private _cancelPlanConfirm(): void { PC.cancelPlanConfirm(this); }

  // ---- continue confirmation (plan-style overlay) --------------------------

  private _renderContinueButtons(summary: string): void {
    this._continueConfirmActive = true;
    this._continueOptionIdx = 0;
    this._continueSummary = summary;
    this._renderContinueOptions();
    this._inputWrapper.style.display = 'none';
    this._confirmWrapper.style.display = 'flex';
    this._confirmWrapper.focus();
  }

  private _renderContinueOptions(): void {
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

  private _submitContinue(): void {
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

  private _scrollBottom(): void {
    this._outputEl.scrollTop = this._outputEl.scrollHeight;
  }

  private _stripAnsi(s: string): string {
    return s.replace(/\x1b\[[0-9;]*m/g, '');
  }

  _renderMarkdown(host: HTMLElement, source: string): void {
    host.dataset.markdown = source;
    if (this._markdownRendering.has(host)) return;
    this._markdownRendering.add(host);

    const renderLatest = async (): Promise<void> => {
      const current = host.dataset.markdown || '';
      try {
        await renderMarkdown({
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
      } catch (_) {
        host.textContent = current;
      }
      if (host.dataset.markdown !== current && host.isConnected) {
        await renderLatest();
      } else {
        this._markdownRendering.delete(host);
      }
    };
    void renderLatest();
  }

  private _ansiToHtml(s: string): string {
    // escape raw text first so ANSI conversion can't inject markup
    s = this._esc(s);
    return s.replace(/\x1b\[32m/g, '<span style="color:#4ade80">')
            .replace(/\x1b\[31m/g, '<span style="color:#f87171">')
            .replace(/\x1b\[90m/g, '<span style="color:#999">')
            .replace(/\x1b\[0m/g, '</span>')
            .replace(/\x1b\[[0-9;]*m/g, '');
  }

  private _esc(s: string): string {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  setTracker(tracker: INotebookTracker): void {
    this._tracker = tracker;
  }

  // ---- kernel / comm -------------------------------------------------------

  resetComm(): void {
    this._discardQueuedPrompts();
    if (this._comm) {
      try { this._comm.close(); } catch (_) {}
      this._comm = null;
    }
    this._kernel = null;
    this._workflowState = 'IDLE';
    this._workflowRevision = 0;
    this._steerTarget = null;
    this._stopStatusTimer();
  }

  connectKernel(kernel: any): void {
    if (this._kernel && this._kernel !== kernel) {
      this.resetComm();
    }
    this._kernel = kernel;

    // Notify kernel of active notebook path for snapshot file isolation.
    // Must happen BEFORE `if (this._comm) return` so it fires on every
    // notebook switch and lazy kernel start (via onKernelChanged).
    const nb = this._tracker?.currentWidget;
    const nbPath = nb?.context?.path || '';
    if (nbPath) {
      kernel.requestExecute({
        code: `from jupyter.magic import _set_active_notebook_path; _set_active_notebook_path(${JSON.stringify(nbPath)})`,
        store_history: false,
      });
    }

    if (this._comm) return;

    try {
      this._comm = kernel.createComm(TARGET);
      this._comm.onMsg = (m: any) => {
        const d = m.content?.data || {};
        switch (d.action) {
          case 'text':
            if (this._skillsMode) {
              const txt = this._ansiToHtml(d.content || '');
              if (txt.includes('✗')) this._installError = txt.trim();
            } else {
              const txt = this._stripAnsi(d.content || '');
              if (this._responseStarted) {
                this._appendTextChunk(txt);
              } else {
                this._renderResponseText(txt);
              }
              // Backend sent config confirmation → enable y/n
              if (txt.includes('Press y to apply')) {
                this._configPending = true;
                this._infoEl.innerHTML = '<span style=\"color:rgb(0,180,180)\">Press y to apply  n to cancel</span>';
                if (this._infoTimer) clearTimeout(this._infoTimer);
              }
            }
            break;
          case 'tool':        this._renderTool(d.name || ''); break;
          case 'thinking':    this._renderThinking(d.content || ''); break;
          case 'code_block':  this._renderCodeBlock(d.language || '', d.code || ''); break;
          case 'result':
            this._stopSpinner();
            if (this._planConfirmActive) this._closeConfirm();
            this._renderResult(d.summary || '');
            break;
          case 'plan_confirm':
            if (this._planConfirmActive) this._closeConfirm();
            this._stopSpinner();
            this._streaming = false;
            this._responseStarted = false;
            this._setStatus('⏸', 'plan');
            this._renderPlanBlock(d.summary || '');
            this._renderPlanConfirm(d.summary || '');
            this._saveState();
            break;
          case 'skill_list':
            if (!this._skillsMode) this._enterSkillsMode();
            this._installMode = false;
            this._installError = '';
            this._renderSkillList(d.skills || []);
            break;
          case 'skill_info': {
            const info = d.skill || {};
            if (!info.name) break;
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
            if (!d.run_id || this._steerTarget?.run_id === String(d.run_id)) {
              this._steerTarget = null;
            }
            break;
          case 'clear':       this._clear(); break;
          case 'restore_conversation':
            // Disk copy arrived for a path with no localStorage cache.
            if ((d.path || '') === this._currentPath && d.buffer) {
              this._applyBuffer(d.buffer);
              try { localStorage.setItem(this._storageKey(this._currentPath), d.buffer); } catch (_) {}
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
      } catch (_) {}
    } catch (e) {
      console.error('[panel] createComm failed:', e);
    }
  }
}

// ===========================================================================
// Notebook Snapshot Dialog
// ===========================================================================

function _jpBtn(text: string, kind: string): HTMLButtonElement {
  const b = document.createElement('button');
  b.textContent = text;
  b.className = kind ? `jp-mod-styled jp-mod-${kind}` : 'jp-mod-styled';
  b.style.cssText = 'padding:4px 12px;font-size:12px;';
  return b;
}

function _showSnapshotDialog(snapshots: any[], panel: any, nb: any, cellRestored: boolean, nbPath: string): void {
  const container = document.createElement('div');
  container.style.cssText = `min-width:520px;max-height:550px;overflow-y:auto;font-size:13px;color:${CC.text};background:${CC.bg};padding:12px;border-radius:10px;`;

  const title = document.createElement('div');
  title.style.cssText = 'font-weight:600;margin-bottom:10px;font-size:14px;';
  const label = nbPath || '(unsaved notebook)';
  title.textContent = `Notebook Snapshots — ${label} (${snapshots.length})`;
  container.appendChild(title);

  if (cellRestored) {
    const warning = document.createElement('div');
    warning.style.cssText = `padding:6px 8px;margin-bottom:10px;background:rgba(255,107,128,0.12);border-left:2px solid ${CC.error};border-radius:0 6px 6px 0;font-size:12px;color:rgb(255,160,175);`;
    warning.textContent = '⚠ Cells have been individually restored in this session. Notebook restore will overwrite those changes.';
    container.appendChild(warning);
  }

  let selectedId = '';
  const previewPanel = document.createElement('div');
  previewPanel.style.cssText = `background:${CC.raised};padding:10px;border-radius:8px;margin-top:10px;max-height:280px;overflow-y:auto;white-space:pre-wrap;font-family:monospace;font-size:12px;color:${CC.inactive};line-height:1.5;`;
  previewPanel.textContent = 'Select a snapshot to preview';
  container.appendChild(previewPanel);

  const updateSelection = (s: any, row: HTMLElement) => {
    selectedId = s.id;
    container.querySelectorAll('.snapshot-row').forEach((el: any) => el.style.background = '');
    row.style.background = 'rgba(0,200,200,0.14)';
    // Show preview
    const previews = s.preview || [];
    if (previews.length > 0) {
      previewPanel.textContent = previews.map((p: string, i: number) => `[${i + 1}] ${p}`).join('\n');
    } else {
      previewPanel.textContent = '(no code preview)';
    }
  };

  snapshots.forEach((s: any, i: number) => {
    const row = document.createElement('div');
    row.className = 'snapshot-row';
    row.style.cssText = `padding:6px 10px;cursor:pointer;border-radius:6px;display:flex;justify-content:space-between;${i === 0 ? 'background:rgba(0,200,200,0.14);' : ''}`;
    const ts = new Date((s.timestamp || 0) * 1000).toLocaleString();
    row.innerHTML = `<span style="font-size:13px;"><b>${ts}</b></span><span style="color:${CC.subtle};font-size:12px;">${s.cells_count} cells</span>`;
    row.addEventListener('click', () => updateSelection(s, row));
    container.appendChild(row);
    if (i === 0) { selectedId = s.id; previewPanel.textContent = (s.preview || []).map((p: string, j: number) => `[${j + 1}] ${p}`).join('\n') || '(no code preview)'; }
  });

  const btnRow = document.createElement('div');
  btnRow.style.cssText = 'margin-top:10px;display:flex;gap:8px;';
  const restoreBtn = _jpBtn('Restore Notebook', 'accept');
  restoreBtn.addEventListener('click', () => {
    if (!selectedId || !panel._kernel) return;
    // Fetch snapshot cells, then restore directly via notebook model
    const future = panel._kernel.requestExecute({
      code: `from jupyter.notebook_snapshot import get_snapshot; import json; sid=${JSON.stringify(selectedId)}; np=${JSON.stringify(nbPath)}; print(json.dumps(get_snapshot(sid, nb_path=np).get("cells",[]) if get_snapshot(sid, nb_path=np) else []))`,
      store_history: false,
    });
    let stdout = '';
    future.onIOPub = (msg: any) => {
      if (msg.header.msg_type === 'stream' && msg.content?.name === 'stdout') stdout += msg.content.text;
    };
    future.done.then(() => {
      try {
        const cells = JSON.parse(stdout.trim());
        if (!cells || !cells.length) { restoreBtn.textContent = 'No cells'; return; }
        const model = nb.model;
        if (!model) { restoreBtn.textContent = 'No model'; return; }
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
      } catch (e) {
        console.error(e);
        restoreBtn.textContent = 'Failed';
        restoreBtn.className = 'jp-mod-styled jp-mod-warn';
      }
    });
  });
  btnRow.appendChild(restoreBtn);
  container.appendChild(btnRow);

  const bodyWidget = new Widget();
  bodyWidget.node.appendChild(container);
  showDialog({
    title: 'Notebook Snapshots',
    body: bodyWidget,
    buttons: [Dialog.okButton({ label: 'Close' })],
  });
}

// ===========================================================================
// Cell Snapshots Dialog
// ===========================================================================

function _stripHtml(s: string): string {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function _showCellSnapshotsDialog(cell: any, versions: any[], panel: any): void {
  if (!versions || versions.length === 0) {
    alert('No version history for this cell.');
    return;
  }

  const container = document.createElement('div');
  container.style.cssText = `min-width:520px;max-height:550px;overflow-y:auto;font-size:13px;color:${CC.text};background:${CC.bg};padding:12px;border-radius:10px;`;

  const title = document.createElement('div');
  title.style.cssText = 'font-weight:600;margin-bottom:10px;font-size:14px;';
  title.textContent = `Cell Snapshots (${versions.length})`;
  container.appendChild(title);

  let selectedIdx = 0;
  const preview = document.createElement('div');
  preview.style.cssText = `background:${CC.raised};padding:10px;border-radius:8px;margin-top:10px;max-height:300px;overflow-y:auto;white-space:pre-wrap;font-family:monospace;font-size:12px;color:${CC.inactive};line-height:1.5;`;
  container.appendChild(preview);

  const updatePreview = (idx: number) => {
    const v = versions[idx];
    if (!v) return;
    preview.textContent = `[${v.version}] ${new Date((v.timestamp || 0) * 1000).toLocaleString()}\n\nCode:\n${v.code || ''}\n\nOutput:\n${v.output || '(none)'}`;
  };
  updatePreview(0);

  versions.forEach((v: any, i: number) => {
    const row = document.createElement('div');
    row.style.cssText = `padding:6px 10px;cursor:pointer;border-radius:6px;display:flex;justify-content:space-between;${i === 0 ? 'background:rgba(0,200,200,0.14);' : ''}`;
    const ts = new Date((v.timestamp || 0) * 1000).toLocaleString();
    const code = (v.code || '').replace(/\n/g, ' ').substring(0, 80);
    row.innerHTML = `<span style="font-size:13px;"><b>${v.version}</b> ${ts}</span><span style="color:${CC.subtle};font-size:12px;">${_stripHtml(code)}</span>`;
    row.addEventListener('click', () => {
      selectedIdx = i;
      container.querySelectorAll('div[style]').forEach((el: any) => el.style.background = '');
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
    if (!v || !panel._kernel) return;
    const future = panel._kernel.requestExecute({
      code: `get_ipython().user_ns['_panel_input']('/cell-snapshot-restore ${cell.model.id} ${v.version}')`,
      store_history: false,
    });
    future.done.then((reply: any) => {
      if (reply.content.status === 'ok') {
        restoreBtn.textContent = 'Restored';
        restoreBtn.className = 'jp-mod-styled';
        restoreBtn.style.cssText = 'padding:4px 12px;font-size:12px;background:var(--jp-success-color1, #1a7f37);color:var(--jp-ui-inverse-font-color1, #fff);border:1px solid var(--jp-success-color2, #1a7f37);';
        setTimeout(() => {
          // Close dialog
          const dlg = document.querySelector('.jp-Dialog');
          if (dlg) (dlg as any).remove?.();
        }, 500);
      } else {
        restoreBtn.textContent = 'Failed';
        restoreBtn.className = 'jp-mod-styled jp-mod-warn';
      }
    });
  });
  btnRow.appendChild(restoreBtn);
  container.appendChild(btnRow);

  const bodyWidget = new Widget();
  bodyWidget.node.appendChild(container);
  showDialog({
    title: 'Cell History',
    body: bodyWidget,
    buttons: [Dialog.okButton({ label: 'Close' })],
  });
}

// ===========================================================================
// Plugin
// ===========================================================================

export const panelPlugin: JupyterFrontEndPlugin<void> = {
  id: 'skillbot:tui',
  autoStart: true,
  requires: [INotebookTracker, IRenderMimeRegistry],
  activate: (
    _app: JupyterFrontEnd,
    tracker: INotebookTracker,
    rendermime: IRenderMimeRegistry,
  ) => {
    const panel = new AgentPanel(rendermime);
    panel.setTracker(tracker);
    panel.setApp(_app);
    _app.shell.add(panel, 'right', { rank: 100 });
    _panelInstance = panel;
    let _panelOpened = false;

    let _currentCtx: any = null;
    let _cellsChangedModel: any = null;
    const onCellsChanged = (_sender: any, args: any) => {
      if (args.type !== 'remove' || !args.oldValues) return;
      const kernel = tracker.currentWidget?.context.sessionContext.session?.kernel;
      for (const cell of args.oldValues) {
        const src = cell?.sharedModel?.getSource?.() || cell?.value?.text || '';
        if (src.trim()) {
          kernel?.requestExecute({
            code: `get_ipython().user_ns['_panel_track_cell_delete'](${JSON.stringify(src)})`,
            store_history: false,
          });
        }
      }
    };
    const onKernelChanged = (_sender: any, args: any) => {
      // Always reset the comm: a kernel change (restart, switch, or lazy start
      // where oldValue is null) must never leave _comm bound to an old kernel.
      panel.resetComm();
      if (args.oldValue) {
        panel._clear();
      }
      if (args.newValue) panel.connectKernel(args.newValue);
    };

    const register = () => {
      const nb = tracker.currentWidget;
      if (!nb) return;
      const ctx = nb.context.sessionContext;
      if (!ctx) return;

      // Save the old buffer on its kernel; load the new buffer on the target kernel.
      const kernel = ctx.session?.kernel || null;
      const pathChanged = panel.setActivePath(nb.context.path || '', kernel);

      // wire kernel restart handler when context changes
      if (ctx !== _currentCtx) {
        if (_currentCtx) _currentCtx.kernelChanged.disconnect(onKernelChanged);
        _currentCtx = ctx;
        ctx.kernelChanged.connect(onKernelChanged);
      }

      if (kernel && pathChanged) panel.notifyNotebookSwitch(nb.context.path || '');

      // Wire cell deletion tracking (disconnect old on notebook change)
      const cells = nb.model?.cells;
      if (cells && cells !== _cellsChangedModel) {
        _cellsChangedModel?.changed.disconnect(onCellsChanged);
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
        const nb = tracker.currentWidget;
        if (!nb || !panel._kernel) return;
        const cell = nb.content.activeCell;
        if (!cell) return;

        const cellId = cell.model.id;
        const cellType = cell.model.type || 'code';
        if (cellType === 'markdown') { alert('Cell optimization only works for code cells.'); return; }
        const code = cell.model.sharedModel.getSource();
        if (!code.trim()) { alert('Cell is empty.'); return; }

        let output = '';
        let cellError = '';
        try {
          const outputs = (cell.model as any).outputs;
          if (outputs?.length > 0) {
            const last = outputs.get(outputs.length - 1);
            if (last?.output_type === 'error') {
              cellError = `${last.ename || 'Error'}: ${last.evalue || ''}`;
            } else {
              output = (last?.data?.['text/plain'] as string) || '';
            }
          }
        } catch (_) {}

        const input = document.createElement('textarea');
        input.placeholder = 'e.g. optimize query, fix bug, improve readability...';
        input.style.cssText = `width:100%;min-height:60px;background:${CC.raised};color:${CC.text};border:1px solid ${CC.border};border-radius:8px;padding:8px;font-size:12px;resize:vertical;font-family:inherit;box-sizing:border-box;`;

        const hint = document.createElement('div');
        hint.style.cssText = `font-size:11px;color:${CC.subtle};margin-top:4px;`;
        hint.textContent = 'Enter → Optimize    Shift+Enter → Optimize & Run';

        const body = new Widget();
        body.node.appendChild(input);
        body.node.appendChild(hint);

        // Build dialog manually for keyboard control
        let autoRun = false;
        const dialog = new Dialog({
          title: 'Cell Optimization',
          body,
          buttons: [
            Dialog.cancelButton(),
            Dialog.okButton({ label: 'Optimize & Run' }),
            Dialog.okButton({ label: 'Optimize' }),
          ],
        });
        // After render, hijack the dialog's keyboard handling
        dialog.node.addEventListener('keydown', (e: KeyboardEvent) => {
          if (e.key !== 'Enter' || e.isComposing) return;
          if (document.activeElement?.tagName === 'TEXTAREA') {
            e.preventDefault();
            e.stopPropagation();
            autoRun = e.shiftKey;
            const btns = dialog.node.querySelectorAll('.jp-Dialog-button');
            const btn = e.shiftKey
              ? (btns[btns.length - 2] as HTMLElement)
              : (btns[btns.length - 1] as HTMLElement);
            btn?.click();
          }
        }, true);
        setTimeout(() => input.focus(), 10);
        const dlgResult = await dialog.launch();

        const clicked = dlgResult.button.label;
        if (clicked === 'Cancel') return;
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
        if (!nb) return;
        const cell = nb.content.activeCell;
        if (!cell) return;
        const cellId = cell.model.id;
        if (!panel._kernel) return;
        const nbPath = nb.context.path || nb.context.localPath || '';
        const future = panel._kernel.requestExecute({
          code: `from jupyter.cell_snapshot import list_versions; import json; d={"versions":list_versions(${JSON.stringify(cellId)}, nb_path=${JSON.stringify(nbPath)}),"cell_id":${JSON.stringify(cellId)}}; print(json.dumps(d))`,
          store_history: false,
        });
        let stdout = '';
        future.onIOPub = (msg: any) => {
          if (msg.header.msg_type === 'stream' && msg.content?.name === 'stdout') stdout += msg.content.text;
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
          } catch (e) { console.error(e); alert('Failed to load cell snapshots.'); }
        });
      },
    });

    _app.commands.addCommand('skillbot:notebook-snapshots', {
      label: 'Notebook Snapshots',
      execute: async () => {
        const nb = tracker.currentWidget;
        if (!nb) return;
        if (!panel._kernel) return;
        const nbPath = nb.context.path || nb.context.localPath || '';
        const future = panel._kernel.requestExecute({
          code: `from jupyter.notebook_snapshot import list_snapshots_for; from jupyter.magic import _get_magic; import json; inst=_get_magic(); d={"snapshots":list_snapshots_for(${JSON.stringify(nbPath)}),"cell_restored":inst._cell_restored if inst else False}; print(json.dumps(d))`,
          store_history: false,
        });
        let stdout = '';
        future.onIOPub = (msg: any) => {
          if (msg.header.msg_type === 'stream' && msg.content?.name === 'stdout') stdout += msg.content.text;
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
          } catch (e) { console.error(e); alert('Failed to load snapshots.'); }
        });
      },
    });

    // Submenu on both .jp-Cell and .jp-Notebook
    const historyMenu = new Menu({ commands: _app.commands });
    historyMenu.title.label = 'Agent';
    historyMenu.addItem({ command: 'skillbot:cell-reference' });
    historyMenu.addItem({ command: 'skillbot:cell-optimize' });
    historyMenu.addItem({ type: 'separator' } as any);
    historyMenu.addItem({ command: 'skillbot:cell-history' });
    historyMenu.addItem({ command: 'skillbot:notebook-snapshots' });

    _app.contextMenu.addItem({
      selector: '.jp-Notebook',
      type: 'submenu' as any,
      submenu: historyMenu,
      rank: 50,
    });

    tracker.currentChanged.connect(() => register());
    setTimeout(register, 500);

    // When a notebook file is deleted from the file browser, purge its
    // conversation record so stale sessions don't linger in the switcher.
    try {
      const contents = (_app.serviceManager as any)?.contents;
      contents?.fileChanged?.connect((_sender: any, change: any) => {
        if (change?.type === 'delete') {
          const p = change.oldValue?.path || '';
          if (p && /\.ipynb$/.test(p)) panel.onNotebookFileDeleted(p);
        }
      });
    } catch (e) {
      console.error('[panel] fileChanged wiring failed:', e);
    }
  },
};
