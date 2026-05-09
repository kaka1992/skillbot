export interface SessionInfo {
  session_id: string;
  messages: number;
  created_at: number;
}

export interface HistoryMessage {
  role: string;
  content: string;
  time: number;
}

export interface SkillInfo {
  name: string;
  description: string;
  path: string;
}

export interface SkillDetail {
  name: string;
  description: string;
  body: string;
}
