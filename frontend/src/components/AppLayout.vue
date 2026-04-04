<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth-store'
import Menubar from 'primevue/menubar'
import Button from 'primevue/button'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const menuItems = computed(() => [
  {
    label: 'Documents',
    icon: 'pi pi-file',
    command: () => router.push('/')
  },
  {
    label: 'Search',
    icon: 'pi pi-search',
    command: () => router.push('/search')
  },
  {
    label: 'Chat',
    icon: 'pi pi-comments',
    command: () => router.push('/chat')
  },
  ...(authStore.isAdmin ? [{
    label: 'Admin',
    icon: 'pi pi-cog',
    command: () => router.push('/admin')
  }] : [])
])

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

const currentRoute = computed(() => route.name)
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <Menubar :model="menuItems" class="mb-0 rounded-none border-b">
      <template #start>
        <span class="text-xl font-bold text-blue-600 mr-4">
          <i class="pi pi-book mr-2"></i>
          Wiki App
        </span>
      </template>
      <template #end>
        <div class="flex items-center gap-4">
          <span v-if="authStore.user" class="text-sm text-gray-600">
            {{ authStore.user.email }}
            <span class="ml-2 text-xs px-2 py-1 bg-gray-100 rounded uppercase">{{ authStore.user.role }}</span>
          </span>
          <Button icon="pi pi-sign-out" label="Logout" text @click="handleLogout" />
        </div>
      </template>
    </Menubar>

    <!-- Main Content -->
    <main>
      <slot />
    </main>
  </div>
</template>
