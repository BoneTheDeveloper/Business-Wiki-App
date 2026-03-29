/**
 * Axios API client with auth interceptors.
 * Automatically adds Bearer token and handles token refresh on 401.
 */
import axios from 'axios'
import { useAuthStore } from '@/stores/auth-store'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If 401 and not already retrying, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) {
          throw new Error('No refresh token')
        }

        // Refresh token
        const { data } = await axios.post('/api/v1/auth/refresh', {
          refresh_token: refreshToken
        })

        // Store new tokens
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)

        // Retry original request
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed - logout user
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default api
