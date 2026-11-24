// Skills view UI helpers for AgentPanel.
// Renders the in-panel skill browser (list → info → full body), handles its
// keyboard navigation, install/uninstall, and enable/disable toggles.
// Extracted from panel.ts; every function takes the panel instance as its
// first argument and accesses its state directly. All instance fields remain
// declared on the AgentPanel class.

import { CC } from './panelStyles';

export function enterSkillsMode(panel: any): void {
  panel._skillsMode = true;
  panel._inputWrapper.style.display = 'none';
  panel._outputEl.querySelectorAll('.skillbot-skill-list').forEach((el: Element) => el.remove());
  panel._renderActionBar();
}

export function exitSkillsMode(panel: any): void {
  panel._skillsMode = false;
  panel._inputWrapper.style.display = '';
  panel._skillRows = [];
  panel._skillSelectedIdx = 0;
  panel._expandedIdx = -1;
  panel._outputEl.querySelectorAll('.skillbot-skill-list').forEach((el: Element) => el.remove());
  panel._inputEl.focus();
  // Reset textarea height (lost during display:none)
  setTimeout(() => panel._resizeInput(), 0);
  panel._renderActionBar();
}

export function renderSkillList(panel: any, skills: Array<{name: string, description: string, enabled: boolean, body?: string}>): void {
  panel._skillData = skills.map(s => ({...s, body: s.body || ''}));
  panel._skillRows = [];
  panel._skillSelectedIdx = 0;
  panel._expandedIdx = -1;
  panel._fullBodyIdx = -1;
  panel._installMode = false;
  panel._installError = '';

  // Remove old list, rebuild
  panel._outputEl.querySelectorAll('.skillbot-skill-list').forEach((el: Element) => el.remove());

  const wrapper = document.createElement('div');
  wrapper.className = 'skillbot-skill-list';
  wrapper.tabIndex = 0;
  wrapper.style.outline = 'none';
  wrapper.innerHTML = `<div style="font-size:13px;font-weight:600;color:${CC.text};margin-bottom:4px;padding:0 4px;">Skills</div>`;

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

  wrapper.addEventListener('keydown', (e) => onSkillKeydown(panel, e));
  panel._skillListWrapper = wrapper;
  panel._outputEl.appendChild(wrapper);
  panel._scrollBottom();
  refreshSkillRows(panel);
  // Focus wrapper so keyboard nav works (input is hidden in skills mode)
  setTimeout(() => wrapper.focus(), 50);
  // Focus the list so keyboard nav works (input is hidden in skills mode)
  setTimeout(() => wrapper.focus(), 50);
}

export function onSkillKeydown(panel: any, e: KeyboardEvent): void {
  // Install mode handled separately
  if (panel._installMode) {
    if (e.key === 'Escape') {
      e.preventDefault(); e.stopPropagation();
      panel._installMode = false;
      refreshSkillRows(panel);
      setTimeout(() => panel._skillListWrapper?.focus(), 0);
    }
    return;
  }

  // Level 3: full body view — only Esc → back to info
  if (panel._fullBodyIdx !== -1) {
    if (e.key === 'Escape') {
      e.preventDefault(); e.stopPropagation();
      panel._fullBodyIdx = -1;
      refreshSkillRows(panel);
      setTimeout(() => panel._skillListWrapper?.focus(), 0);
    }
    return;
  }

  // Level 2: info view — Enter → full body, Esc → list
  if (panel._expandedIdx !== -1) {
    if (e.key === 'Enter') {
      e.preventDefault(); e.stopPropagation();
      panel._fullBodyIdx = panel._expandedIdx;
      refreshSkillRows(panel);
      setTimeout(() => panel._skillListWrapper?.focus(), 0);
      return;
    }
    if (e.key === 'Escape') {
      e.preventDefault(); e.stopPropagation();
      panel._expandedIdx = -1;
      panel._fullBodyIdx = -1;
      refreshSkillRows(panel);
      setTimeout(() => panel._skillListWrapper?.focus(), 0);
    }
    return;
  }

  const skills = panel._skillData;

  // Allow install + exit even when list is empty
  if (!skills.length) {
    if (e.key === 'i') {
      e.preventDefault(); e.stopPropagation();
      panel._installMode = true;
      panel._installError = '';
      refreshSkillRows(panel);
    } else if (e.key === 'Escape') {
      e.preventDefault(); e.stopPropagation();
      exitSkillsMode(panel);
    }
    return;
  }

  switch (e.key) {
    case 'i':
      // Install — show inline path input
      e.preventDefault(); e.stopPropagation();
      panel._installMode = true;
      panel._installError = '';
      refreshSkillRows(panel);
      // Focus the input after render
      setTimeout(() => {
        const inp = panel._skillListWrapper?.querySelector('.skillbot-install-input') as HTMLInputElement;
        inp?.focus();
      }, 50);
      break;
    case 'd':
      // Uninstall — requires double-tap for safety
      e.preventDefault(); e.stopPropagation();
      const toRemove = skills[panel._skillSelectedIdx];
      if (!toRemove) break;
      // Show confirmation hint
      const hintEl = panel._skillListWrapper?.querySelector('.skillbot-skill-hint') as HTMLElement | null;
      if (hintEl) {
        hintEl.textContent = `Press d again to confirm uninstall of "${toRemove.name}" (any other key to cancel)`;
        hintEl.style.color = 'rgb(220,120,100)';
      }
      // Wait for second keypress (auto-cancel after 3s)
      let cancelled = false;
      const cancelTimer = setTimeout(() => {
        cancelled = true;
        panel._skillListWrapper?.removeEventListener('keydown', onConfirm);
        if (hintEl) { hintEl.style.color = ''; }
        refreshSkillRows(panel);
      }, 3000);
      const onConfirm = (e2: KeyboardEvent) => {
        if (cancelled) return;
        clearTimeout(cancelTimer);
        panel._skillListWrapper?.removeEventListener('keydown', onConfirm);
        if (hintEl) { hintEl.style.color = ''; }
        if (e2.key === 'd') {
          if (panel._kernel) {
            panel._kernel.requestExecute({
              code: `get_ipython().user_ns['_panel_input'](${JSON.stringify('/skills uninstall ' + toRemove.name)})`,
              store_history: false,
            });
          }
          panel._skillData.splice(panel._skillSelectedIdx, 1);
          panel._skillSelectedIdx = Math.min(panel._skillSelectedIdx, panel._skillData.length - 1);
          refreshSkillRows(panel);
        } else {
          refreshSkillRows(panel); // reset hint
        }
      };
      setTimeout(() => {
        panel._skillListWrapper?.addEventListener('keydown', onConfirm, { once: false });
      }, 0);
      break;
    case 'Tab':
    case 'ArrowDown':
      e.preventDefault(); e.stopPropagation();
      panel._skillSelectedIdx = Math.min(skills.length - 1, panel._skillSelectedIdx + 1);
      refreshSkillRows(panel);
      break;
    case 'ArrowUp':
      e.preventDefault(); e.stopPropagation();
      panel._skillSelectedIdx = Math.max(0, panel._skillSelectedIdx - 1);
      refreshSkillRows(panel);
      break;
    case 'Enter':
      e.preventDefault(); e.stopPropagation();
      panel._expandedIdx = panel._skillSelectedIdx;
      refreshSkillRows(panel);
      break;
    case ' ':
      e.preventDefault(); e.stopPropagation();
      const s = skills[panel._skillSelectedIdx];
      if (s && panel._kernel) {
        s.enabled = !s.enabled;
        refreshSkillRows(panel);
        panel._kernel.requestExecute({
          code: `get_ipython().user_ns['_panel_input'](${JSON.stringify('/skills toggle ' + s.name)})`,
          store_history: false,
        });
      }
      break;
    case 'Escape':
      e.preventDefault(); e.stopPropagation();
      exitSkillsMode(panel);
      break;
  }
}

export function refreshSkillRows(panel: any): void {
  const listEl = panel._skillListWrapper?.querySelector('.skillbot-skill-items') as HTMLElement;
  if (!listEl) return;
  listEl.innerHTML = '';
  panel._skillRows = [];

  // Empty state in list area
  if (!panel._installMode && panel._skillData.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = `padding:12px 4px;font-size:12px;color:rgb(120,120,120);text-align:center;`;
    empty.textContent = 'No skills installed';
    listEl.appendChild(empty);
  }

  // Install mode: show input row
  if (panel._installMode) {
    const row = document.createElement('div');
    row.style.cssText = `padding:4px;display:flex;gap:6px;align-items:center;`;
    const input = document.createElement('input');
    input.className = 'skillbot-install-input';
    input.type = 'text';
    input.placeholder = 'path/to/skill.zip';
    input.style.cssText = `flex:1;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:${CC.text};padding:4px 8px;border-radius:3px;font-size:12px;outline:none;`;
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault(); e.stopPropagation();
        const path = input.value.trim();
        if (path && panel._kernel) {
          panel._kernel.requestExecute({
            code: `get_ipython().user_ns['_panel_input'](${JSON.stringify('/skills install ' + path)})`,
            store_history: false,
          });
        }
        // Close input, wait for skill_list refresh
        panel._installMode = false;
        refreshSkillRows(panel);
        setTimeout(() => panel._skillListWrapper?.focus(), 0);
      }
      if (e.key === 'Escape') {
        e.preventDefault(); e.stopPropagation();
        panel._installMode = false;
        refreshSkillRows(panel);
        setTimeout(() => panel._skillListWrapper?.focus(), 0);
      }
    });
    row.appendChild(input);
    const label = document.createElement('span');
    label.style.cssText = `font-size:10px;color:rgb(140,140,140);white-space:nowrap;`;
    label.textContent = 'Enter to install';
    row.appendChild(label);
    listEl.appendChild(row);
    // Show last error
    if (panel._installError) {
      const errRow = document.createElement('div');
      errRow.style.cssText = `padding:4px;font-size:11px;color:rgb(220,120,100);`;
      errRow.textContent = panel._installError;
      listEl.appendChild(errRow);
    }
  }
  panel._skillData.forEach((s: {name: string, description: string, enabled: boolean, body: string}, i: number) => {
    const selected = i === panel._skillSelectedIdx;
    const expanded = i === panel._expandedIdx;
    const row = document.createElement('div');
    row.style.cssText = `padding:2px 4px;border-radius:3px;background:${selected ? 'rgba(255,255,255,0.08)' : ''};`;

    const header = document.createElement('div');
    header.style.cssText = `display:flex;align-items:center;gap:8px;cursor:pointer;`;
    const dot = s.enabled
      ? `<span style="color:rgb(100,200,100);font-size:14px;">●</span>`
      : `<span style="color:rgb(200,100,100);font-size:14px;">●</span>`;
    const status = s.enabled ? 'enabled' : 'disabled';
    const statusColor = s.enabled ? 'rgb(100,200,100)' : 'rgb(200,100,100)';
    header.innerHTML = `${dot} <span style="color:${CC.text};font-size:12px;">${panel._esc(s.name)}</span> <span style="color:${statusColor};font-size:10px;margin-left:auto;">${status}</span>`;
    row.appendChild(header);

    if (expanded) {
      const showFull = panel._fullBodyIdx === i;
      const detail = document.createElement('div');
      detail.style.cssText = `margin:6px 0 4px 22px;font-size:11px;color:rgb(180,180,180);line-height:1.5;`;
      if (showFull) {
        // Level 3: full SKILL.md body
        detail.innerHTML = `<div style="color:${CC.text};background:rgba(255,255,255,0.04);padding:8px;border-radius:3px;max-height:350px;overflow-y:auto;white-space:pre-wrap;font-size:11px;line-height:1.4;">${panel._esc(s.body || '')}</div>`;
      } else {
        // Level 2: info view (description + truncated body)
        detail.innerHTML = `<div style="margin-bottom:4px;">${panel._esc(s.description)}</div>`;
        if (s.body) {
          const bodyText = s.body.slice(0, 1000);
          detail.innerHTML += `<div style="color:${CC.text};background:rgba(255,255,255,0.03);padding:6px;border-radius:3px;max-height:150px;overflow-y:auto;white-space:pre-wrap;font-size:11px;">${panel._esc(bodyText)}${s.body.length > 1000 ? '...' : ''}</div>`;
        }
      }
      row.appendChild(detail);
    }
    listEl.appendChild(row);
    panel._skillRows.push(row);
  });

  const hintEl = panel._skillListWrapper?.querySelector('.skillbot-skill-hint');
  if (hintEl) {
    if (panel._installMode) {
      hintEl.textContent = 'Enter install path to skill.zip  Esc cancel';
    } else if (panel._skillData.length === 0) {
      hintEl.textContent = 'Press i to install from .zip  Esc close';
    } else if (panel._fullBodyIdx !== -1) {
      hintEl.textContent = 'Esc back to info';
    } else if (panel._expandedIdx !== -1) {
      hintEl.textContent = 'Enter full body  Esc back to list';
    } else {
      hintEl.textContent = '↑↓ select  Enter details  Space toggle  d uninstall  i install  Esc close';
    }
  }
}

export function renderSkillInfo(panel: any, skill: {name: string, description: string, enabled: boolean, body: string, path: string}): void {
  const wrapper = document.createElement('div');
  wrapper.className = 'skillbot-skill-info';

  const dot = skill.enabled
    ? `<span style="color:rgb(100,200,100);font-size:16px;">●</span>`
    : `<span style="color:rgb(200,100,100);font-size:16px;">●</span>`;

  const header = document.createElement('div');
  header.style.cssText = `font-size:14px;font-weight:600;color:${CC.text};margin-bottom:4px;`;
  header.innerHTML = `${dot} ${panel._esc(skill.name)}`;

  const meta = document.createElement('div');
  meta.style.cssText = `font-size:12px;color:rgb(180,180,180);margin-bottom:8px;line-height:1.5;`;
  meta.innerHTML = `
    ${panel._esc(skill.description)}<br>
    <span style="color:rgb(140,140,140);">Status:</span> ${skill.enabled ? 'enabled' : 'disabled'}<br>
    <span style="color:rgb(140,140,140);">Path:</span> ${panel._esc(skill.path)}
  `;

  const bodyText = (skill.body || '').slice(0, 1500);
  const bodyWrap = document.createElement('div');
  bodyWrap.style.cssText = `font-size:12px;color:${CC.text};background:rgba(255,255,255,0.04);padding:8px;border-radius:4px;max-height:200px;overflow-y:auto;white-space:pre-wrap;line-height:1.4;`;
  bodyWrap.textContent = bodyText;
  if ((skill.body || '').length > 1500) {
    bodyWrap.textContent += '\n\n... (truncated)';
  }

  wrapper.appendChild(header);
  wrapper.appendChild(meta);
  wrapper.appendChild(bodyWrap);
  panel._appendToBlock(wrapper);
}
