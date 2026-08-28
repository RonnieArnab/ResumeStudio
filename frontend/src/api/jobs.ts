import { apiClient } from "./client";
import { streamSSE } from "./sse";
import type {
  ApplicantProfile,
  Application,
  ApplyRunView,
  BoardSource,
  CdpStatus,
  ConnectionStatus,
  CrawlEvent,
  Provider,
  RankedJob,
  RegistryEntry,
  TrackerStatus,
} from "../types/jobs";

export interface JobFilters {
  min_score?: number;
  location_contains?: string;
  provider?: string;
  remote_only?: boolean;
  posted_within_days?: number | null;
  target_years_experience?: number | null;
}

export const jobsApi = {
  listSources: () => apiClient.get<BoardSource[]>("/api/jobs/sources"),

  addSource: (ref: string, label?: string) =>
    apiClient.post<BoardSource>("/api/jobs/sources", { ref, label: label ?? null }),

  addSearchSource: (provider: Provider, query: string, location: string) =>
    apiClient.post<BoardSource>("/api/jobs/sources", { provider, query, location: location || null }),

  removeSource: (sourceId: string) =>
    apiClient.del<{ removed: boolean }>(`/api/jobs/sources/${sourceId}`),

  searchRegistry: (q: string) =>
    apiClient.get<RegistryEntry[]>(`/api/jobs/registry?q=${encodeURIComponent(q)}`),

  listConnections: () => apiClient.get<ConnectionStatus[]>("/api/jobs/connect"),

  cdpStatus: () => apiClient.get<CdpStatus>("/api/jobs/cdp/status"),

  connectStart: (provider: Provider) =>
    apiClient.post<{ status: string }>(`/api/jobs/connect/${provider}/start`, undefined),

  connectFinish: (provider: Provider) =>
    apiClient.post<ConnectionStatus>(`/api/jobs/connect/${provider}/finish`, undefined),

  connectDelete: (provider: Provider) =>
    apiClient.del<{ removed: boolean }>(`/api/jobs/connect/${provider}`),

  crawl: (
    body: { resume_session_id?: string | null; resume_text?: string | null } & JobFilters,
    onEvent: (event: CrawlEvent) => void,
  ) => streamSSE<CrawlEvent>("/api/jobs/crawl", body, onEvent),

  listJobs: (filters: JobFilters = {}) => {
    const params = new URLSearchParams();
    if (filters.min_score) params.set("min_score", String(filters.min_score));
    if (filters.location_contains) params.set("location_contains", filters.location_contains);
    if (filters.provider) params.set("provider", filters.provider);
    if (filters.remote_only) params.set("remote_only", "true");
    if (filters.posted_within_days) params.set("posted_within_days", String(filters.posted_within_days));
    const qs = params.toString();
    return apiClient.get<RankedJob[]>(`/api/jobs${qs ? `?${qs}` : ""}`);
  },

  getJob: (jobId: string) => apiClient.get<RankedJob>(`/api/jobs/${encodeURIComponent(jobId)}`),

  getProfile: () => apiClient.get<ApplicantProfile>("/api/jobs/profile"),

  saveProfile: (profile: ApplicantProfile) =>
    apiClient.put<ApplicantProfile>("/api/jobs/profile", profile),

  setResumeFromSession: (resumeSessionId: string) =>
    apiClient.post<ApplicantProfile>("/api/jobs/profile/resume", { resume_session_id: resumeSessionId }),

  autofillProfile: (resumeSessionId: string, overwrite = false) =>
    apiClient.post<ApplicantProfile>("/api/jobs/profile/from-resume", {
      resume_session_id: resumeSessionId,
      overwrite,
    }),

  openLoginTab: (provider: string) =>
    apiClient.post<{ opened: string }>(`/api/jobs/connect/${provider}/open-login`, undefined),

  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.postForm<ApplicantProfile>("/api/jobs/profile/resume/upload", form);
  },

  prepareApply: (jobId: string, resumeSessionId?: string | null) =>
    apiClient.post<ApplyRunView>("/api/jobs/apply/prepare", {
      job_id: jobId,
      resume_session_id: resumeSessionId ?? null,
    }),

  openExternal: (jobId: string) =>
    apiClient.post<{ url: string }>("/api/jobs/apply/open-external", { job_id: jobId }),

  prepareApplyUrl: (url: string, title?: string, resumeSessionId?: string | null) =>
    apiClient.post<ApplyRunView>("/api/jobs/apply/prepare-url", {
      url,
      title: title || null,
      resume_session_id: resumeSessionId ?? null,
    }),

  editFields: (runId: string, overrides: Record<string, string>) =>
    apiClient.put<ApplyRunView>(`/api/jobs/apply/${runId}/fields`, { overrides }),

  submitApply: (runId: string) =>
    apiClient.post<ApplyRunView>(`/api/jobs/apply/${runId}/submit`, undefined),

  cancelApply: (runId: string) =>
    apiClient.post<{ status: string }>(`/api/jobs/apply/${runId}/cancel`, undefined),

  // ---- applied-jobs tracker ------------------------------------------------
  listApplications: () => apiClient.get<Application[]>("/api/jobs/applications"),

  addApplication: (body: Partial<Application>) =>
    apiClient.post<Application>("/api/jobs/applications", body),

  updateApplication: (id: string, body: { status?: TrackerStatus; notes?: string; company?: string; title?: string }) =>
    apiClient.patch<Application>(`/api/jobs/applications/${id}`, body),

  deleteApplication: (id: string) =>
    apiClient.del<{ removed: boolean }>(`/api/jobs/applications/${id}`),
};
