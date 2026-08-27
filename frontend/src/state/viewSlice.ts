import type { StateCreator } from "zustand";

export type AppView = "resume" | "jobs";

export interface ViewSlice {
  view: AppView;
  setView: (view: AppView) => void;
}

export const createViewSlice: StateCreator<ViewSlice> = (set) => ({
  view: "resume",
  setView: (view) => set({ view }),
});
