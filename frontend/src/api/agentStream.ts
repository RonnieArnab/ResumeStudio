import { apiClient } from "./client";
import { streamSSE } from "./sse";
import type { AgentEvent, StagedEditSummary } from "../types/agent";
import type { CompileResponse } from "../types/resume";

export function streamSectionEdit(sessionId: string, sectionId: string, instruction: string, onEvent: (event: AgentEvent) => void): Promise<void> {
  return streamSSE<AgentEvent>(`/api/agent/${sessionId}/section-edit`, { section_id: sectionId, instruction }, onEvent);
}

export function getStagedDiff(sessionId: string, sectionId: string): Promise<StagedEditSummary> {
  return apiClient.get<StagedEditSummary>(`/api/agent/${sessionId}/diff/${sectionId}`);
}

export function listStagedDiffs(sessionId: string): Promise<StagedEditSummary[]> {
  return apiClient.get<StagedEditSummary[]>(`/api/agent/${sessionId}/diff`);
}

export function applyDiff(sessionId: string, sectionIds: string[]): Promise<CompileResponse> {
  return apiClient.post<CompileResponse>(`/api/agent/${sessionId}/diff/apply`, { section_ids: sectionIds });
}

export function rejectDiff(sessionId: string, sectionIds: string[]): Promise<{ rejected: string[] }> {
  return apiClient.post<{ rejected: string[] }>(`/api/agent/${sessionId}/diff/reject`, { section_ids: sectionIds });
}
