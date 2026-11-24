"use strict";
// Plan confirmation UI helpers for AgentPanel
Object.defineProperty(exports, "__esModule", { value: true });
exports.renderPlanConfirm = renderPlanConfirm;
exports.getConfirmHint = getConfirmHint;
exports.renderConfirmOptions = renderConfirmOptions;
exports.closeConfirm = closeConfirm;
exports.sendConfirmToBackend = sendConfirmToBackend;
exports.submitPlanConfirm = submitPlanConfirm;
exports.cancelPlanConfirm = cancelPlanConfirm;
function renderPlanConfirm(panel, summary) {
    panel._planCurrentSummary = summary;
    panel._planConfirmOptionIdx = 0;
    panel._planConfirmFeedbackMode = false;
    panel._planConfirmActive = true;
    renderConfirmOptions(panel);
    panel._inputWrapper.style.display = 'none';
    panel._confirmWrapper.style.display = 'flex';
    panel._confirmWrapper.focus();
}
function getConfirmHint(panel) {
    if (panel._planConfirmFeedbackMode) {
        return 'Enter submit · Esc back to options';
    }
    return 'Tab/↑↓ select · Enter confirm · Esc cancel · Ctrl+C discard';
}
function renderConfirmOptions(panel) {
    // Save feedback text before re-render (innerHTML destroys old textarea)
    const oldTa = panel._confirmWrapper.querySelector('.skillbot-confirm-feedback');
    const savedFeedback = oldTa ? oldTa.value : '';
    const options = [
        'Yes, accept edits (code cells generated, manual review)',
        'Yes, auto-execute (code cells generated and run)',
        'No, revise this plan',
    ];
    const optionsHtml = options.map((label, i) => {
        const cls = i === panel._planConfirmOptionIdx
            ? 'skillbot-confirm-option skillbot-confirm-option-active'
            : 'skillbot-confirm-option';
        return `<div class="${cls}">${label}</div>`;
    }).join('');
    const feedbackStyle = panel._planConfirmFeedbackMode ? '' : 'display:none;';
    panel._confirmWrapper.innerHTML = `
    <div class="skillbot-confirm-label">Plan preview</div>
    <div class="skillbot-plan-preview">${panel._esc(panel._planCurrentSummary)}</div>
    <div class="skillbot-confirm-label">Approve this plan?</div>
    ${optionsHtml}
    <textarea class="skillbot-confirm-feedback" style="${feedbackStyle}"
              placeholder="Type your revision feedback, then press Enter..."></textarea>
    <div class="skillbot-confirm-hint">${getConfirmHint(panel)}</div>
  `;
    // Restore saved feedback text
    if (savedFeedback) {
        const newTa = panel._confirmWrapper.querySelector('.skillbot-confirm-feedback');
        if (newTa)
            newTa.value = savedFeedback;
    }
    if (panel._planConfirmFeedbackMode) {
        const ta = panel._confirmWrapper.querySelector('.skillbot-confirm-feedback');
        if (ta)
            ta.focus();
    }
}
function closeConfirm(panel) {
    panel._planConfirmActive = false;
    panel._planConfirmFeedbackMode = false;
    panel._planConfirmOptionIdx = 0;
    panel._planCurrentSummary = '';
    panel._confirmWrapper.style.display = 'none';
    panel._inputWrapper.style.display = 'flex';
}
function sendConfirmToBackend(panel, cmd) {
    panel._startBlock();
    panel._renderPrompt(cmd);
    panel._startSpinner();
    panel._setStatus('…', 'implementing');
    if (panel._kernel) {
        const code = `get_ipython().user_ns['_panel_input'](${JSON.stringify(cmd)})`;
        const future = panel._kernel.requestExecute({ code, store_history: false });
        let firstStdout = true;
        future.onIOPub = (msg) => {
            var _a;
            if (msg.header.msg_type === 'stream' && ((_a = msg.content) === null || _a === void 0 ? void 0 : _a.name) === 'stdout') {
                if (firstStdout) {
                    panel._renderResponseText(panel._stripAnsi(msg.content.text));
                    firstStdout = false;
                }
                else {
                    panel._appendTextChunk(panel._stripAnsi(msg.content.text));
                }
            }
        };
    }
    panel._inputEl.focus();
}
function submitPlanConfirm(panel) {
    if (panel._planConfirmFeedbackMode) {
        const ta = panel._confirmWrapper.querySelector('.skillbot-confirm-feedback');
        const feedback = ta ? ta.value.trim() : '';
        if (!feedback) {
            panel._planConfirmFeedbackMode = false;
            const hint = panel._confirmWrapper.querySelector('.skillbot-confirm-hint');
            renderConfirmOptions(panel);
            if (hint) {
                const newHint = panel._confirmWrapper.querySelector('.skillbot-confirm-hint');
                if (newHint)
                    newHint.textContent = 'Type feedback first, or select an option above';
                setTimeout(() => {
                    const h = panel._confirmWrapper.querySelector('.skillbot-confirm-hint');
                    if (h)
                        h.textContent = getConfirmHint(panel);
                }, 2000);
            }
            panel._confirmWrapper.focus();
            return;
        }
        closeConfirm(panel);
        sendConfirmToBackend(panel, `/confirm ${feedback}`);
        return;
    }
    switch (panel._planConfirmOptionIdx) {
        case 0:
            closeConfirm(panel);
            sendConfirmToBackend(panel, '/confirm accept_edits');
            break;
        case 1:
            closeConfirm(panel);
            sendConfirmToBackend(panel, '/confirm yes');
            break;
        case 2:
            panel._planConfirmFeedbackMode = true;
            renderConfirmOptions(panel);
            break;
    }
}
function cancelPlanConfirm(panel) {
    closeConfirm(panel);
    panel._inputEl.focus();
    panel._setStatus('○', 'idle');
    if (panel._kernel) {
        panel._kernel.requestExecute({
            code: `get_ipython().user_ns['_panel_input']("/confirm no")`,
            store_history: false,
        });
    }
}
