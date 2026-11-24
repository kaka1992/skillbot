// ---------------------------------------------------------------------------
// Skills Gallery — shadow-DOM styles
// ---------------------------------------------------------------------------
// The gallery lives in the LEFT shell area but, like the right-hand Agent
// Panel, renders inside its own shadow root so none of these rules leak into
// JupyterLab's native chrome (and vice-versa). Colours come from the shared
// `CC` palette so the two skillbot surfaces stay visually consistent.
// ---------------------------------------------------------------------------
import { CC } from './panelStyles';

export const GALLERY_STYLES = `
:host {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 240px;
  background: ${CC.bg};
  color: ${CC.text};
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 12.5px;
  line-height: 1.5;
}

/* ---- header ---- */
.gallery-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px 10px;
  border-bottom: 1px solid ${CC.border};
  flex-shrink: 0;
}
.gallery-avatar {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: #08201f;
  background: linear-gradient(135deg, ${CC.accent}, ${CC.brand});
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  flex-shrink: 0;
}
.gallery-title {
  font-size: 13px;
  font-weight: 600;
  color: ${CC.text};
  letter-spacing: 0.02em;
}

/* ---- tab strip (Skills / Knowledge) ---- */
.gallery-tabs {
  display: flex;
  gap: 4px;
  padding: 8px 10px 0;
  flex-shrink: 0;
}
.gallery-tab {
  flex: 1;
  text-align: center;
  padding: 6px 8px;
  font-size: 12px;
  font-weight: 600;
  color: ${CC.subtle};
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px 8px 0 0;
  cursor: pointer;
  user-select: none;
  transition: color 0.15s, background 0.15s;
}
.gallery-tab:hover { color: ${CC.inactive}; }
.gallery-tab.active {
  color: ${CC.text};
  background: ${CC.surface};
  box-shadow: inset 0 -2px 0 ${CC.accent};
}

/* ---- scrollable body ---- */
.gallery-body {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}
.gallery-body::-webkit-scrollbar { width: 7px; }
.gallery-body::-webkit-scrollbar-thumb { background: #33333d; border-radius: 4px; }
.gallery-body::-webkit-scrollbar-track { background: transparent; }

.gallery-page { display: none; }
.gallery-page.active { display: block; }

/* ---- cards ---- */
.gallery-card {
  background: ${CC.surface};
  border: 1px solid ${CC.border};
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  transition: border-color 0.15s, transform 0.05s;
}
.gallery-card.clickable { cursor: pointer; }
.gallery-card.clickable:hover {
  border-color: rgba(0,200,200,0.4);
}
.gallery-card.clickable:active { transform: translateY(1px); }

.gallery-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.gallery-card-name {
  font-size: 12.5px;
  font-weight: 600;
  color: ${CC.text};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gallery-card-desc {
  font-size: 11.5px;
  color: ${CC.inactive};
  line-height: 1.45;
}
.gallery-card-meta {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.gallery-chip {
  font-size: 10.5px;
  font-weight: 600;
  color: ${CC.subtle};
  background: rgba(255,255,255,0.04);
  border: 1px solid ${CC.border};
  border-radius: 999px;
  padding: 1px 8px;
}

/* enabled / disabled status dot on skill cards */
.gallery-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: ${CC.subtle};
}
.gallery-status.on {
  background: ${CC.success};
  box-shadow: 0 0 0 3px rgba(90,205,120,0.15);
}

/* category header inside the knowledge page */
.gallery-cat {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: ${CC.accent};
  margin: 12px 2px 6px;
}
.gallery-cat:first-child { margin-top: 2px; }

/* ---- empty / loading state ---- */
.gallery-empty {
  padding: 24px 14px;
  text-align: center;
  color: ${CC.subtle};
  font-size: 12px;
  line-height: 1.6;
}
`;
