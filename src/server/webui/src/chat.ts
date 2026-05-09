import { getHistory, streamChat } from "./api";

export class ChatView {
  private msgEl: HTMLElement;
  private inputEl: HTMLTextAreaElement;
  private sendBtn: HTMLButtonElement;
  private indicatorEl: HTMLElement;
  private sid: string | null = null;
  private ctrl: AbortController | null = null;
  private welcomeEl: HTMLElement | null = null;

  constructor(container: HTMLElement) {
    container.innerHTML = `
      <div id="chat-toolbar">
        <button id="btn-toggle-sidebar" title="Toggle sidebar">&#9776;</button>
        <div id="session-indicator">No session selected</div>
      </div>
      <div id="chat-messages"></div>
      <div class="chat-input-area">
        <textarea id="chat-input" placeholder="Type a message... (Shift+Enter to break)" rows="2" disabled></textarea>
        <button id="btn-send" title="Send" disabled>&#9654;</button>
      </div>
    `;
    this.msgEl = document.getElementById("chat-messages")!;
    this.inputEl = document.getElementById("chat-input") as HTMLTextAreaElement;
    this.sendBtn = document.getElementById("btn-send") as HTMLButtonElement;
    this.indicatorEl = document.getElementById("session-indicator")!;

    this.showWelcome();

    this.inputEl.onkeydown = (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); this.doSend(); }
    };
    this.sendBtn.onclick = () => this.doSend();

    // mobile: collapse sidebar when a session is loaded
    const btnToggle = document.getElementById("btn-toggle-sidebar")!;
    btnToggle.onclick = () => document.getElementById("sidebar")!.classList.toggle("collapsed");
  }

  private showWelcome(): void {
    this.msgEl.innerHTML = `
      <div class="welcome-screen">
        <div class="logo">&gt; claude _</div>
        <div class="hint">Create or select a session to start.<br>Messages stream token-by-token via SSE.</div>
      </div>
    `;
  }

  async loadSession(sid: string): Promise<void> {
    this.sid = sid;
    this.indicatorEl.innerHTML = `Session <span>${sid.slice(0, 12)}</span>`;
    this.inputEl.disabled = false;
    this.sendBtn.disabled = false;
    this.msgEl.innerHTML = "";

    try {
      const msgs = await getHistory(sid);
      if (msgs.length === 0) {
        this.showWelcome();
        return;
      }
      for (const m of msgs) {
        this.addMessage(m.role, m.content);
      }
    } catch {
      this.showWelcome();
    }
    this.scrollBottom();
  }

  private doSend(): void {
    if (!this.sid || this.ctrl) return;
    const text = this.inputEl.value.trim();
    if (!text) return;
    this.inputEl.value = "";
    this.inputEl.disabled = true;
    this.sendBtn.disabled = true;

    // clear welcome
    if (this.msgEl.querySelector(".welcome-screen")) {
      this.msgEl.innerHTML = "";
    }

    this.addMessage("user", text);

    // assistant message with streaming indicator
    const asstDiv = document.createElement("div");
    asstDiv.className = "message assistant";
    asstDiv.innerHTML = `
      <span class="role">Claude</span>
      <div class="bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>
    `;
    this.msgEl.appendChild(asstDiv);
    const bubble = asstDiv.querySelector(".bubble")!;
    this.scrollBottom();

    this.ctrl = streamChat(
      this.sid, text,
      (token) => {
        // replace dots on first token
        if (bubble.querySelector(".typing-dots")) {
          bubble.textContent = "";
        }
        bubble.textContent += token;
        this.scrollBottom();
      },
      () => {
        this.ctrl = null;
        this.inputEl.disabled = false;
        this.sendBtn.disabled = false;
        this.inputEl.focus();
        if (!bubble.textContent) bubble.innerHTML = `<span style="color:var(--text-muted)">(empty response)</span>`;
      },
      (err) => {
        if (bubble.querySelector(".typing-dots")) bubble.textContent = "";
        bubble.innerHTML += `<div style="color:var(--red);margin-top:6px;font-size:12px">Error: ${err}</div>`;
        this.ctrl = null;
        this.inputEl.disabled = false;
        this.sendBtn.disabled = false;
      },
    );
  }

  private addMessage(role: string, content: string): void {
    const label = role === "user" ? "You" : "Claude";
    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.innerHTML = `<span class="role">${label}</span><div class="bubble"></div>`;
    div.querySelector(".bubble")!.textContent = content;
    this.msgEl.appendChild(div);
  }

  private scrollBottom(): void {
    this.msgEl.scrollTop = this.msgEl.scrollHeight;
  }
}
