/**
 * Auth store -- delegates all auth to Supabase client.
 * No manual token storage. Supabase manages session persistence.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { supabase } from '@/lib/supabase'
import type { User } from '@supabase/supabase-js'
import api from '@/api/client'

export interface AppUser {
  id: string
  email: string
  role: 'user' | 'editor' | 'admin'
  is_active: boolean
  email_verified?: boolean
  name?: string
  avatar_url?: string
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AppUser | null>(null)
  const supabaseUser = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!supabaseUser.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  /**
   * Fetch app user from backend /auth/me.
   * Called after Supabase session is confirmed.
   */
  async function fetchUser(): Promise<void> {
    try {
      const { data } = await api.get('/auth/me')
      user.value = data
    } catch {
      user.value = null
    }
  }

  /**
   * Email/password login via Supabase.
   */
  async function login(email: string, password: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const { data, error: sbError } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (sbError) {
        error.value = sbError.message
        return false
      }

      supabaseUser.value = data.user
      await fetchUser()
      return true
    } catch (e: any) {
      error.value = e.message || 'Login failed'
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Email/password registration via Supabase.
   */
  async function register(email: string, password: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const { data, error: sbError } = await supabase.auth.signUp({
        email,
        password,
      })

      if (sbError) {
        error.value = sbError.message
        return false
      }

      // If email confirmation is disabled, user is immediately logged in
      if (data.user && data.session) {
        supabaseUser.value = data.user
        await fetchUser()
      }

      return true
    } catch (e: any) {
      error.value = e.message || 'Registration failed'
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Google OAuth via Supabase.
   * Supabase handles the entire OAuth flow and redirect.
   */
  async function loginWithGoogle(): Promise<void> {
    const { error: sbError } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/`,
      },
    })

    if (sbError) {
      error.value = sbError.message
    }
  }

  /**
   * Logout via Supabase.
   */
  async function logout(): Promise<void> {
    await supabase.auth.signOut()
    user.value = null
    supabaseUser.value = null
  }

  /**
   * Initialize auth state from existing Supabase session.
   * Handles PKCE callback (code in URL) and normal session restore.
   */
  async function init(): Promise<void> {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')

    // Register auth listener BEFORE any async exchange to avoid race conditions
    // onAuthStateChange fires INITIAL_SESSION on first subscribe — skip it to
    // prevent duplicate fetchUser() calls during PKCE exchange.
    let skipInitialEvent = true
    supabase.auth.onAuthStateChange(async (event, session) => {
      if (skipInitialEvent) {
        skipInitialEvent = false
        return
      }
      if (event === 'SIGNED_IN' && session?.user) {
        supabaseUser.value = session.user
        await fetchUser()
      } else if (event === 'SIGNED_OUT') {
        user.value = null
        supabaseUser.value = null
      }
    })

    if (code) {
      // PKCE flow — exchange auth code for session
      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
      if (exchangeError) {
        error.value = 'Google login failed — please try again'
      } else if (data.session?.user) {
        supabaseUser.value = data.session.user
        await fetchUser()
      }
      window.history.replaceState({}, document.title, window.location.pathname)
    } else {
      // Restore existing session
      const { data: { session } } = await supabase.auth.getSession()
      if (session?.user) {
        supabaseUser.value = session.user
        await fetchUser()
      }
    }
  }

  return {
    user,
    supabaseUser,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    login,
    register,
    fetchUser,
    logout,
    loginWithGoogle,
    init,
  }
})
