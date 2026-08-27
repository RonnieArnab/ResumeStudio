import type { StateCreator } from "zustand";
import type { ResumeSession } from "../types/resume";

export interface ResumeSlice {
  session: ResumeSession | null;
  setSession: (session: ResumeSession) => void;
}

export const createResumeSlice: StateCreator<ResumeSlice> = (set) => ({
  session: null,
  setSession: (session) => set({ session }),
});
