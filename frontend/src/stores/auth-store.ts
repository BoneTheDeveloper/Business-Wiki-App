/**
 * Auth store — fully Supabase SDK. No backend API calls for user data.
 * User profile built from Supabase session + JWT app_role claim.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { supabase } from '@/lib/supabase'
import type { User } from '@supabase/supabase-js'

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

/** Build AppUser from Supabase User. Role from JWT app_role claim (custom_access_token hook). */
function buildUser(sbUser: User): AppUser {
  return {
    id: sbUser.id,
    email: sbUser.email ?? '',
    role: (sbUser.app_metadata?.app_role as AppUser['role']) || 'user',
    is_active: true,
    email_verified: sbUser.email_confirmed_at != null,
    name: sbUser.user_metadata?.name || sbUser.user_metadata?.full_name,
    avatar_url: sbUser.user_metadata?.avatar_url,
    created_at: sbUser.created_at,
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AppUser | null>(null)
  const supabaseUser = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!supabaseUser.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  /** Sync both refs from a Supabase User object. */
  function syncUser(sbUser: User) {
    supabaseUser.value = sbUser
    user.value = buildUser(sbUser)
  }

  /** Clear all auth state. */
  function clearUser() {
    user.value = null
    supabaseUser.value = null
  }

  /** Email/password login via Supabase. */
  async function login(email: string, password: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const { data, error: sbError } = await supabase.auth.signInWithPassword({ email, password })
      if (sbError) {
        error.value = sbError.message
        return false
      }
      syncUser(data.user)
      return true
    } catch (e: any) {
      error.value = e.message || 'Login failed'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Email/password registration via Supabase. */
  async function register(email: string, password: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const { data, error: sbError } = await supabase.auth.signUp({ email, password })
      if (sbError) {
        error.value = sbError.message
        return false
      }
      if (data.user && data.session) {
        syncUser(data.user)
      }
      return true
    } catch (e: any) {
      error.value = e.message || 'Registration failed'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Google OAuth via Supabase. */
  async function loginWithGoogle(): Promise<void> {
    const { error: sbError } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/` },
    })
    if (sbError) {
      error.value = sbError.message
    }
  }

  /** Logout via Supabase. */
  async function logout(): Promise<void> {
    await supabase.auth.signOut()
    clearUser()
  }

  /**
   * Initialize auth state. Handles PKCE exchange and session restore.
   * CRITICAL: Never throws — router guard depends on init() resolving.
   */
  async function init(): Promise<void> {
    // Register listener FIRST — exchangeCodeForSession fires SIGNED_IN internally
    supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        syncUser(session.user)
      } else if (event === 'SIGNED_OUT') {
        clearUser()
      }
    })

    try {
      const params = new URLSearchParams(window.location.search)
      const code = params.get('code')
      if (code) {
        const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
        if (exchangeError) {
          error.value = 'OAuth login failed. Please try again.'
        } else if (data.session?.user) {
          syncUser(data.session.user)
        }
        // Always clean URL — prevents crash loop on refresh with stale code
        window.history.replaceState({}, document.title, window.location.pathname)
        return
      }

      // Restore existing session on page refresh
      const { data: { session } } = await supabase.auth.getSession()
      if (session?.user) {
        syncUser(session.user)
      }
    } catch (err) {
      console.error('Auth init failed:', err)
      if (window.location.search.includes('code=')) {
        window.history.replaceState({}, document.title, window.location.pathname)
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
    logout,
    loginWithGoogle,
    init,
  }
})
