// ---------------------------------------------------------------------------
// Claude Code colour palette
// ---------------------------------------------------------------------------
export const CC = {
  bg:        '#171717',
  surface:   '#2c2c2c',
  text:      '#ececec',
  inactive:  'rgb(175,175,175)',
  subtle:    'rgb(130,130,130)',
  border:    '#333',
  accent:    'rgb(0,180,180)',  // bright teal for section dividers
  brand:     'rgb(215,119,87)',
  success:   'rgb(78,186,101)',
  error:     'rgb(255,107,128)',
  userBg:    'rgb(55,55,55)',
  pointer:   'rgb(175,175,175)',  // matches cc-haha 'subtle' for pointer
};

// All CSS lives inside shadowRoot — completely isolated from JupyterLab
export const STYLES = `
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

/* Collapsible tool output */
.skillbot-response-text details {
  margin-left: 16px;
  padding: 0;
}
.skillbot-response-text details summary {
  color: rgb(150,150,150);
  font-size: 12px;
  cursor: pointer;
  padding: 2px 0;
}
.skillbot-response-text details summary:hover {
  color: rgb(200,200,200);
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

/* ---- spinner (cc-haha style) ---- */
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
  border-r、adius: 2px;
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
