# Phase 3: Frontend OAuth Integration

**Priority:** P1 | **Status:** Pending | **Effort:** 2h

## Context

- Research: `plans/reports/researcher-260327-1108-google-oauth-implementation.md`
- Depends on: Phase 2 (Backend OAuth Endpoints)
- Auth store: `frontend/src/stores/auth-store.ts`
- Router: `frontend/src/router/index.ts`
- Login view: `frontend/src/views/LoginView.vue`

## Overview

Add Google OAuth button to login page, handle OAuth callback, and update auth store with OAuth methods.

## Key Insights

1. OAuth button redirects to backend `/oauth/authorize`
2. Callback page extracts code/state from URL, calls backend
3. Auth store needs new `oauthLogin` method
4. Existing Google button in LoginView is non-functional - wire it up

## Requirements

### Functional
- Google OAuth button on login/register pages
- OAuth callback route handler
- Auth store OAuth methods
- Loading states and error handling
- Redirect after successful login

### Non-Functional
- OAuth button matches existing design
- Smooth loading transitions
- Clear error messages

## Architecture

```
Login Flow:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ LoginView   │────▶│ Backend     │────▶│ Google      │
│ (click)     │     │ /authorize  │     │ Consent     │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Dashboard   │◀────│ AuthStore   │◀────│ CallbackView│
│ (redirect)  │     │ (setTokens) │     │ (code/state)│
└─────────────┘     └─────────────┘     └─────────────┘
```

## Related Code Files

### Modify
- `frontend/src/stores/auth-store.ts` - Add OAuth methods
- `frontend/src/views/LoginView.vue` - Wire Google button
- `frontend/src/views/RegisterView.vue` - Add OAuth option
- `frontend/src/router/index.ts` - Add callback route

### Create
- `frontend/src/views/OAuthCallbackView.vue` - Handle callback
- `frontend/src/api/oauth.ts` - OAuth API calls

## Implementation Steps

### Step 1: Update Auth Store

```typescript
// frontend/src/stores/auth-store.ts

export interface OAuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
  is_new_user: boolean
}

export const useAuthStore = defineStore('auth', () => {
  // ... existing state ...

  const oauthLoading = ref(false)

  async function oauthLogin(code: string, state: string): Promise<boolean> {
    oauthLoading.value = true
    error.value = null

    try {
      const { data } = await api.get<OAuthResponse>('/oauth/callback', {
        params: { code, state }
      })

      accessToken.value = data.access_token
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)

      user.value = data.user
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'OAuth login failed'
      return false
    } finally {
      oauthLoading.value = false
    }
  }

  async function initOAuth() {
    // Redirect to backend OAuth authorize endpoint
    window.location.href = '/api/v1/oauth/authorize'
  }

  return {
    // ... existing exports ...
    oauthLoading,
    oauthLogin,
    initOAuth
  }
})
```

### Step 2: Create OAuth Callback View

```vue
<!-- frontend/src/views/OAuthCallbackView.vue -->

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth-store'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  const code = route.query.code as string
  const state = route.query.state as string
  const errorParam = route.query.error as string

  if (errorParam) {
    error.value = route.query.error_description as string || errorParam
    loading.value = false
    return
  }

  if (!code || !state) {
    error.value = 'Missing OAuth parameters'
    loading.value = false
    return
  }

  try {
    const success = await authStore.oauthLogin(code, state)

    if (success) {
      // Redirect to dashboard or intended page
      const redirect = route.query.redirect as string || '/'
      router.replace(redirect)
    } else {
      error.value = authStore.error || 'OAuth login failed'
    }
  } catch (e: any) {
    error.value = e.message || 'An error occurred'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="min-h-screen w-full flex items-center justify-center bg-[#0f172a]">
    <!-- Loading State -->
    <div v-if="loading" class="text-center">
      <div class="inline-flex items-center justify-center w-16 h-16 mb-4 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 animate-pulse">
        <svg class="w-8 h-8 text-white animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>
      <p class="text-slate-400 text-lg">Completing login...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center max-w-md px-6">
      <div class="inline-flex items-center justify-center w-16 h-16 mb-4 rounded-2xl bg-red-500/20">
        <svg class="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <h2 class="text-xl font-semibold text-white mb-2">Login Failed</h2>
      <p class="text-slate-400 mb-6">{{ error }}</p>
      <router-link
        to="/login"
        class="inline-flex items-center px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium hover:from-blue-500 hover:to-indigo-500 transition-all"
      >
        Try Again
      </router-link>
    </div>
  </main>
</template>
```

### Step 3: Add Callback Route

```typescript
// frontend/src/router/index.ts

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // ... existing routes ...
    {
      path: '/oauth/callback',
      name: 'oauth-callback',
      component: () => import('@/views/OAuthCallbackView.vue'),
      meta: { guest: true }
    },
    // ...
  ]
})
```

### Step 4: Update Login View

```vue
<!-- frontend/src/views/LoginView.vue -->

<script setup lang="ts">
// ... existing imports ...
import { useAuthStore } from '@/stores/auth-store'

const authStore = useAuthStore()

// ... existing code ...

async function handleGoogleLogin() {
  loading.value = true
  authStore.initOAuth()
}
</script>

<template>
  <!-- ... existing template ... -->

  <!-- Social Logins - UPDATE EXISTING BUTTON -->
  <div class="grid grid-cols-2 gap-4">
    <button
      @click="handleGoogleLogin"
      :disabled="loading"
      class="flex items-center justify-center px-4 py-2.5 border border-slate-700 rounded-xl bg-slate-800/50 text-slate-300 hover:bg-slate-700/50 hover:text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <svg class="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
        <!-- Google icon SVG paths -->
      </svg>
      Google
    </button>
    <!-- GitHub button remains placeholder -->
  </div>

  <!-- ... rest of template ... -->
</template>
```

### Step 5: Update Register View

```vue
<!-- frontend/src/views/RegisterView.vue -->

<!-- Add similar OAuth button as LoginView -->
<div class="relative my-6">
  <div class="absolute inset-0 flex items-center">
    <div class="w-full border-t border-slate-700"></div>
  </div>
  <div class="relative flex justify-center text-xs uppercase">
    <span class="px-2 text-slate-500">Or continue with</span>
  </div>
</div>

<button
  @click="handleGoogleLogin"
  class="w-full flex items-center justify-center px-4 py-3 border border-slate-700 rounded-xl bg-slate-800/50 text-slate-300 hover:bg-slate-700/50 hover:text-white transition-all"
>
  <svg class="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
    <!-- Google icon -->
  </svg>
  Sign up with Google
</button>
```

## Todo List

- [ ] Update auth-store.ts with oauthLogin and initOAuth
- [ ] Create OAuthCallbackView.vue
- [ ] Add callback route to router
- [ ] Wire Google button in LoginView
- [ ] Add OAuth button to RegisterView
- [ ] Test OAuth flow end-to-end
- [ ] Test error handling

## Success Criteria

- [ ] Google button redirects to OAuth
- [ ] Callback page shows loading state
- [ ] Tokens stored after successful OAuth
- [ ] User redirected to dashboard
- [ ] Error messages displayed properly
- [ ] Loading states work correctly
- [ ] Works on both login and register pages

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Callback URL mismatch | High | Configure exact redirect URI in Google Console |
| Session lost on redirect | Medium | Check cookie settings, same-site policy |
| Race condition on token save | Low | Use async/await properly |

## Security Considerations

- State parameter validated by backend
- Tokens stored in localStorage (acceptable for SPA)
- Consider httpOnly cookies for production
- Clear error messages without exposing internals

## Next Steps

After completion:
- Proceed to Phase 4: Environment Configuration (if not done)
- Proceed to Phase 5: Security Hardening
