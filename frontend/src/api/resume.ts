import { apiClient } from "./client";
import type { CompileResponse, ResumeSession } from "../types/resume";

export function uploadResume(file: File): Promise<ResumeSession> {
  const form = new FormData();
  form.append("file", file);
  return apiClient.postForm<ResumeSession>("/api/resume/upload", form);
}

export function getResume(sessionId: string): Promise<ResumeSession> {
  return apiClient.get<ResumeSession>(`/api/resume/${sessionId}`);
}

export function compileResume(sessionId: string): Promise<CompileResponse> {
  return apiClient.post<CompileResponse>(`/api/resume/${sessionId}/compile`);
}

export function addResumeSection(sessionId: string, title: string): Promise<ResumeSession> {
  return apiClient.post<ResumeSession>(`/api/resume/${sessionId}/sections`, { title });
}

export function deleteResumeSection(sessionId: string, sectionId: string): Promise<ResumeSession> {
  return apiClient.del<ResumeSession>(`/api/resume/${sessionId}/sections/${sectionId}`);
}
