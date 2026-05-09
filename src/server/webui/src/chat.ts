import { getHistory, streamChat } from "./api";

interface Msg { role: string; content: string; }

interface SessionState {
  messages: Msg[];
  scrollTop: number;
  inputText: string;
}

export class ChatView {
  private msgEl: HTMLElement;
  private inputEl: HTMLTextAreaElement;
  private sendBtn: HTMLButtonElement;
  private indicatorEl: HTMLElement;
  private sid: string | null = null;
  private ctrl: AbortController | null = null;
  private messages: Msg[] = [];
  private sessions: Map<string, SessionState> = new Map();
  onActivity: (() => void) | null = null;  // called when messages change

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

    this.renderWelcome();

    this.inputEl.onkeydown = (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
        e.preventDefault(); this.doSend();
      }
    };
    this.sendBtn.onclick = () => this.doSend();

    const btnToggle = document.getElementById("btn-toggle-sidebar")!;
    btnToggle.onclick = () => document.getElementById("sidebar")!.classList.toggle("collapsed");
  }

  // ---- render ----

  private renderWelcome(): void {
    this.msgEl.innerHTML = `
      <div class="welcome-screen">
        <div class="logo">&gt; claude _</div>
        <div class="hint">Create or select a session to start.<br>Messages stream token-by-token via SSE.</div>
      </div>
    `;
  }

  private renderMessages(): void {
    this.msgEl.innerHTML = "";
    for (const m of this.messages) {
      this.appendMsgEl(m.role, m.content);
    }
    this.msgEl.scrollTop = this.msgEl.scrollHeight;
  }

  private appendMsgEl(role: string, content: string): HTMLElement {
    const label = role === "user" ? "You" : "Claude";
    const div = document.createElement("div");
    div.className = `message ${role}`;
    const body = content || `<div class="typing-dots"><span></span><span></span><span></span></div>`;
    div.innerHTML = `<span class="role">${label}</span><div class="bubble">${body}</div>`;
    this.msgEl.appendChild(div);
    return div.querySelector(".bubble")!;
  }

  // ---- session management ----

  async loadSession(sid: string): Promise<void> {
    // save current session: capture partial stream text, abort stream
    if (this.sid && this.sid !== sid) {
      this.captureStreamingText();
      if (this.ctrl) { this.ctrl.abort(); this.ctrl = null; }
      this.sessions.set(this.sid, {
        messages: this.messages.map(m => ({ ...m })),
        scrollTop: this.msgEl.scrollTop,
        inputText: this.inputEl.value,
      });
    }

    // restore target session
    const saved = this.sessions.get(sid);
    this.sid = sid;
    this.ctrl = null;
    this.indicatorEl.innerHTML = `Session <span>${sid.slice(0, 12)}</span>`;

    if (saved) {
      this.messages = saved.messages.map(m => ({ ...m }));
      this.inputEl.value = saved.inputText;
      this.renderMessages();
      this.msgEl.scrollTop = saved.scrollTop;
      this.setInputState(false);
      return;
    }

    // first load — fetch history from server
    this.messages = [];
    this.msgEl.innerHTML = "";
    this.setInputState(false);
    try {
      const msgs = await getHistory(sid);
      if (msgs.length === 0) {
        this.renderWelcome();
        return;
      }
      this.messages = msgs.map(m => ({ role: m.role, content: m.content }));
      this.renderMessages();
    } catch {
      this.renderWelcome();
    }
  }

  /** Read current DOM text into messages[last] for the active stream. */
  private captureStreamingText(): void {
    const last = this.messages[this.messages.length - 1];
    if (!last || last.role !== "assistant" || last.content) return;
    const bubbles = this.msgEl.querySelectorAll(".message.assistant .bubble");
    const domBubble = bubbles[bubbles.length - 1];
    if (domBubble && !domBubble.querySelector(".typing-dots")) {
      last.content = domBubble.textContent || "";
    }
    if (!last.content) last.content = "";
  }

  private setInputState(disabled: boolean): void {
    this.inputEl.disabled = disabled;
    this.sendBtn.disabled = disabled;
  }

  // ---- send ----

  private doSend(): void {
    if (!this.sid || this.ctrl) return;
    const text = this.inputEl.value.trim();
    if (!text) return;
    this.inputEl.value = "";

    this.messages.push({ role: "user", content: text });
    this.messages.push({ role: "assistant", content: "" });
    this.renderMessages();
    this.setInputState(true);

    const bubbles = this.msgEl.querySelectorAll(".message.assistant .bubble");
    const bubble = bubbles[bubbles.length - 1] as HTMLElement;
    const msgIdx = this.messages.length - 1;

    this.ctrl = streamChat(
      this.sid, text,
      (token) => {
        this.messages[msgIdx].content += token;
        if (bubble.querySelector(".typing-dots")) bubble.textContent = "";
        bubble.textContent += token;
        this.msgEl.scrollTop = this.msgEl.scrollHeight;
      },
      () => {
        this.ctrl = null;
        this.setInputState(false);
        this.inputEl.focus();
        const m = this.messages[msgIdx];
        if (!m.content) {
          m.content = "(empty response)";
          bubble.innerHTML = `<span style="color:var(--text-muted)">(empty response)</span>`;
        }
        this.saveSession();
        this.onActivity?.();
      },
      (err) => {
        this.messages[msgIdx].content += `\n[Error: ${err}]`;
        if (bubble.querySelector(".typing-dots")) bubble.textContent = "";
        bubble.innerHTML += `<div style="color:var(--red);margin-top:6px;font-size:12px">Error: ${err}</div>`;
        this.ctrl = null;
        this.setInputState(false);
        this.saveSession();
        this.onActivity?.();
      },
    );
  }

  private saveSession(): void {
    if (!this.sid) return;
    this.sessions.set(this.sid, {
      messages: this.messages.map(m => ({ ...m })),
      scrollTop: this.msgEl.scrollTop,
      inputText: this.inputEl.value,
    });
  }
}
