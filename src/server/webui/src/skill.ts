import { getSkill, getSkills } from "./api";
import type { SkillDetail, SkillInfo } from "./types";

export class SkillPanel {
  private el: HTMLElement;

  constructor(el: HTMLElement) {
    this.el = el;
    this.render();
    this.refresh();
  }

  private render(): void {
    this.el.innerHTML = `
      <div class="panel-header"><span>Skills</span></div>
      <div id="skill-list"></div>
      <div id="skill-modal" class="modal-overlay">
        <div class="modal-panel">
          <div class="modal-panel-header">
            <span id="skill-modal-title"></span>
            <button id="skill-modal-close">&times;</button>
          </div>
          <div class="modal-panel-body" id="skill-modal-body"></div>
        </div>
      </div>
    `;
    document.getElementById("skill-modal-close")!.onclick = () => {
      document.getElementById("skill-modal")!.classList.remove("open");
    };
    document.getElementById("skill-modal")!.onclick = (e) => {
      if (e.target === document.getElementById("skill-modal")) {
        document.getElementById("skill-modal")!.classList.remove("open");
      }
    };
  }

  async refresh(): Promise<void> {
    const list = document.getElementById("skill-list")!;
    try {
      const skills: SkillInfo[] = await getSkills();
      if (skills.length === 0) {
        list.innerHTML = `<div class="empty-hint"><div class="empty-icon">&#9881;</div>No skills loaded</div>`;
        return;
      }
      list.innerHTML = skills.map(s => `
        <div class="skill-item" data-name="${s.name}">
          <span class="skill-name">${s.name}</span>
          <span class="skill-desc">${s.description.slice(0, 60)}</span>
        </div>
      `).join("");

      list.querySelectorAll<HTMLElement>(".skill-item").forEach(el => {
        el.onclick = () => this.showSkill(el.dataset.name!);
      });
    } catch {
      list.innerHTML = `<div class="empty-hint">server unreachable</div>`;
    }
  }

  private async showSkill(name: string): Promise<void> {
    try {
      const detail: SkillDetail = await getSkill(name);
      document.getElementById("skill-modal-title")!.textContent = detail.name;
      document.getElementById("skill-modal-body")!.textContent = detail.body;
      document.getElementById("skill-modal")!.classList.add("open");
    } catch { /* skip */ }
  }
}
