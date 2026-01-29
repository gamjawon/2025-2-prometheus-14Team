export type Role = "user" | "assistant";

export type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  createdAt: number;
};

export type Thread = {
  id: string;
  title: string;
  updatedAt: number;
};

export type SafetyPayload = {
  title: string;
  description: string;
  bullets: string[];
};
