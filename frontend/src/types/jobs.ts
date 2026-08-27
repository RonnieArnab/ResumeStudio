export type Provider = "greenhouse" | "lever" | "ashby" | "linkedin" | "wellfound" | "other";

export type SourceKind = "board" | "search";

export const CONNECTED_PROVIDERS = ["linkedin", "wellfound"] as const;

export interface RegistryEntry {
  name: string;
  provider: Provider;
  slug: string;
}

export interface ConnectionStatus {
  provider: Provider;
  connected: boolean;
  since: string | null;
}

export type FieldKind =
  | "text"
  | "email"
  | "tel"
  | "url"
  | "number"
  | "textarea"
  | "select"
  | "file"
  | "checkbox"
  | "radio"
  | "unknown";

export type FieldSource = "profile" | "generated" | "default" | "empty" | "user";

export type RunStatus =
  | "filling"
  | "ready_for_review"
  | "submitting"
  | "submitted"
  | "failed"
  | "cancelled";

export interface BoardSource {
  id: string;
  provider: Provider;
  kind: SourceKind;
  slug: string;
  query: string;
  location: string;
  label: string;
  added_at: string;
}

export interface JobPosting {
  id: string;
  provider: Provider;
  company: string;
  title: string;
  location: string;
  team: string | null;
  remote: boolean;
  url: string;
  apply_url: string;
  description_text: string;
  posted_at: string | null;
}

export interface MatchResult {
  job_id: string;
  score: number;
  verdict: string;
  summary: string;
  matched_requirements: string[];
  missing_requirements: string[];
  error: string | null;
}

export interface RankedJob {
  job: JobPosting;
  match: MatchResult | null;
}

export interface ApplicantProfile {
  full_name: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  location: string;
  linkedin_url: string;
  github_url: string;
  portfolio_url: string;
  work_authorization: string;
  requires_sponsorship: boolean | null;
  years_experience: string;
  pronouns: string;
  cover_letter_blurb: string;
  default_answers: Record<string, string>;
  resume_pdf_path: string | null;
  resume_source_label: string | null;
  updated_at: string | null;
}

export interface FormField {
  selector: string;
  label: string;
  kind: FieldKind;
  options: string[];
  required: boolean;
  value: string;
  source: FieldSource;
}

export interface ApplyRunView {
  run_id: string;
  job_id: string;
  job_title: string;
  company: string;
  status: RunStatus;
  fields: FormField[];
  screenshot_url: string;
  captcha_detected: boolean;
  manual_only: boolean;
  notes: string[];
  confirmation_text: string | null;
  created_at: string;
}

export type CrawlEvent =
  | { type: "board_started"; provider: Provider; slug: string; label: string }
  | { type: "board_error"; slug: string; error: string }
  | { type: "jobs_found"; slug: string; count: number }
  | { type: "job_scored"; job_id: string; title: string; score: number | null; verdict?: string; skipped?: boolean; capped?: boolean }
  | { type: "done"; jobs: number; scored: number; message?: string };
