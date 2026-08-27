import { apiClient } from "./client";
import { streamSSE } from "./sse";
import type { AgentEvent } from "../types/agent";
import type { ChatMessageSummary } from "../types/chat";

export function streamChatMessage(sessionId: string, text: string, jobDescription: string | null, onEvent: (event: AgentEvent) => void): Promise<void> {
  return streamSSE<AgentEvent>(`/api/chat/${sessionId}/message`, { text, job_description: jobDescription }, onEvent);
}

export function getChatHistory(sessionId: string): Promise<ChatMessageSummary[]> {
  return apiClient.get<ChatMessageSummary[]>(`/api/chat/${sessionId}/history`);
}
