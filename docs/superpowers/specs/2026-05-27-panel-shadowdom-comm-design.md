# TUI Panel: Shadow DOM + Frontend Comm

**Date**: 2026-05-27
**Status**: Design
**Context**: Right-side Agent TUI panel in JupyterLab. Current implementation works functionally but has two recurring problems: (1) CSS colors overridden by JupyterLab stylesheet, (2) comm registration race condition when Python opens comm before frontend registers target.

## Problem

### CSS Leakage

JupyterLab's stylesheet (`.lm-Widget`, `.jp-*`) overrides panel text colors. Inline `style.color` and `!important` partially mitigated this, but the root cause — shared CSS context — means any new JupyterLab rule can break the panel.

### Comm Race

Current comm flow:

```
Python:  create_comm("skillbot:tui") → comm.open()   [step 1]
Frontend: kernel.registerCommTarget("skillbot:tui")    [step 2, may happen after step 1]
```

If step 1 runs before step 2, the `comm_open` message is dropped. The `kernelChanged` listener partially fixed this but the race remains for edge cases (kernel restart, delayed extension load).

## Solution

### Shadow DOM Isolation

Wrap all panel content inside `this.node.attachShadow({mode: 'open'})`. CSS inside shadowRoot is completely isolated from the parent document — JupyterLab styles cannot penetrate, panel styles cannot leak out.

```
AgentPanel.node (Light DOM, min style only)
  └─ shadowRoot
       ├─ <style>  /* all Claude Code TUI CSS, no !important needed */
       ├─ <div class="output">
       ├─ <div class="status">
       └─ <div class="input-wrapper">
```

Input focus, keyboard events, and scroll work identically inside Shadow DOM.

### Frontend-Initiated Comm

Reverse the comm direction so the frontend always creates the comm:

```
Frontend: comm = kernel.createComm("skillbot:tui")
          comm.open()
          comm.onMsg = handler           [handler registered BEFORE open completes]

Python:   shell.kernel.comm_manager.register_target("skillbot:tui", on_comm)
```

Since `createComm` is called from `connectKernel` (which only fires when kernel is available), there is no race. The handler is always registered before the comm is opened.

## File Changes

| File | Change |
|------|--------|
| `src/jupyter/extension/src/panel.ts` | Shadow DOM: `attachShadow`, `<style>` inside shadowRoot, render methods target `shadowRoot` instead of `this.node`. Comm: `kernel.createComm(TARGET)` replaces `kernel.registerCommTarget`. Remove all `!important` and inline `style.color` workarounds. |
| `src/jupyter/panel.py` | Replace `create_comm(TARGET)` + `comm.open()` with `shell.kernel.comm_manager.register_target(TARGET, callback)`. Store comm reference in callback. `send_to_panel` unchanged. |

## Verification

1. `./scripts/jupyter.sh --rebuild`
2. Open JupyterLab, hard refresh (Cmd+Shift+R)
3. Verify colors are correct (light text on dark bg) without `!important` in styles
4. Verify `%load_ext jupyter` → comm opens → console shows no "Comm not found" errors
5. Type prompt → verify streaming output, spinner, message blocks
6. `/clear` → verify output clears
7. Kernel restart → verify comm reconnects automatically
