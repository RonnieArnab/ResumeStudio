import type { StateCreator } from "zustand";
import type { ChatMessageSummary } from "../types/chat";

export interface ChatSlice {
  messages: ChatMessageSummary[];
  jobDescription: string | null;
  addMessage: (message: ChatMessageSummary) => void;
  setMessages: (messages: ChatMessageSummary[]) => void;
  setJobDescription: (jobDescription: string | null) => void;
}

export const createChatSlice: StateCreator<ChatSlice> = (set) => ({
  messages: [],
  jobDescription: null,
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setMessages: (messages) => set({ messages }),
  setJobDescription: (jobDescription) => set({ jobDescription }),
});
