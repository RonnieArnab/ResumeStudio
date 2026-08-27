export type AgentEvent =
  | { type: "tool_call"; name: string; arguments: Record<string, unknown> }
  | { type: "tool_result"; name: string; result: unknown }
  | { type: "section_proposed"; section_id: string }
  | { type: "validation_error"; errors: string[] }
  | { type: "done"; message: string }
  | { type: "error"; message: string };

export interface StagedEditSummary {
  section_id: string;
  old_latex: string;
  new_latex: string;
  rationale: string;
}
