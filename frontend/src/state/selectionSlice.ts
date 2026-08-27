import type { StateCreator } from "zustand";

export interface SelectionSlice {
  selectedSectionId: string | null;
  selectSection: (id: string | null) => void;
}

export const createSelectionSlice: StateCreator<SelectionSlice> = (set) => ({
  selectedSectionId: null,
  selectSection: (id) => set({ selectedSectionId: id }),
});
