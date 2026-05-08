import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const authApi = {
  register: (email: string, password: string, full_name: string) =>
    api.post('/auth/register', { email, password, full_name }),
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
}

export const chatApi = {
  send: (session_id: string, message: string, user_profile?: object) =>
    api.post('/chat/', { session_id, message, user_profile }),
  clearSession: (session_id: string) =>
    api.delete(`/chat/${session_id}`),
}

export const recommendApi = {
  get: (session_id: string, user_profile: object) =>
    api.post('/recommendations/', { session_id, user_profile }),
}

export const policiesApi = {
  list: () => api.get('/policies/'),
  get: (id: string) => api.get(`/policies/${id}`),
}

export const adminApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/admin/policies/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete: (policy_id: string) => api.delete(`/admin/policies/${policy_id}`),
}

export default api
