import { create } from 'zustand'
import type { ChatTurn, RecommendationResponse, UserProfile } from '@/types'

interface AppState {
  sessionId: string
  userProfile: UserProfile | null
  recommendations: RecommendationResponse | null
  chatTurns: ChatTurn[]
  adminToken: string | null

  setUserProfile: (profile: UserProfile) => void
  setRecommendations: (recs: RecommendationResponse) => void
  addChatTurn: (turn: ChatTurn) => void
  clearChat: () => void
  setAdminToken: (token: string | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  sessionId: crypto.randomUUID(),
  userProfile: null,
  recommendations: null,
  chatTurns: [],
  adminToken: localStorage.getItem('admin_token'),

  setUserProfile: (profile) => set({ userProfile: profile }),
  setRecommendations: (recs) => set({ recommendations: recs }),
  addChatTurn: (turn) => set((s) => ({ chatTurns: [...s.chatTurns, turn] })),
  clearChat: () => set({ chatTurns: [] }),
  setAdminToken: (token) => {
    if (token) localStorage.setItem('admin_token', token)
    else localStorage.removeItem('admin_token')
    set({ adminToken: token })
  },
}))
