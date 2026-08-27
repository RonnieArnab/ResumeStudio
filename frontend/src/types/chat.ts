export interface ChatMessageSummary {
  role: "user" | "agent";
  text: string;
  created_at: string;
}
