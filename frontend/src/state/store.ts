import { create } from "zustand";
import { createChatSlice, type ChatSlice } from "./chatSlice";
import { createJobsSlice, type JobsSlice } from "./jobsSlice";
import { createResumeSlice, type ResumeSlice } from "./resumeSlice";
import { createSelectionSlice, type SelectionSlice } from "./selectionSlice";
import { createViewSlice, type ViewSlice } from "./viewSlice";

type StoreState = ResumeSlice & SelectionSlice & ChatSlice & ViewSlice & JobsSlice;

export const useStore = create<StoreState>()((...args) => ({
  ...createResumeSlice(...args),
  ...createSelectionSlice(...args),
  ...createChatSlice(...args),
  ...createViewSlice(...args),
  ...createJobsSlice(...args),
}));
