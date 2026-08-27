import type { StateCreator } from "zustand";
import type { ApplyRunView, BoardSource, RankedJob } from "../types/jobs";

export interface JobsSlice {
  sources: BoardSource[];
  jobs: RankedJob[];
  selectedJobId: string | null;
  applyRun: ApplyRunView | null;
  crawlLog: string[];
  crawling: boolean;
  trackerVersion: number;

  setSources: (sources: BoardSource[]) => void;
  setJobs: (jobs: RankedJob[]) => void;
  selectJob: (jobId: string | null) => void;
  setApplyRun: (run: ApplyRunView | null) => void;
  setCrawlLog: (log: string[]) => void;
  appendCrawlLog: (line: string) => void;
  setCrawling: (crawling: boolean) => void;
  bumpTracker: () => void;
}

export const createJobsSlice: StateCreator<JobsSlice> = (set) => ({
  sources: [],
  jobs: [],
  selectedJobId: null,
  applyRun: null,
  crawlLog: [],
  crawling: false,
  trackerVersion: 0,

  setSources: (sources) => set({ sources }),
  setJobs: (jobs) => set({ jobs }),
  selectJob: (selectedJobId) => set({ selectedJobId, applyRun: null }),
  setApplyRun: (applyRun) => set({ applyRun }),
  setCrawlLog: (crawlLog) => set({ crawlLog }),
  appendCrawlLog: (line) => set((state) => ({ crawlLog: [...state.crawlLog, line] })),
  setCrawling: (crawling) => set({ crawling }),
  bumpTracker: () => set((state) => ({ trackerVersion: state.trackerVersion + 1 })),
});
