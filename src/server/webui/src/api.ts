import type { HistoryMessage, SessionInfo, SkillDetail, SkillInfo } from "./types";

declare var API_BASE: string | undefined;
const BASE = (typeof API_BASE !== "undefined" ? API_BASE : "") || "http://127.0.0.1:9000";

export async function createSession(): Promise<SessionInfo> {
  const r = await fetch(`${BASE}/sessions`, { method: "POST" });
  return r.json();
}

export async function listSessions(): Promise<SessionInfo[]> {
  const r = await fetch(`${BASE}/sessions`);
  return r.json();
}

export async function deleteSession(sid: string): Promise<void> {
  await fetch(`${BASE}/sessions/${sid}`, { method: "DELETE" });
}

export async function getHistory(sid: string): Promise<HistoryMessage[]> {
  const r = await fetch(`${BASE}/sessions/${sid}/history`);
  return r.json();
}

export async function getSkills(): Promise<SkillInfo[]> {
  const r = await fetch(`${BASE}/skills`);
  return r.json();
}

export async function getSkill(name: string): Promise<SkillDetail> {
  const r = await fetch(`${BASE}/skills/${name}`);
  return r.json();
}

export function streamChat(
  sid: string,
  message: string,
  onToken: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
): AbortController {
  const ctrl = new AbortController();
  fetch(`${BASE}/sessions/${sid}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal: ctrl.signal,
  }).then(async (resp) => {
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const reader = resp.body?.getReader();
    if (!reader) return;
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.text) onToken(data.text);
          else if (data.type === "done") onDone();
          else if (data.type === "error") onError(data.error);
        } catch { /* skip parse errors */ }
      }
    }
  }).catch(err => {
    if (err.name !== "AbortError") onError(String(err));
  });
  return ctrl;
}
