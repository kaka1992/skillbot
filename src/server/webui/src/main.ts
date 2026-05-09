import { ChatView } from "./chat";
import { SessionPanel } from "./session";
import { SkillPanel } from "./skill";

function init(): void {
  const chatView = new ChatView(document.getElementById("chat-area")!);

  const sessionPanel = new SessionPanel(
    document.getElementById("sidebar-top")!,
    (sid: string) => chatView.loadSession(sid),
  );

  // refresh session list when messages are sent/received
  chatView.onActivity = () => { sessionPanel.refresh(); };

  new SkillPanel(document.getElementById("sidebar-bottom")!);

  // mobile sidebar toggle
  const sidebar = document.getElementById("sidebar")!;
  const btnToggle = document.getElementById("btn-toggle-sidebar")!;
  btnToggle.onclick = () => sidebar.classList.toggle("collapsed");
}

document.addEventListener("DOMContentLoaded", init);
