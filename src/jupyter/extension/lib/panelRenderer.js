"use strict";
// Output rendering helpers for AgentPanel
// All functions take the panel instance (as any to avoid circular imports)
Object.defineProperty(exports, "__esModule", { value: true });
exports.ensureResponsePrefix = ensureResponsePrefix;
exports.renderPrompt = renderPrompt;
exports.renderResponseText = renderResponseText;
exports.appendTextChunk = appendTextChunk;
exports.renderTool = renderTool;
exports.renderThinking = renderThinking;
exports.renderCodeBlock = renderCodeBlock;
exports.renderPlanBlock = renderPlanBlock;
exports.renderResult = renderResult;
function ensureResponsePrefix(panel) {
    if (!panel._responseStarted) {
        panel._responseStarted = true;
        const prefix = document.createElement('div');
        prefix.className = 'skillbot-response-prefix';
        prefix.textContent = '  ⎿ ';
        panel._appendToBlock(prefix);
    }
}
function renderPrompt(panel, text) {
    const div = document.createElement('div');
    div.className = 'skillbot-prompt-line';
    div.innerHTML = `<span class="skillbot-prompt-prefix">❯</span><span class="skillbot-prompt-text">${panel._esc(text)}</span>`;
    panel._appendToBlock(div);
}
function renderResponseText(panel, content) {
    ensureResponsePrefix(panel);
    panel._textEl = null;
    panel._thinkingEl = null;
    appendTextChunk(panel, content);
}
function appendTextChunk(panel, content) {
    if (!panel._textEl || !panel._textEl.parentElement) {
        panel._textEl = document.createElement('div');
        panel._textEl.className = 'skillbot-response-text';
        panel._textEl.textContent = content;
        panel._appendToBlock(panel._textEl);
    }
    else {
        panel._textEl.textContent += content;
    }
}
function renderTool(panel, name) {
    ensureResponsePrefix(panel);
    panel._textEl = null;
    panel._thinkingEl = null;
    panel._thinkingEl = null;
    const div = document.createElement('div');
    div.className = 'skillbot-tool-line';
    div.textContent = `⬢ ${name}`;
    panel._appendToBlock(div);
}
function renderThinking(panel, content) {
    ensureResponsePrefix(panel);
    // Accumulate thinking into a single element (each token arrives separately)
    if (!panel._thinkingEl || !panel._thinkingEl.parentElement) {
        panel._textEl = null;
        panel._thinkingEl = null;
        panel._thinkingEl = document.createElement('div');
        panel._thinkingEl.className = 'skillbot-thinking-line';
        panel._thinkingEl.textContent = `∴ ${content}`;
        panel._appendToBlock(panel._thinkingEl);
    }
    else {
        // If currently collapsed, restore full text before appending new chunk
        if (panel._thinkingCollapsed && panel._thinkingEl.hasAttribute('data-full')) {
            panel._thinkingEl.textContent = panel._thinkingEl.getAttribute('data-full') || '';
            panel._thinkingEl.removeAttribute('data-full');
        }
        // Add space between chunks (thinking tokens arrive without whitespace)
        const prev = panel._thinkingEl.textContent;
        const needSpace = prev.length > 0 && !prev.endsWith(' ') && !content.startsWith(' ') && !prev.endsWith('\n');
        panel._thinkingEl.textContent += (needSpace ? ' ' : '') + content;
    }
    // Apply collapse if active (Ctrl+T default: collapsed 150 chars)
    if (panel._thinkingCollapsed !== undefined) {
        panel._applyThinkingCollapse();
    }
}
function renderCodeBlock(panel, _language, code) {
    ensureResponsePrefix(panel);
    panel._textEl = null;
    panel._thinkingEl = null;
    const wrapper = document.createElement('div');
    wrapper.className = 'skillbot-code-block';
    wrapper.innerHTML = `<pre><code>${panel._esc(code)}</code></pre>`;
    panel._appendToBlock(wrapper);
}
function renderPlanBlock(panel, text) {
    ensureResponsePrefix(panel);
    panel._textEl = null;
    panel._thinkingEl = null;
    const wrapper = document.createElement('div');
    wrapper.className = 'skillbot-plan-block';
    wrapper.innerHTML = `<div class="skillbot-plan-header">⏸ Plan</div>${panel._esc(text)}`;
    panel._appendToBlock(wrapper);
}
function renderResult(panel, summary) {
    ensureResponsePrefix(panel);
    panel._textEl = null;
    panel._thinkingEl = null;
    const div = document.createElement('div');
    div.className = 'skillbot-result-line';
    div.innerHTML = `<span style="color:rgb(78,186,101)">✓</span> ${panel._esc(summary)}`;
    panel._appendToBlock(div);
    panel._stopSpinner();
    panel._setStatus('✓', 'done');
    panel._streaming = false;
    panel._saveState();
}
