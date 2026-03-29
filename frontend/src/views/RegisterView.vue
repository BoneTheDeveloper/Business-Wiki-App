<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth-store'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Toast from 'primevue/toast'

const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)

async function handleRegister() {
  if (password.value !== confirmPassword.value) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Passwords do not match' })
    return
  }

  if (password.value.length < 6) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Password must be at least 6 characters' })
    return
  }

  loading.value = true

  try {
    const success = await authStore.register(email.value, password.value)

    if (success) {
      toast.add({ severity: 'success', summary: 'Success', detail: 'Account created. Please login.' })
      router.push('/login')
    } else {
      toast.add({ severity: 'error', summary: 'Error', detail: authStore.error || 'Registration failed' })
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Toast />
  <main class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
      <h1 class="text-2xl font-bold text-center mb-6 text-gray-800">Register</h1>

      <form @submit.prevent="handleRegister" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <InputText
            v-model="email"
            type="email"
            placeholder="your@email.com"
            class="w-full"
            required
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <Password
            v-model="password"
            placeholder="Password"
            toggleMask
            class="w-full"
            inputClass="w-full"
            required
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
          <Password
            v-model="confirmPassword"
            placeholder="Confirm Password"
            :feedback="false"
            toggleMask
            class="w-full"
            inputClass="w-full"
            required
          />
        </div>

        <Button
          type="submit"
          label="Register"
          :loading="loading"
          class="w-full"
        />
      </form>

      <p class="text-center mt-4 text-sm text-gray-600">
        Already have an account?
        <router-link to="/login" class="text-blue-600 hover:underline">Login</router-link>
      </p>
    </div>
  </main>
</template>
