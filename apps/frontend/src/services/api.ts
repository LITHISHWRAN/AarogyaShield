import axios from 'axios'
import type { AdminDeleteResponse, AdminPolicy, AdminUploadResponse, ChatResponse, Policy, RecommendationResponse, TokenResponse } from '@/types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

// ── Standard API client (user-facing) ────────────────────────────────────────

const api = axios.create({
  baseURL: `${BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Admin API client (uses admin JWT) ─────────────────────────────────────────

const adminApi = axios.create({
  baseURL: `${BASE}/api/v1`,
})

adminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  register: (email: string, password: string, full_name: string) =>
    api.post<TokenResponse>('/auth/register', { email, password, full_name }),
  login: (email: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { email, password }),
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export const chatApi = {
  send: (session_id: string, message: string, user_profile?: object) =>
    api.post<ChatResponse>('/chat/', { session_id, message, user_profile }),
  getSessionInfo: (session_id: string) =>
    api.get(`/chat/${session_id}/session`),
  clearSession: (session_id: string) =>
    api.delete(`/chat/${session_id}`),
}

// ── Recommendations ───────────────────────────────────────────────────────────

export const recommendApi = {
  get: (session_id: string, user_profile: object) =>
    api.post<RecommendationResponse>('/recommendations/', { session_id, user_profile }),
}

// ── Policies (public) ─────────────────────────────────────────────────────────

export const policiesApi = {
  list: () => api.get<Policy[]>('/policies/'),
}

// ── Admin (requires admin JWT stored as admin_token) ──────────────────────────

export const adminAuthApi = {
  login: (username: string, password: string) => {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    return axios.post<TokenResponse>(`${BASE}/api/v1/admin/login`, form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
}

export const adminPoliciesApi = {
  list: () => adminApi.get<AdminPolicy[]>('/admin/policies'),
  upload: (file: File, policy_name: string, insurer: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('policy_name', policy_name)
    form.append('insurer', insurer)
    return adminApi.post<AdminUploadResponse>('/admin/policies/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete: (policy_id: string) =>
    adminApi.delete<AdminDeleteResponse>(`/admin/policies/${policy_id}`),
}

export default api
