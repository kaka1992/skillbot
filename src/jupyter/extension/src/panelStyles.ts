// ---------------------------------------------------------------------------
// Claude Code colour palette
// ---------------------------------------------------------------------------
export const CC = {
  // Layered dark surfaces: canvas < surface < raised (was flat bg/surface).
  bg:        '#141417',           // canvas — a touch deeper for more contrast
  surface:   '#1f1f25',           // panel surface (code / action bar)
  raised:    '#26262e',           // raised cards (code block, tool body)
  text:      '#f2f2f7',           // primary — brighter for readability
  inactive:  'rgb(196,196,208)',  // secondary text (was 175) — pulled brighter
  subtle:    'rgb(140,140,155)',  // tertiary/muted (was 130) — kept distinct
  border:    '#2e2e37',           // softer, cooler border
  accent:    'rgb(0,200,200)',    // brighter teal for dividers / focus
  brand:     'rgb(230,140,105)',  // warm brand accent (tool lines) — brighter
  success:   'rgb(90,205,120)',
  error:     'rgb(255,107,128)',
  userBg:    'rgba(0,200,200,0.10)',  // subtle teal tint for user prompt
  userLine:  'rgb(0,180,180)',        // user prompt left accent
  pointer:   'rgb(0,200,200)',        // prompt pointer picks up the accent
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
  border-bottom: 1px solid ${CC.border};
  color: ${CC.subtle};
  font-size: 12px;
}
.skillbot-welcome-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.skillbot-welcome-title {
  font-size: 14px;
  font-weight: 600;
  color: ${CC.text};
}
.skillbot-welcome-hint {
  font-size: 12px;
  font-weight: 500;
  color: ${CC.inactive};
  line-height: 1.5;
}

/* ---- status dot (top-bar state indicator) ---- */
.skillbot-status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
  background: ${CC.subtle};
  box-shadow: 0 0 0 3px rgba(255,255,255,0.03);
  transition: background 0.2s, box-shadow 0.2s;
}
.skillbot-status-dot--idle {
  background: ${CC.subtle};
}
.skillbot-status-dot--thinking {
  background: ${CC.accent};
  box-shadow: 0 0 0 3px rgba(0,200,200,0.18);
  animation: skillbot-pulse 1s ease-in-out infinite;
}
.skillbot-status-dot--done {
  background: ${CC.success};
  box-shadow: 0 0 0 3px rgba(90,205,120,0.15);
}
.skillbot-status-dot--interrupted {
  background: ${CC.brand};
  box-shadow: 0 0 0 3px rgba(230,140,105,0.15);
}
.skillbot-status-dot--plan {
  background: ${CC.accent};
  box-shadow: 0 0 0 3px rgba(0,200,200,0.18);
}

.skillbot-output {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px 8px 12px;
  scroll-behavior: smooth;
  color: ${CC.text};
}
.skillbot-output::-webkit-scrollbar { width: 7px; }
.skillbot-output::-webkit-scrollbar-thumb { background: #33333d; border-radius: 4px; }
.skillbot-output::-webkit-scrollbar-track { background: transparent; }

/* ---- message block (one prompt+response pair) ---- */
.skillbot-msg-block {
  margin-top: 14px;
  color: ${CC.text};
}

/* ---- user prompt (right-aligned chat bubble) ---- */
.skillbot-prompt-line {
  display: flex;
  align-items: flex-start;
  background: ${CC.userBg};
  padding: 8px 12px;
  border-radius: 12px 12px 4px 12px;
  border: 1px solid rgba(0,200,200,0.22);
  margin: 6px 0 6px auto;
  width: fit-content;
  max-width: 85%;
}
.skillbot-prompt-prefix {
  display: none;
}
.skillbot-prompt-text {
  color: ${CC.text};
  white-space: pre-wrap;
  word-break: break-word;
}
.skillbot-prompt-refs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 5px;
}
.skillbot-prompt-ref {
  color: ${CC.accent};
  font-size: 11px;
  font-weight: 600;
}

/* ---- agent response ---- */
.skillbot-response-prefix {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 6px 0 3px 0;
  user-select: none;
  flex-shrink: 0;
}
.skillbot-agent-avatar {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #08201f;
  background: linear-gradient(135deg, ${CC.accent}, ${CC.brand});
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  flex-shrink: 0;
}
.skillbot-agent-name {
  font-size: 11px;
  font-weight: 600;
  color: ${CC.inactive};
  letter-spacing: 0.02em;
}
.skillbot-response-text {
  color: ${CC.text};
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.skillbot-response-text p {
  margin: 0 0 10px;
}
.skillbot-response-text p:last-child {
  margin-bottom: 0;
}
.skillbot-response-text ul,
.skillbot-response-text ol {
  margin: 4px 0 10px;
  padding-left: 24px;
}
.skillbot-response-text li {
  margin: 2px 0;
}
.skillbot-response-text code {
  padding: 1px 4px;
  border-radius: 4px;
  background: ${CC.raised};
  color: ${CC.brand};
  font-family: inherit;
}
.skillbot-response-text pre {
  margin: 8px 0;
  padding: 10px 12px;
  overflow-x: auto;
  border: 1px solid ${CC.border};
  border-radius: 6px;
  background: ${CC.raised};
  white-space: pre;
}
.skillbot-response-text pre code {
  padding: 0;
  background: transparent;
  color: ${CC.text};
}
.skillbot-response-text a {
  color: ${CC.accent};
}

.skillbot-tool-line {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: ${CC.brand};
  background: rgba(230,140,105,0.10);
  border: 1px solid rgba(230,140,105,0.25);
  border-radius: 999px;
  padding: 3px 11px;
  margin: 3px 6px 3px 8px;
  font-size: 11.5px;
  font-weight: 600;
  max-width: calc(100% - 16px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

/* Collapsible tool output */
.skillbot-response-text details {
  margin-left: 16px;
  padding: 0;
}
.skillbot-response-text details summary {
  color: ${CC.subtle};
  font-size: 12px;
  cursor: pointer;
  padding: 2px 0;
}
.skillbot-response-text details summary:hover {
  color: ${CC.text};
}

.skillbot-thinking-line {
  color: ${CC.subtle};
  font-style: italic;
  padding: 4px 10px;
  margin: 3px 0 3px 8px;
  border-left: 2px solid #4a4a58;
  background: rgba(255,255,255,0.02);
  border-radius: 0 6px 6px 0;
}

.skillbot-code-block {
  background: ${CC.raised};
  border: 1px solid ${CC.border};
  border-radius: 8px;
  margin: 8px 0 8px 8px;
  padding: 11px 14px;
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
.skillbot-code-block::-webkit-scrollbar { height: 5px; }
.skillbot-code-block::-webkit-scrollbar-thumb { background: #33333d; border-radius: 3px; }

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
  color: ${CC.inactive};
  margin-left: 4px;
}

/* ---- info bar (mode switch messages) ---- */
.skillbot-info {
  font-size: 12px;
  font-weight: 500;
  color: ${CC.inactive};
  padding: 6px 16px;
  border-top: 1px solid ${CC.border};
  min-height: 20px;
  transition: opacity 0.3s;
}

.skillbot-status {
  font-size: 12px;
  font-weight: 500;
  color: ${CC.inactive};
  padding: 6px 16px;
  border-top: 1px solid ${CC.border};
  user-select: none;
  display: flex;
  justify-content: space-between;
}

/* ---- agent action bar ---- */
.skillbot-action-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  padding: 8px 12px;
  background: ${CC.surface};
  border-top: 1px solid ${CC.border};
}
.skillbot-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 13px;
  border-radius: 9px;
  background: ${CC.raised};
  color: ${CC.inactive};
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
  border: 1px solid ${CC.border};
  transition: background 0.12s, color 0.12s, border-color 0.12s, transform 0.08s;
}
.skillbot-action-btn:hover {
  color: ${CC.text};
  background: #30303a;
  border-color: #3d3d48;
  transform: translateY(-1px);
}
.skillbot-action-btn:active {
  transform: translateY(0);
}
.skillbot-action-stop {
  color: ${CC.error};
  border-color: rgba(255,107,128,0.4);
}
.skillbot-action-stop:hover {
  color: #fff;
  background: ${CC.error};
  border-color: ${CC.error};
}
.skillbot-action-skills.active {
  color: ${CC.text};
  background: rgba(0,200,200,0.15);
  border-color: ${CC.accent};
}
.skillbot-action-skills.active:hover {
  background: rgba(0,200,200,0.25);
}
.skillbot-action-plan.active {
  color: #08201f;
  background: ${CC.accent};
  border-color: ${CC.accent};
}
.skillbot-action-plan.active:hover {
  background: rgb(0,220,220);
}
.skillbot-action-btn.disabled {
  opacity: 0.4;
  cursor: default;
  pointer-events: none;
}

/* ---- session switcher (vertical list) ---- */
.skillbot-session-bar {
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid ${CC.border};
  background: ${CC.bg};
  max-height: 240px;
}
.skillbot-session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px 6px 12px;
}
.skillbot-session-titlewrap {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  min-width: 0;
}
.skillbot-session-chevron {
  font-size: 10px;
  color: ${CC.subtle};
  transition: color 0.12s;
}
.skillbot-session-titlewrap:hover .skillbot-session-chevron,
.skillbot-session-titlewrap:hover .skillbot-session-title {
  color: ${CC.text};
}
.skillbot-session-bar.collapsed {
  max-height: none;
}
.skillbot-session-bar.collapsed .skillbot-session-header {
  padding-bottom: 8px;
}
.skillbot-session-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: ${CC.subtle};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.skillbot-session-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.skillbot-session-btn {
  padding: 3px 10px;
  border-radius: 6px;
  background: ${CC.surface};
  color: ${CC.inactive};
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  user-select: none;
  border: 1px solid transparent;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
}
.skillbot-session-btn:hover {
  color: ${CC.text};
  background: #3a3a3a;
}
.skillbot-session-btn-primary {
  color: ${CC.brand};
  border-color: rgba(215,119,87,0.35);
}
.skillbot-session-btn-primary:hover {
  color: #fff;
  background: ${CC.brand};
  border-color: ${CC.brand};
}
.skillbot-session-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 2px 8px 8px 8px;
  overflow-y: auto;
}
.skillbot-session-list::-webkit-scrollbar { width: 5px; }
.skillbot-session-list::-webkit-scrollbar-thumb { background: ${CC.subtle}; border-radius: 3px; }
.skillbot-session-empty {
  padding: 10px 8px;
  font-size: 12px;
  color: ${CC.subtle};
  text-align: center;
}
.skillbot-session-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: background 0.12s;
}
.skillbot-session-row:hover {
  background: ${CC.surface};
}
.skillbot-session-row.active {
  background: ${CC.userBg};
  border-left-color: ${CC.accent};
}
.skillbot-session-dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: ${CC.subtle};
}
.skillbot-session-row.active .skillbot-session-dot {
  background: ${CC.accent};
  box-shadow: 0 0 4px ${CC.accent};
}
.skillbot-session-name {
  flex: 1;
  min-width: 0;
  font-size: 12.5px;
  color: ${CC.inactive};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.skillbot-session-row.active .skillbot-session-name {
  color: ${CC.text};
  font-weight: 500;
}
.skillbot-session-edit {
  flex-shrink: 0;
  font-size: 12px;
  color: transparent;
  cursor: pointer;
  padding: 0 2px;
  transition: color 0.12s;
}
.skillbot-session-row:hover .skillbot-session-edit {
  color: ${CC.subtle};
}
.skillbot-session-edit:hover {
  color: ${CC.accent};
}
.skillbot-session-del {
  flex-shrink: 0;
  font-size: 12px;
  color: transparent;
  cursor: pointer;
  padding: 0 2px;
  transition: color 0.12s;
}
.skillbot-session-row:hover .skillbot-session-del {
  color: ${CC.subtle};
}
.skillbot-session-del:hover {
  color: ${CC.error};
}

.skillbot-cell-references {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 7px 12px 2px;
  background: ${CC.surface};
  border-top: 1px solid ${CC.border};
}
.skillbot-cell-reference {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  padding: 4px 7px;
  border: 1px solid rgba(0,200,200,0.35);
  border-radius: 6px;
  background: rgba(0,200,200,0.10);
  color: ${CC.accent};
  font-size: 11px;
  font-weight: 600;
}
.skillbot-cell-reference button {
  width: 16px;
  height: 16px;
  padding: 0;
  border: 0;
  background: transparent;
  color: ${CC.inactive};
  cursor: pointer;
  font: inherit;
  line-height: 14px;
}
.skillbot-cell-reference button:hover {
  color: ${CC.error};
}

.skillbot-input-wrapper {
  display: flex;
  align-items: center;
  margin: 4px 12px 12px 12px;
  background: ${CC.raised};
  border: 1px solid ${CC.border};
  border-radius: 12px;
  transition: border-color 0.12s, box-shadow 0.12s;
}
.skillbot-input-wrapper:focus-within {
  border-color: ${CC.accent};
  box-shadow: 0 0 0 3px rgba(0,200,200,0.12);
}
.skillbot-input-marker {
  color: ${CC.accent};
  font-weight: 700;
  padding-left: 14px;
  user-select: none;
  flex-shrink: 0;
}
.skillbot-input {
  flex: 1;
  background: transparent;
  color: ${CC.text};
  border: none;
  padding: 10px 12px 10px 8px;
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
  color: ${CC.subtle};
  font-weight: 400;
}
.skillbot-input::-webkit-scrollbar { width: 4px; }
.skillbot-input::-webkit-scrollbar-thumb { background: #33333d; border-radius: 2px; }

/* ---- slash-command dropdown (inside shadow root) ---- */
.skillbot-command-dropdown {
  background: ${CC.surface};
  border: 1px solid ${CC.border};
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.45);
  overflow: hidden;
}
.skillbot-command-item {
  padding: 7px 13px;
  font-size: 12px;
  cursor: pointer;
  color: ${CC.inactive};
  transition: background 0.1s, color 0.1s;
}
.skillbot-command-item:hover {
  color: ${CC.text};
  background: ${CC.raised};
}
.skillbot-command-item.active {
  color: ${CC.text};
  background: rgba(0,200,200,0.14);
}

/* ---- plan confirmation (replaces input area) ---- */
.skillbot-confirm-wrapper {
  border-top: 1px solid ${CC.border};
  padding: 10px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.skillbot-confirm-label {
  color: ${CC.text};
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
}
.skillbot-confirm-option {
  padding: 6px 10px;
  border-radius: 6px;
  color: ${CC.inactive};
  cursor: pointer;
}
.skillbot-confirm-option-active {
  background: ${CC.raised};
  color: ${CC.text};
  font-weight: 600;
}
.skillbot-confirm-option-active::before {
  content: '❯ ';
  color: ${CC.brand};
}
.skillbot-confirm-hint {
  color: ${CC.subtle};
  font-size: 12px;
  margin-top: 4px;
}

/* ---- plan block in output area ---- */
.skillbot-plan-block {
  background: rgba(0,200,200,0.06);
  border-left: 3px solid ${CC.accent};
  padding: 8px 12px;
  margin: 6px 0;
  border-radius: 6px;
  white-space: pre-wrap;
  line-height: 1.6;
  color: ${CC.text};
}
.skillbot-plan-header {
  font-weight: 600;
  color: ${CC.accent};
  font-size: 11px;
  margin-bottom: 6px;
}

/* ---- plan preview in confirm dialog ---- */
.skillbot-plan-preview {
  background: rgba(0,200,200,0.06);
  border-left: 3px solid ${CC.accent};
  padding: 8px 12px;
  margin-bottom: 8px;
  max-height: 200px;
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  border-radius: 6px;
  color: ${CC.text};
}
.skillbot-plan-preview::-webkit-scrollbar { width: 4px; }
.skillbot-plan-preview::-webkit-scrollbar-thumb { background: #33333d; border-radius: 2px; }

/* ---- feedback textarea in confirm ---- */
.skillbot-confirm-feedback {
  background: ${CC.raised};
  color: ${CC.text};
  border: 1px solid ${CC.border};
  padding: 8px 10px;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  min-height: 60px;
  outline: none;
  border-radius: 8px;
  box-sizing: border-box;
}
.skillbot-confirm-feedback:focus {
  border-color: ${CC.accent};
  box-shadow: 0 0 0 3px rgba(0,200,200,0.12);
}
.skillbot-confirm-feedback::placeholder {
  color: ${CC.subtle};
  font-weight: 400;
}
`;
