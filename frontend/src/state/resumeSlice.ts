import type { StateCreator } from "zustand";
import type { MatchReport, ResumeSession } from "../types/resume";
import type { StagedEditSummary } from "../types/agent";

export interface ResumeSlice {
  session: ResumeSession | null;
  stagedEdits: StagedEditSummary[];
  matchReport: MatchReport | null;
  /** instruction to pre-fill the section edit modal with (e.g. from a match suggestion) */
  pendingSectionInstruction: string | null;
  setSession: (session: ResumeSession) => void;
  setStagedEdits: (edits: StagedEditSummary[]) => void;
  setMatchReport: (report: MatchReport | null) => void;
  setPendingSectionInstruction: (instruction: string | null) => void;
}

export const createResumeSlice: StateCreator<ResumeSlice> = (set) => ({
  session: null,
  stagedEdits: [],
  matchReport: null,
  pendingSectionInstruction: null,
  setSession: (session) => set({ session }),
  setStagedEdits: (stagedEdits) => set({ stagedEdits }),
  setMatchReport: (matchReport) => set({ matchReport }),
  setPendingSectionInstruction: (pendingSectionInstruction) => set({ pendingSectionInstruction }),
});
