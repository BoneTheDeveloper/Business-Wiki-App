---
title: "Phase 3: Frontend Auth Migration"
phase: 3
status: pending
effort: 5h
depends_on: [phase-01]
---

# Phase 3: Frontend Auth Migration

## Context
- Plan: [plan.md](plan.md)
- Phase 1: [phase-01-local-dev-infrastructure.md](phase-01-local-dev-infrastructure.md)
- Backend: [phase-02-backend-auth-migration.md](phase-02-backend-auth-migration.md) (can run in parallel)

## Overview
Replace all custom auth logic (manual token storage, backend auth endpoints, OAuth redirects) with `@supabase/supabase-js` client. Supabase handles signup, login, OAuth, session persistence, and token refresh.

## Requirements

### Functional
- Email/password signup and login via Supabase Auth
- Google OAuth via Supabase `signInWithOAuth`
- Session persisted by Supabase client (not manual localStorage)
- Access token from Supabase session attached to all API requests
- Auto-refresh tokens handled by Supabase client
- Logout clears Supabase session
- Router guards use Supabase session state

### Non-Functional
- No manual token management in localStorage
- Auth state reactive across components via Pinia store
- OAuth redirect seamless (no visible callback page flicker)

## Architecture

```
BEFORE:
  LoginView --POST /auth/login--> backend --returns JWT--> localStorage
  OAuth -----> backend /auth/oauth/google --> Google --> backend callback --> redirect with tokens in URL

AFTER:
  LoginView --supabase.signInWithPassword()--> Supabase Auth --> session in memory/cookie
  OAuth -----> supabase.signInWithOAuth() --> Google --> Supabase callback --> redirect to app
  API calls --getSession()--> get access_token --> Authorization header
```

## Related Code Files

### Modify
- `frontend/package.json` -- Add `@supabase/supabase-js`
- `frontend/src/stores/auth-store.ts` -- Rewrite with Supabase SDK
- `frontend/src/views/LoginView.vue` -- Use Supabase signIn methods
- `frontend/src/views/OAuthCallbackView.vue` -- Repurpose or remove
- `frontend/src/api/client.ts` -- Get token from Supabase session
- `frontend/src/router/index.ts` -- Use Supabase session for guards

### Create
- `frontend/src/lib/supabase.ts` -- Supabase client initialization

### Delete (optional)
- `frontend/src/views/OAuthCallbackView.vue` -- May no longer be needed depending on OAuth flow

## Implementation Steps

### Step 1: Install Supabase client

```bash
cd frontend
npm install @supabase/supabase-js
```

### Step 2: Create `frontend/src/lib/supabase.ts`

```typescript
/**
 * Supabase client initialization.
 * Uses env vars from Vite: VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY.
 */
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. Check frontend/.env'
  )
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### Step 3: Rewrite `frontend/src/stores/auth-store.ts`

Replace all localStorage token management with Supabase session.

```typescript
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
   * Called after session is confirmed.
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
   * Call once on app mount.
   */
  async function init(): Promise<void> {
    const { data: { session } } = await supabase.auth.getSession()

    if (session?.user) {
      supabaseUser.value = session.user
      await fetchUser()
    }

    // Listen for auth state changes (OAuth redirect, token refresh, etc.)
    supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        supabaseUser.value = session.user
        await fetchUser()
      } else if (event === 'SIGNED_OUT') {
        user.value = null
        supabaseUser.value = null
      }
    })
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
```

### Step 4: Update `frontend/src/api/client.ts`

Replace localStorage token with Supabase session token. Remove manual refresh logic (Supabase handles it).

```typescript
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
```

### Step 5: Update `frontend/src/views/LoginView.vue`

Key changes:
- `handleLogin()` calls `authStore.login()` (unchanged interface)
- `handleGoogleLogin()` calls `authStore.loginWithGoogle()` instead of `window.location.href`
- Remove `api` import (no longer needed for OAuth redirect)
- Keep existing UI/template unchanged

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth-store'
import { useToast } from 'primevue/usetoast'
import Toast from 'primevue/toast'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const toast = useToast()

const email = ref('')
const password = ref('')
const loading = ref(false)
const showPassword = ref(false)
const rememberMe = ref(false)

onMounted(() => {
  // Supabase OAuth errors come as URL hash fragments
  // The Supabase client processes them automatically via onAuthStateChange
})

async function handleLogin() {
  loading.value = true

  try {
    const success = await authStore.login(email.value, password.value)

    if (success) {
      toast.add({ severity: 'success', summary: 'Welcome', detail: 'Login successful' })
      const redirect = route.query.redirect as string || '/'
      router.push(redirect)
    } else {
      toast.add({ severity: 'error', summary: 'Error', detail: authStore.error || 'Login failed' })
    }
  } finally {
    loading.value = false
  }
}

async function handleGoogleLogin() {
  loading.value = true
  try {
    await authStore.loginWithGoogle()
    // Page will redirect to Google, then back -- no further action needed
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to initiate Google login' })
  } finally {
    loading.value = false
  }
}
</script>

<!-- Template stays exactly the same as current -->
<!-- Only the <script setup> logic changes -->
```

### Step 6: Handle OAuth callback / remove OAuthCallbackView

Supabase `signInWithOAuth` redirects back to the app with hash fragment `#access_token=...`. The Supabase client auto-processes this on page load via `onAuthStateChange`.

**Option A (recommended): Remove OAuthCallbackView entirely.**
- Delete the `/oauth/callback` route from router
- Delete `frontend/src/views/OAuthCallbackView.vue`
- Supabase redirects to `redirectTo` URL (e.g., `http://127.0.0.1:5173/`) and the auth store's `onAuthStateChange` handler picks up the session

**Option B: Keep OAuthCallbackView as a loading screen.**
- If Supabase `redirectTo` is set to `/oauth/callback`, the view shows a spinner while `onAuthStateChange` processes the hash fragment, then redirects to `/`.
- This provides a smoother UX but is not strictly necessary.

**Decision: Option A** -- simpler. Update router to remove the route.

### Step 7: Update `frontend/src/router/index.ts`

Remove `/oauth/callback` route. Update `beforeEach` guard to use auth store (interface unchanged).

```typescript
// Remove this route definition:
// {
//   path: '/oauth/callback',
//   name: 'oauth-callback',
//   component: () => import('@/views/OAuthCallbackView.vue'),
//   meta: { guest: true }
// },

// The beforeEach guard logic stays the same because authStore.isAuthenticated
// and authStore.init() have the same interface.
// Only change: call authStore.init() early to process Supabase hash fragments.
```

The guard should call `authStore.init()` on first navigation to ensure the Supabase session is loaded (including processing OAuth hash fragments on redirect).

```typescript
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Ensure auth is initialized (processes Supabase OAuth redirect hash on first load)
  if (!authStore.supabaseUser && !authStore.user) {
    await authStore.init()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  if (to.meta.guest && authStore.isAuthenticated) {
    next({ name: 'dashboard' })
    return
  }

  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next({ name: 'dashboard' })
    return
  }

  next()
})
```

### Step 8: Initialize auth store on app startup

In the main app entry point (likely `frontend/src/App.vue` or `frontend/src/main.ts`), call `authStore.init()` on mount.

In `App.vue`:
```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth-store'

const authStore = useAuthStore()

onMounted(async () => {
  await authStore.init()
})
</script>
```

Or ensure the router guard handles init (as shown in Step 7) and skip App.vue changes.

### Step 9: Update `frontend/vite.config.ts` (if needed)

No changes required. The existing proxy config already forwards `/api` to backend. Supabase Auth calls go directly to `VITE_SUPABASE_URL` (not through Vite proxy).

### Step 10: Delete OAuthCallbackView

```bash
rm frontend/src/views/OAuthCallbackView.vue
```

## Todo Checklist

- [ ] Install `@supabase/supabase-js` (`npm install @supabase/supabase-js`)
- [ ] Create `frontend/src/lib/supabase.ts`
- [ ] Rewrite `frontend/src/stores/auth-store.ts` with Supabase SDK
- [ ] Update `frontend/src/api/client.ts` (get token from Supabase session)
- [ ] Update `frontend/src/views/LoginView.vue` (Supabase signIn methods)
- [ ] Delete `frontend/src/views/OAuthCallbackView.vue`
- [ ] Update `frontend/src/router/index.ts` (remove oauth-callback route, update guard)
- [ ] Add auth init call (App.vue or rely on router guard)
- [ ] Verify `frontend/.env.example` has VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
- [ ] Run `npm run build` to verify no TypeScript/compile errors
- [ ] Manual test: login, logout, Google OAuth, session persistence

## Success Criteria
- `npm run build` completes without errors
- Email/password login creates Supabase session and fetches user from backend
- Google OAuth redirects to Google, returns to app, session established
- Page refresh maintains session (Supabase persists session)
- API calls include valid `Authorization: Bearer <token>` header
- Expired tokens auto-refresh via Supabase client
- Logout clears session and redirects to login
- Router guards redirect unauthenticated users to login

## Risk Assessment
- **OAuth redirect URL mismatch:** `redirectTo` in `signInWithOAuth` must match Supabase `site_url` + `additional_redirect_urls` in config.toml. If mismatched, OAuth silently fails.
- **Hash fragment processing:** Supabase uses URL hash fragments (`#access_token=...`) for OAuth callbacks. These are not sent to the server. The client SDK processes them on page load. If the app uses hash-based routing (`createWebHashHistory`), there could be conflicts. Our app uses `createWebHistory` (path-based), so no conflict.
- **Session persistence:** Supabase stores session in localStorage by default. If users clear localStorage, they are logged out. This is standard behavior.

## Security Considerations
- `VITE_SUPABASE_ANON_KEY` is public (embedded in frontend bundle). This is by design -- it's the Supabase "anon" key with restricted permissions enforced by RLS policies.
- Access tokens are short-lived (1 hour by default). Supabase auto-refreshes.
- No tokens stored in localStorage by our code. Supabase manages session storage.
- OAuth state parameter handled by Supabase internally (CSRF protection built-in).

## Next Steps
- Phase 4 (testing) validates the full flow end-to-end
- Update documentation in Phase 4
