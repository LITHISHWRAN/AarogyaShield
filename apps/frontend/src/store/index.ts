import { create } from 'zustand'
import type { ChatMessage, UserProfile } from '@/types'

interface AppState {
  sessionId: string
  userProfile: UserProfile | null
  chatHistory: ChatMessage[]
  setSessionId: (id: string) => void
  setUserProfile: (profile: UserProfile) => void
  addMessage: (msg: ChatMessage) => void
  clearChat: () => void
}

export const useAppStore = create<AppState>((set) => ({
  sessionId: crypto.randomUUID(),
  userProfile: null,
  chatHistory: [],
  setSessionId: (id) => set({ sessionId: id }),
  setUserProfile: (profile) => set({ userProfile: profile }),
  addMessage: (msg) => set((s) => ({ chatHistory: [...s.chatHistory, msg] })),
  clearChat: () => set({ chatHistory: [] }),
}))
