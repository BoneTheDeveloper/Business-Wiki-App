<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth-store'
import AppLayout from '@/components/AppLayout.vue'

const route = useRoute()
const authStore = useAuthStore()

onMounted(async () => {
  await authStore.init()
})
</script>

<template>
  <!-- Auth pages without layout -->
  <RouterView v-if="route.meta.guest" />

  <!-- Protected pages with layout -->
  <AppLayout v-else-if="authStore.isAuthenticated">
    <RouterView />
  </AppLayout>

  <!-- Loading state while checking auth -->
  <div v-else class="min-h-screen flex items-center justify-center">
    <p class="text-gray-500">Loading...</p>
  </div>
</template>
