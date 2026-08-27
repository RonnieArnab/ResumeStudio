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
