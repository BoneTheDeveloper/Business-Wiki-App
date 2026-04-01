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
  // Show OAuth error if redirected back with error
  const oauthError = route.query.oauth_error as string
  if (oauthError) {
    const messages: Record<string, string> = {
      missing_tokens: 'Google login failed - missing credentials',
      callback_failed: 'Google login failed - please try again',
      access_denied: 'Google login was cancelled',
    }
    toast.add({ severity: 'error', summary: 'OAuth Error', detail: messages[oauthError] || 'Google login failed' })
  }
})

async function handleLogin() {
  loading.value = true

  try {
    const success = await authStore.login(email.value, password.value)

    if (success) {
      toast.add({ severity: 'success', summary: 'Welcome', detail: 'Login successful' })
      const redirect = (route.query.redirect as string) || '/'
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
    // Page will redirect to Google -- no further action needed here
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to initiate Google login' })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Toast />
  <main class="min-h-screen w-full flex items-center justify-center relative overflow-hidden bg-[#0f172a]">
    <!-- Background Decorative Blobs -->
    <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/30 rounded-full blur-[120px] animate-pulse"></div>
    <div class="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-600/20 rounded-full blur-[120px] animate-pulse" style="animation-delay: 2s;"></div>
    <div class="absolute top-[20%] right-[10%] w-[20%] h-[20%] bg-purple-600/20 rounded-full blur-[100px]"></div>

    <!-- Main Login Card -->
    <div class="relative z-10 w-full max-w-md px-6 py-12 md:px-10 bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl transition-all duration-300 hover:shadow-blue-500/10">

      <!-- Header Section -->
      <div class="text-center mb-10">
        <div class="inline-flex items-center justify-center w-16 h-16 mb-4 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 shadow-lg shadow-blue-500/30">
          <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <h1 class="text-3xl font-bold text-white tracking-tight mb-2">Welcome Back!</h1>
        <p class="text-slate-400 text-sm">Please enter your credentials to access the system</p>
      </div>

      <!-- Form Section -->
      <form @submit.prevent="handleLogin" class="space-y-6">
        <!-- Email Input -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-slate-300 ml-1">Email Address</label>
          <div class="relative group">
            <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <svg class="h-5 w-5 text-slate-500 group-focus-within:text-blue-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <input
              v-model="email"
              type="email"
              class="block w-full pl-11 pr-4 py-3 bg-slate-900/50 border border-slate-700 text-white rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all placeholder:text-slate-600"
              placeholder="name@company.com"
              required
            />
          </div>
        </div>

        <!-- Password Input -->
        <div class="space-y-2">
          <div class="flex justify-between items-center ml-1">
            <label class="text-sm font-medium text-slate-300">Password</label>
            <a href="#" class="text-xs text-blue-400 hover:text-blue-300 transition-colors">Forgot password?</a>
          </div>
          <div class="relative group">
            <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <svg class="h-5 w-5 text-slate-500 group-focus-within:text-blue-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              class="block w-full pl-11 pr-12 py-3 bg-slate-900/50 border border-slate-700 text-white rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all placeholder:text-slate-600"
              placeholder="••••••••"
              required
            />
            <button
              type="button"
              class="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-500 hover:text-slate-300 transition-colors"
              @click="showPassword = !showPassword"
            >
              <svg v-if="showPassword" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              </svg>
              <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Remember Me -->
        <div class="flex items-center space-x-2 px-1">
          <input
            v-model="rememberMe"
            type="checkbox"
            id="remember"
            class="w-4 h-4 rounded border-slate-700 bg-slate-900/50 text-blue-600 focus:ring-blue-500/50 cursor-pointer"
          />
          <label for="remember" class="text-sm text-slate-400 cursor-pointer select-none">Remember me</label>
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          :disabled="loading"
          class="group relative w-full flex justify-center py-3.5 px-4 border border-transparent rounded-xl text-white text-sm font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#0f172a] focus:ring-blue-500 transition-all shadow-lg shadow-blue-500/25 overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="loading" class="flex items-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Signing in...
          </span>
          <span v-else class="relative z-10 flex items-center">
            Sign In
            <svg class="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </span>
          <div class="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
        </button>
      </form>

      <!-- Divider -->
      <div class="relative my-8">
        <div class="absolute inset-0 flex items-center">
          <div class="w-full border-t border-slate-700"></div>
        </div>
        <div class="relative flex justify-center text-xs uppercase">
          <span class="bg-[#1e293b]/0 px-2 text-slate-500 backdrop-blur-xl">Or continue with</span>
        </div>
      </div>

      <!-- Social Logins -->
      <div class="grid grid-cols-2 gap-4">
        <button
          type="button"
          @click="handleGoogleLogin"
          class="flex items-center justify-center px-4 py-2.5 border border-slate-700 rounded-xl bg-slate-800/50 text-slate-300 hover:bg-slate-700/50 hover:text-white transition-all"
        >
          <svg class="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          Google
        </button>
        <button class="flex items-center justify-center px-4 py-2.5 border border-slate-700 rounded-xl bg-slate-800/50 text-slate-300 hover:bg-slate-700/50 hover:text-white transition-all">
          <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
          </svg>
          GitHub
        </button>
      </div>

      <!-- Footer Link -->
      <p class="mt-10 text-center text-sm text-slate-400">
        Don't have an account?
        <router-link to="/register" class="font-semibold text-blue-400 hover:text-blue-300 transition-colors">
          Sign up now
        </router-link>
      </p>
    </div>
  </main>
</template>
