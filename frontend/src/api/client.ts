/**
 * Axios API client with Supabase auth interceptor.
 * Gets access token from Supabase session (not localStorage).
 * Supabase client handles token refresh automatically.
 */
import axios from 'axios'
import { supabase } from '@/lib/supabase'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach Supabase access token
api.interceptors.request.use(
  async (config) => {
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Response interceptor: handle 401 by attempting session recovery
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      // Try to refresh the session
      const { data: { session } } = await supabase.auth.refreshSession()

      if (session?.access_token) {
        originalRequest.headers.Authorization = `Bearer ${session.access_token}`
        return api(originalRequest)
      }

      // Session recovery failed -- redirect to login
      await supabase.auth.signOut()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    return Promise.reject(error)
  },
)

export default api
