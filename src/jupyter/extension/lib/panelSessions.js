"use strict";
// Session management + persistence helpers for AgentPanel.
// Per-notebook conversation buffers are stored under keys derived from the
// notebook path (see storageKey). A separate registry key tracks the set of
// known sessions so we can render the session switcher across reloads.
// Extracted from panel.ts; every function takes the panel instance as its
// first argument and accesses its state directly. All instance fields remain
// declared on the AgentPanel class.
Object.defineProperty(exports, "__esModule", { value: true });
exports.COLLAPSE_KEY = void 0;
exports.storageKey = storageKey;
exports.saveState = saveState;
exports.restoreState = restoreState;
exports.loadBuffer = loadBuffer;
exports.applyBuffer = applyBuffer;
exports.loadRegistry = loadRegistry;
exports.saveRegistry = saveRegistry;
exports.registerSession = registerSession;
exports.switchToSession = switchToSession;
exports.openNotebook = openNotebook;
exports.newSession = newSession;
exports.renameSession = renameSession;
exports.deleteSession = deleteSession;
exports.purgeSession = purgeSession;
exports.onNotebookFileDeleted = onNotebookFileDeleted;
exports.flashInfo = flashInfo;
exports.toggleSessionsCollapsed = toggleSessionsCollapsed;
exports.renderSessionBar = renderSessionBar;
const panelStyles_1 = require("./panelStyles");
// Buffer keys are `STORAGE_PREFIX + <notebook path>`; the registry and the
// collapse flag get their own fixed keys. COLLAPSE_KEY is also read by the
// AgentPanel constructor, so it is exported.
const STORAGE_PREFIX = 'skillbot-panel:';
const REGISTRY_KEY = 'skillbot-sessions';
exports.COLLAPSE_KEY = 'skillbot-sessions-collapsed';
function storageKey(panel, path) {
    const p = path !== undefined ? path : panel._currentPath;
    return STORAGE_PREFIX + (p || '__default__');
}
function saveState(panel) {
    let payload = '';
    try {
        payload = JSON.stringify({
            output: panel._outputEl.innerHTML,
            history: panel._history,
            mode: panel._mode,
            status: panel._statusEl.innerHTML,
        });
        localStorage.setItem(storageKey(panel), payload);
    }
    catch (_) { }
    // Mirror to disk so the conversation survives restarts / machine changes.
    if (payload && panel._currentPath && panel._kernel) {
        try {
            panel._kernel.requestExecute({
                code: `get_ipython().user_ns['_panel_save_conversation'](${JSON.stringify(panel._currentPath)}, ${JSON.stringify(payload)})`,
                store_history: false,
            });
        }
        catch (_) { }
    }
}
function restoreState(panel) {
    loadBuffer(panel, panel._currentPath);
}
/** Load the conversation buffer for a notebook path into the visible panel. */
function loadBuffer(panel, path) {
    // reset visible transient state before painting the target buffer
    panel._outputEl.innerHTML = '';
    panel._history = [];
    panel._currentBlock = null;
    panel._textEl = null;
    panel._thinkingEl = null;
    panel._streaming = false;
    let found = false;
    try {
        const raw = localStorage.getItem(storageKey(panel, path));
        if (raw) {
            applyBuffer(panel, raw);
            found = true;
        }
    }
    catch (_) { }
    // Nothing cached locally (new browser / machine) — ask backend for the
    // disk copy, which arrives async via the 'restore_conversation' action.
    if (!found && path && panel._kernel) {
        try {
            panel._kernel.requestExecute({
                code: `get_ipython().user_ns['_panel_load_conversation'](${JSON.stringify(path)})`,
                store_history: false,
            });
        }
        catch (_) { }
    }
}
/** Paint a serialized buffer (JSON string) into the visible panel. */
function applyBuffer(panel, raw) {
    try {
        const s = JSON.parse(raw);
        const sanitize = (html) => panel._rendermime.sanitizer.sanitize(html);
        if (typeof s.output === 'string') {
            panel._outputEl.innerHTML = sanitize(s.output);
            panel._scrollBottom();
        }
        if (s.history)
            panel._history = s.history;
        if (s.mode) {
            panel._mode = s.mode;
            panel._updateModeInfo();
            panel._renderActionBar();
        }
        if (typeof s.status === 'string')
            panel._statusEl.innerHTML = sanitize(s.status);
    }
    catch (_) { }
}
// ---- session registry / switcher ----------------------------------------
/** Map of notebook path → display label, persisted across reloads. */
function loadRegistry(_panel) {
    try {
        const raw = localStorage.getItem(REGISTRY_KEY);
        if (raw)
            return JSON.parse(raw);
    }
    catch (_) { }
    return {};
}
function saveRegistry(_panel, reg) {
    try {
        localStorage.setItem(REGISTRY_KEY, JSON.stringify(reg));
    }
    catch (_) { }
}
/** Register (or refresh) a notebook path as a known session. */
function registerSession(panel, path) {
    if (!path)
        return;
    const reg = loadRegistry(panel);
    if (!(path in reg)) {
        reg[path] = path.split('/').pop() || path;
    }
    saveRegistry(panel, reg);
    renderSessionBar(panel);
}
/**
 * Switch the panel to a notebook's conversation. Saves the current buffer,
 * loads the target buffer, and (if it differs from the active notebook) opens
 * the corresponding .ipynb via docmanager.
 */
function switchToSession(panel, path) {
    if (path === panel._currentPath) {
        openNotebook(panel, path);
        return;
    }
    saveState(panel); // persist the buffer we're leaving
    panel._currentPath = path;
    loadBuffer(panel, path);
    renderSessionBar(panel);
    openNotebook(panel, path);
}
/** Open an existing notebook file in the main area. */
function openNotebook(panel, path) {
    if (!panel._app || !path)
        return;
    try {
        panel._app.commands.execute('docmanager:open', { path });
    }
    catch (e) {
        console.error('[panel] docmanager:open failed:', e);
    }
}
/** Create a fresh Untitled.ipynb, open it, and switch the session to it. */
async function newSession(panel) {
    var _a, _b, _c, _d, _e;
    if (!panel._app)
        return;
    try {
        const cwd = ((_d = (_c = (_b = (_a = panel._tracker) === null || _a === void 0 ? void 0 : _a.currentWidget) === null || _b === void 0 ? void 0 : _b.context) === null || _c === void 0 ? void 0 : _c.path) === null || _d === void 0 ? void 0 : _d.split('/').slice(0, -1).join('/')) || '';
        await panel._app.serviceManager.kernelspecs.ready;
        const specs = panel._app.serviceManager.kernelspecs.specs;
        if (!((_e = specs === null || specs === void 0 ? void 0 : specs.kernelspecs) === null || _e === void 0 ? void 0 : _e.skillbot)) {
            throw new Error('skillbot kernelspec is not installed; run scripts/jupyter.sh setup');
        }
        const model = await panel._app.serviceManager.contents.newUntitled({
            path: cwd,
            type: 'notebook',
        });
        await panel._app.commands.execute('docmanager:open', {
            path: model.path,
            factory: 'Notebook',
            kernel: { name: 'skillbot' },
        });
        registerSession(panel, model.path);
        switchToSession(panel, model.path);
    }
    catch (e) {
        console.error('[panel] newSession failed:', e);
    }
}
/** Rename a session's display label (persists to registry). */
function renameSession(panel, path) {
    const reg = loadRegistry(panel);
    const current = reg[path] || path.split('/').pop() || path;
    const next = window.prompt('会话名称', current);
    if (next && next.trim()) {
        reg[path] = next.trim();
        saveRegistry(panel, reg);
        renderSessionBar(panel);
    }
}
/** Delete a session record after user confirmation (from the 🗑 button). */
function deleteSession(panel, path) {
    const reg = loadRegistry(panel);
    const label = reg[path] || path.split('/').pop() || path;
    if (!window.confirm(`删除会话「${label}」的对话记录？\n（不会删除 notebook 文件本身）`))
        return;
    purgeSession(panel, path);
    flashInfo(panel, '会话记录已删除');
}
/**
 * Remove all traces of a session: registry entry, localStorage buffer, and
 * the on-disk conversation file. If it's the session currently shown, clear
 * the panel too. Shared by the 🗑 button and the notebook-file-deletion
 * listener. Does NOT touch the .ipynb file itself.
 */
function purgeSession(panel, path) {
    if (!path)
        return;
    const reg = loadRegistry(panel);
    delete reg[path];
    saveRegistry(panel, reg);
    try {
        localStorage.removeItem(storageKey(panel, path));
    }
    catch (_) { }
    // Mirror the delete to disk via the backend bridge.
    if (panel._kernel) {
        try {
            panel._kernel.requestExecute({
                code: `get_ipython().user_ns['_panel_delete_conversation'](${JSON.stringify(path)})`,
                store_history: false,
            });
        }
        catch (_) { }
    }
    // If we just deleted the active session's record, blank the panel view.
    if (path === panel._currentPath) {
        panel._currentPath = '';
        panel._outputEl.innerHTML = '';
        panel._history = [];
        panel._currentBlock = null;
        panel._textEl = null;
        panel._thinkingEl = null;
        panel._streaming = false;
    }
    renderSessionBar(panel);
}
/** Public: called by the plugin when a notebook file is deleted from disk.
 *  Silently purges the matching session record (no confirm — the file is
 *  already gone). No-op if we have no record for that path. */
function onNotebookFileDeleted(panel, path) {
    if (!path)
        return;
    const reg = loadRegistry(panel);
    const hasRecord = path in reg;
    let hasBuffer = false;
    try {
        hasBuffer = localStorage.getItem(storageKey(panel, path)) != null;
    }
    catch (_) { }
    if (!hasRecord && !hasBuffer)
        return; // nothing to clean up
    purgeSession(panel, path);
    flashInfo(panel, `已随 notebook 删除会话记录`);
}
/** Briefly show a message in the info bar. */
function flashInfo(panel, msg) {
    if (!panel._infoEl)
        return;
    panel._infoEl.innerHTML = `<span style="color:${panelStyles_1.CC.success}">✓ ${msg}</span>`;
    if (panel._infoTimer)
        clearTimeout(panel._infoTimer);
    panel._infoTimer = setTimeout(() => { panel._infoEl.innerHTML = ''; }, 1800);
}
function toggleSessionsCollapsed(panel) {
    panel._sessionsCollapsed = !panel._sessionsCollapsed;
    try {
        localStorage.setItem(exports.COLLAPSE_KEY, panel._sessionsCollapsed ? '1' : '0');
    }
    catch (_) { }
    renderSessionBar(panel);
}
function renderSessionBar(panel) {
    if (!panel._sessionBarEl)
        return;
    const reg = loadRegistry(panel);
    const paths = Object.keys(reg);
    panel._sessionBarEl.className = 'skillbot-session-bar' + (panel._sessionsCollapsed ? ' collapsed' : '');
    panel._sessionBarEl.innerHTML = '';
    // header: collapse chevron + title + actions
    const header = document.createElement('div');
    header.className = 'skillbot-session-header';
    const titleWrap = document.createElement('span');
    titleWrap.className = 'skillbot-session-titlewrap';
    titleWrap.addEventListener('click', () => toggleSessionsCollapsed(panel));
    const chevron = document.createElement('span');
    chevron.className = 'skillbot-session-chevron';
    chevron.textContent = panel._sessionsCollapsed ? '▸' : '▾';
    titleWrap.appendChild(chevron);
    const title = document.createElement('span');
    title.className = 'skillbot-session-title';
    // When collapsed, show the current session's name inline for context.
    const curLabel = panel._currentPath ? (reg[panel._currentPath] || panel._currentPath.split('/').pop()) : '';
    title.textContent = panel._sessionsCollapsed && curLabel
        ? `会话 · ${curLabel}`
        : `会话 · ${paths.length}`;
    titleWrap.appendChild(title);
    header.appendChild(titleWrap);
    const actions = document.createElement('span');
    actions.className = 'skillbot-session-actions';
    const add = document.createElement('span');
    add.className = 'skillbot-session-btn skillbot-session-btn-primary';
    add.textContent = '＋ 新建';
    add.title = '新会话（新建 notebook）';
    add.addEventListener('click', () => { void newSession(panel); });
    actions.appendChild(add);
    header.appendChild(actions);
    panel._sessionBarEl.appendChild(header);
    // collapsed → header only (compact strip)
    if (panel._sessionsCollapsed)
        return;
    // vertical list of sessions
    const list = document.createElement('div');
    list.className = 'skillbot-session-list';
    if (paths.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'skillbot-session-empty';
        empty.textContent = '暂无会话，点「＋ 新建」开始';
        list.appendChild(empty);
    }
    for (const p of paths) {
        const active = p === panel._currentPath;
        const row = document.createElement('div');
        row.className = 'skillbot-session-row' + (active ? ' active' : '');
        row.title = p;
        row.addEventListener('click', () => switchToSession(panel, p));
        const dot = document.createElement('span');
        dot.className = 'skillbot-session-dot';
        row.appendChild(dot);
        const name = document.createElement('span');
        name.className = 'skillbot-session-name';
        name.textContent = reg[p];
        row.appendChild(name);
        const edit = document.createElement('span');
        edit.className = 'skillbot-session-edit';
        edit.textContent = '✎';
        edit.title = '重命名';
        edit.addEventListener('click', (e) => { e.stopPropagation(); renameSession(panel, p); });
        row.appendChild(edit);
        const del = document.createElement('span');
        del.className = 'skillbot-session-del';
        del.textContent = '✕';
        del.title = '删除此会话记录';
        del.addEventListener('click', (e) => { e.stopPropagation(); deleteSession(panel, p); });
        row.appendChild(del);
        list.appendChild(row);
    }
    panel._sessionBarEl.appendChild(list);
}
