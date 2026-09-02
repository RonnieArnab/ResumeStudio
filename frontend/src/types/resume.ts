export interface SectionSummary {
  id: string;
  summary: string;
}

export interface SectionFragment {
  id: string;
  pdf_url: string;
}

export interface ResumeSession {
  session_id: string;
  latex: string;
  sections: SectionSummary[];
  pdf_url: string | null;
  section_fragments: SectionFragment[];
}

export interface LatexUpdateResult extends ResumeSession {
  compile_errors: string[];
}

export interface SectionBox {
  id: string;
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface CompileResponse {
  pdf_url: string | null;
  section_boxes: SectionBox[];
  section_fragments: SectionFragment[];
  validation_errors: string[];
}

export interface ScoreDimension {
  key: string;
  label: string;
  score: number;
  weight: number;
  note: string;
}

export interface KeywordAnalysis {
  coverage: number;
  matched: string[];
  partial: string[];
  missing: string[];
}

export type RequirementStatus = "met" | "partial" | "missing";

export interface RequirementMatch {
  requirement: string;
  status: RequirementStatus;
  evidence: string;
}

export type SuggestionPriority = "high" | "medium" | "low";

export interface MatchSuggestion {
  section: string;
  title: string;
  detail: string;
  priority: SuggestionPriority;
}

export interface MatchReport {
  overall_score: number;
  verdict: "strong" | "moderate" | "weak";
  headline: string;
  summary: string;
  dimensions: ScoreDimension[];
  keywords: KeywordAnalysis;
  requirements: RequirementMatch[];
  strengths: string[];
  gaps: string[];
  suggestions: MatchSuggestion[];
  jd_title: string;
  generated_at: string;
}
