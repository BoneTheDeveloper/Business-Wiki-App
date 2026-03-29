/**
 * Authentication store with Pinia.
 * Manages user state, tokens, login/logout/refresh operations.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

export interface User {
  id: string
  email: string
  role: 'user' | 'editor' | 'admin'
  is_active: boolean
  email_verified?: boolean
  name?: string
  avatar_url?: string
  oauth_provider?: string
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(email: string, password: string) {
    loading.value = true
    error.value = null

    try {
      const { data } = await api.post('/auth/login', { email, password })

      accessToken.value = data.access_token
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)

      await fetchUser()
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Login failed'
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string) {
    loading.value = true
    error.value = null

    try {
      await api.post('/auth/register', { email, password })
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Registration failed'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    try {
      const { data } = await api.get('/auth/me')
      user.value = data
    } catch (e) {
      user.value = null
    }
  }

  async function refreshToken() {
    const refreshTokenValue = localStorage.getItem('refresh_token')
    if (!refreshTokenValue) {
      throw new Error('No refresh token')
    }

    const { data } = await api.post('/auth/refresh', {
      refresh_token: refreshTokenValue
    })

    accessToken.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
  }

  function logout() {
    user.value = null
    accessToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  // OAuth login - redirect to Google
  function loginWithGoogle() {
    window.location.href = '/api/v1/auth/oauth/google'
  }

  // Handle OAuth callback with tokens
  async function handleOAuthCallback(access_token: string, refresh_token: string) {
    accessToken.value = access_token
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    await fetchUser()
  }

  // Initialize - fetch user if token exists
  async function init() {
    if (accessToken.value) {
      await fetchUser()
    }
  }

  return {
    user,
    accessToken,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    login,
    register,
    fetchUser,
    refreshToken,
    logout,
    loginWithGoogle,
    handleOAuthCallback,
    init
  }
})
