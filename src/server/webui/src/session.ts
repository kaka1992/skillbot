import { createSession, deleteSession, listSessions } from "./api";

export class SessionPanel {
  private el: HTMLElement;
  private onSelect: (sid: string) => void;

  constructor(el: HTMLElement, onSelect: (sid: string) => void) {
    this.el = el;
    this.onSelect = onSelect;
    this.render();
    this.refresh();
  }

  private render(): void {
    this.el.innerHTML = `
      <div class="panel-header">
        <span>Sessions</span>
        <button id="btn-new-session" title="New session">+</button>
      </div>
      <div id="session-list"></div>
    `;
    document.getElementById("btn-new-session")!.onclick = () => this.doCreate();
  }

  async refresh(): Promise<void> {
    const list = document.getElementById("session-list")!;
    try {
      const sessions = await listSessions();
      sessions.sort((a, b) => b.created_at - a.created_at);
      if (sessions.length === 0) {
        list.innerHTML = `<div class="empty-hint"><div class="empty-icon">&#9670;</div>No sessions yet</div>`;
        return;
      }
      list.innerHTML = sessions.map(s => `
        <div class="session-item" data-sid="${s.session_id}">
          <span class="session-name">${s.session_id.slice(0, 12)}</span>
          <span class="session-msg">${s.messages}</span>
          <button class="btn-del" data-sid="${s.session_id}" title="Delete">&times;</button>
        </div>
      `).join("");

      list.querySelectorAll<HTMLElement>(".session-item").forEach(el => {
        el.onclick = (e) => {
          if ((e.target as HTMLElement).classList.contains("btn-del")) return;
          list.querySelectorAll(".session-item").forEach(i => i.classList.remove("active"));
          el.classList.add("active");
          this.onSelect(el.dataset.sid!);
        };
      });
      list.querySelectorAll<HTMLButtonElement>(".btn-del").forEach(btn => {
        btn.onclick = async (e) => {
          e.stopPropagation();
          await deleteSession(btn.dataset.sid!);
          this.refresh();
        };
      });
    } catch {
      list.innerHTML = `<div class="empty-hint">server unreachable</div>`;
    }
  }

  private async doCreate(): Promise<void> {
    try {
      const s = await createSession();
      await this.refresh();
      this.onSelect(s.session_id);
      const items = document.querySelectorAll<HTMLElement>(".session-item");
      items.forEach(i => {
        if (i.dataset.sid === s.session_id) i.classList.add("active");
      });
    } catch { /* server error */ }
  }
}
