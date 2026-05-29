import { Widget } from '@lumino/widgets';
import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';
import { INotebookTracker, NotebookActions } from '@jupyterlab/notebook';
import { CC, STYLES } from './panelStyles';
import * as R from './panelRenderer';
import * as PC from './panelPlanConfirm';

const TARGET = 'skillbot:tui';
let _panelInstance: AgentPanel | null = null;
// ===========================================================================
// AgentPanel
// ===========================================================================

class AgentPanel extends Widget {
  private static STORAGE_KEY = 'skillbot-panel';
  private _root: ShadowRoot;
  private _outputEl: HTMLElement;
  private _inputEl: HTMLTextAreaElement;
  private _killRing: string = '';  // for Ctrl+Y yank
  private _lastKill: string = '';   // track consecutive kill type for accumulation
  private _charsPerLine: number = 80;  // computed from textarea width / monospace char width
  private _inputWrapper: HTMLElement;
  private _confirmWrapper: HTMLElement;
  private _statusEl: HTMLElement;
  private _statusTimer: any = null;
  private _execStartTime: number = 0;
  private _statusIcon: string = '○';
  private _statusLabel: string = 'idle';
  private _tracker: INotebookTracker | null = null;
  private _kernel: any = null;
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

  // message block
  private _currentBlock: HTMLElement | null = null;
  private _streaming = false;
  private _responseStarted = false;
  private _textEl: HTMLElement | null = null;  // accumulated text element for streaming
  _thinkingEl: HTMLElement | null = null;      // accumulated thinking element

  constructor() {
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

  private _onKeydown(e: KeyboardEvent): void {
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
            // Clear input (same as Escape)
            el.value = '';
            this._historyIdx = -1;
            this._historyDraft = '';
            this._killRing = ''; this._lastKill = '';
            this._resizeInput();
          }
          // On empty input, Ctrl+C is a no-op (panel stays open)
          return;
        }
        case 'l': e.preventDefault(); this._clear(); return;
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

    // Reset kill ring on printable character input
    if (e.key.length === 1 && !ctrl && !e.altKey) {
      this._killRing = ''; this._lastKill = '';
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

  private _tabComplete(): void {
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

  private _sendPrompt(): void {
    if (this._planConfirmActive) return;
    const text = this._inputEl.value.trim();
    if (!text) return;

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
    this._historyDraft = '';
    this._resizeInput();
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
  private _renderPrompt(text: string): void { R.renderPrompt(this, text); }
  private _renderResponseText(content: string): void { R.renderResponseText(this, content); }
  private _appendTextChunk(content: string): void { R.appendTextChunk(this, content); }
  private _renderTool(name: string): void { R.renderTool(this, name); }
  private _renderThinking(content: string): void { R.renderThinking(this, content); }
  private _renderCodeBlock(l: string, c: string): void { R.renderCodeBlock(this, l, c); }
  private _renderPlanBlock(text: string): void { R.renderPlanBlock(this, text); }
  private _renderResult(summary: string): void { R.renderResult(this, summary); }

  _clear(): void {
    this._outputEl.innerHTML = '';
    this._currentBlock = null;
    this._textEl = null;
    this._thinkingEl = null;
    this._streaming = false;
    this._stopSpinner();
    this._setStatus('○', 'idle');
    this._closeConfirm();  // ensure confirm UI is dismissed
    this._saveState();
    this._inputEl.value = '';
    this._historyIdx = -1;
    this._historyDraft = '';
    this._resizeInput();
  }

  // ---- persistence (localStorage) ----

  private _saveState(): void {
    try {
      localStorage.setItem(AgentPanel.STORAGE_KEY, JSON.stringify({
        output: this._outputEl.innerHTML,
        history: this._history,
        mode: this._mode,
        status: this._statusEl.innerHTML,
      }));
    } catch (_) {}
  }

  private _restoreState(): void {
    try {
      const raw = localStorage.getItem(AgentPanel.STORAGE_KEY);
      if (!raw) return;
      const s = JSON.parse(raw);
      if (s.output) { this._outputEl.innerHTML = s.output; this._scrollBottom(); }
      if (s.history) this._history = s.history;
      if (s.mode) { this._mode = s.mode; this._updateModeInfo(); }
      if (s.status) this._statusEl.innerHTML = s.status;
    } catch (_) {}
  }

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
    if (icon === '…' && this._execStartTime > 0) {
      const elapsed = Math.floor((Date.now() - this._execStartTime) / 1000);
      this._statusEl.innerHTML = `<span>${icon} ${label} (${elapsed}s)</span><span>skillbot</span>`;
    } else {
      this._statusEl.innerHTML = `<span>${icon} ${label}</span><span>skillbot</span>`;
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

  // ---- helpers -------------------------------------------------------------

  private _scrollBottom(): void {
    this._outputEl.scrollTop = this._outputEl.scrollHeight;
  }

  private _stripAnsi(s: string): string {
    return s.replace(/\x1b\[[0-9;]*m/g, '');
  }

  private _esc(s: string): string {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  setTracker(tracker: INotebookTracker): void {
    this._tracker = tracker;
  }

  _handleCellComm(comm: any, msg: any): void {
    try {
      this._handleCellCommImpl(comm, msg);
    } catch (e) {
      console.error('[panel] _handleCellComm failed:', e);
    }
  }

  private _handleCellCommImpl(comm: any, msg: any): void {
    const data = msg.content?.data || {};
    const nb = this._tracker?.currentWidget;
    if (!nb) return;
    const model = nb.model;
    if (!model) return;

    const code: string = data.code || '';
    const auto: boolean = data.auto !== false;
    const cellType: string = data.cell_type || 'code';
    const replaceId: string = data.replace_cell_id || '';
    if (!code) return;

    const notebook = nb.content;

    if (replaceId) {
      const cells = model.sharedModel.cells;
      for (let i = cells.length - 1; i >= 0; i--) {
        if (cells[i].id === replaceId) {
          cells[i].source = code;
          notebook.activeCellIndex = i;
          comm.send({ cell_id: cells[i].id });
          if (cellType !== 'markdown' && auto) {
            NotebookActions.run(notebook, nb.context.sessionContext);
          }
          return;
        }
      }
    }

    // Insert new cell + execute
    const activeIndex = notebook.activeCellIndex;
    model.sharedModel.insertCell(activeIndex + 1, {
      cell_type: cellType as 'code' | 'markdown',
      source: code,
      metadata: {},
    });
    const newCell = model.sharedModel.cells[activeIndex + 1];
    notebook.activeCellIndex = activeIndex + 1;

    comm.send({ cell_id: newCell.id });

    if (cellType === 'markdown' || !auto) return;
    NotebookActions.run(notebook, nb.context.sessionContext);
  }

  // ---- kernel / comm -------------------------------------------------------

  resetComm(): void {
    if (this._comm) {
      try { this._comm.close(); } catch (_) {}
      this._comm = null;
    }
    this._kernel = null;
    this._stopStatusTimer();
  }

  connectKernel(kernel: any): void {
    this._kernel = kernel;

    // Re-register cell-execution target (needed on kernel restart)
    try {
      kernel.registerCommTarget('skillbot:execute-cell', (comm: any, msg: any) => {
        this._handleCellComm(comm, msg);
      });
    } catch (e) {
      console.error('[panel] registerCommTarget failed:', e);
    }

    if (this._comm) return;

    try {
      this._comm = kernel.createComm(TARGET);
      this._comm.open();
      this._comm.onMsg = (m: any) => {
        const d = m.content?.data || {};
        switch (d.action) {
          case 'text':        this._appendTextChunk(this._stripAnsi(d.content || '')); break;
          case 'tool':        this._renderTool(d.name || ''); break;
          case 'thinking':    this._renderThinking(d.content || ''); break;
          case 'code_block':  this._renderCodeBlock(d.language || '', d.code || ''); break;
          case 'result':
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
          case 'clear':       this._clear(); break;
        }
      };
    } catch (e) {
      console.error('[panel] createComm failed:', e);
    }
  }
}

// ===========================================================================
// Plugin
// ===========================================================================

export const panelPlugin: JupyterFrontEndPlugin<void> = {
  id: 'skillbot:tui',
  autoStart: true,
  requires: [INotebookTracker],
  activate: (_app: JupyterFrontEnd, tracker: INotebookTracker) => {
    const panel = new AgentPanel();
    panel.setTracker(tracker);
    _app.shell.add(panel, 'right', { rank: 100 });
    _panelInstance = panel;
    let _panelOpened = false;

    let _currentCtx: any = null;
    const onKernelChanged = (_sender: any, args: any) => {
      if (args.oldValue) {
        panel.resetComm();
        panel._clear();
      }
      if (args.newValue) panel.connectKernel(args.newValue);
    };

    const register = () => {
      const nb = tracker.currentWidget;
      if (!nb) return;
      const ctx = nb.context.sessionContext;
      if (!ctx) return;

      // wire kernel restart handler when context changes
      if (ctx !== _currentCtx) {
        if (_currentCtx) _currentCtx.kernelChanged.disconnect(onKernelChanged);
        _currentCtx = ctx;
        ctx.kernelChanged.connect(onKernelChanged);
      }

      const kernel = ctx.session?.kernel;
      if (kernel) {
        // register cell-execution target directly (not through connectKernel)
        try {
          kernel.registerCommTarget('skillbot:execute-cell', (comm: any, msg: any) => {
            panel._handleCellComm(comm, msg);
          });
        } catch (e) {
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
