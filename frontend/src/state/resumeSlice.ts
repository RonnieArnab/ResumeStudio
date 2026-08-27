import type { StateCreator } from "zustand";
import type { ResumeSession } from "../types/resume";
import type { StagedEditSummary } from "../types/agent";

export interface ResumeSlice {
  session: ResumeSession | null;
  stagedEdits: StagedEditSummary[];
  setSession: (session: ResumeSession) => void;
  setStagedEdits: (edits: StagedEditSummary[]) => void;
}

export const createResumeSlice: StateCreator<ResumeSlice> = (set) => ({
  session: null,
  stagedEdits: [],
  setSession: (session) => set({ session }),
  setStagedEdits: (stagedEdits) => set({ stagedEdits }),
});
