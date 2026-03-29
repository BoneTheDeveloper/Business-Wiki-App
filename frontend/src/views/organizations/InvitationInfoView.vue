<template>
  <div class="invitation-info-view min-h-screen flex items-center justify-center bg-gray-50">
    <div class="max-w-md w-full p-6">
      <!-- Loading state -->
      <Card v-if="loading" class="text-center">
        <template #content>
          <ProgressSpinner class="mb-4" />
          <p class="text-gray-600">Loading invitation details...</p>
        </template>
      </Card>

      <!-- Error state -->
      <Card v-else-if="error" class="text-center">
        <template #content>
          <i class="pi pi-exclamation-triangle text-6xl text-red-300 mb-4"></i>
          <h2 class="text-xl font-semibold text-gray-900 mb-2">Invalid Invitation</h2>
          <p class="text-gray-600 mb-4">{{ error }}</p>
          <Button
            label="Go to Home"
            @click="router.push({ name: 'home' })"
          />
        </template>
      </Card>

      <!-- Invitation preview -->
      <Card v-else-if="info" class="text-center">
        <template #content>
          <i class="pi pi-envelope text-6xl text-blue-500 mb-4"></i>
          <h2 class="text-xl font-semibold text-gray-900 mb-2">
            You've Been Invited!
          </h2>
          <p class="text-gray-600 mb-6">
            You have been invited to join <strong>{{ info.organization_name }}</strong>
          </p>

          <div class="bg-gray-50 rounded-lg p-4 mb-6 text-left">
            <div class="mb-3">
              <span class="text-gray-500 text-sm">Organization:</span>
              <div class="font-semibold text-lg">{{ info.organization_name }}</div>
            </div>
            <div class="mb-3">
              <span class="text-gray-500 text-sm">Invited as:</span>
              <div>
                <Tag :value="info.role" :severity="getRoleSeverity(info.role)" class="mt-1" />
              </div>
            </div>
            <div class="mb-3">
              <span class="text-gray-500 text-sm">Invited email:</span>
              <div>{{ info.invitee_email }}</div>
            </div>
            <div>
              <span class="text-gray-500 text-sm">Expires:</span>
              <div :class="{ 'text-red-600': isExpiringSoon }">
                {{ formatDate(info.expires_at) }}
                <span v-if="isExpiringSoon" class="text-sm">(Expires soon!)</span>
              </div>
            </div>
          </div>

          <Message v-if="!info.is_valid" severity="error">
            This invitation is no longer valid.
          </Message>

          <template v-else>
            <div class="flex flex-col gap-2">
              <Button
                label="Accept Invitation"
                icon="pi pi-check"
                @click="handleAccept"
              />
              <Button
                v-if="!isAuthenticated"
                label="Login to Accept"
                severity="secondary"
                icon="pi pi-sign-in"
                @click="handleLogin"
              />
            </div>
          </template>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth-store'
import { useOrganizationStore, type OrgRole } from '@/stores/organization-store'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const orgStore = useOrganizationStore()

const token = computed(() => route.params.token as string)

const loading = ref(true)
const error = ref<string | null>(null)
const info = ref<{
  organization_name: string
  invitee_email: string
  role: OrgRole
  expires_at: string
  is_valid: boolean
} | null>(null)

const isAuthenticated = computed(() => authStore.isAuthenticated)

const isExpiringSoon = computed(() => {
  if (!info.value) return false
  const expiresAt = new Date(info.value.expires_at)
  const now = new Date()
  const hoursUntilExpiry = (expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60)
  return hoursUntilExpiry < 24
})

onMounted(async () => {
  await loadInvitationInfo()
})

async function loadInvitationInfo() {
  loading.value = true
  error.value = null

  try {
    const result = await orgStore.getInvitationInfo(token.value)

    if (!result || !result.is_valid) {
      error.value = 'This invitation is invalid, expired, or has already been used.'
      return
    }

    info.value = result
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to load invitation details'
  } finally {
    loading.value = false
  }
}

function handleAccept() {
  // Redirect to accept page which handles login check
  router.push({ name: 'accept-invitation', params: { token: token.value } })
}

function handleLogin() {
  // Store redirect URL and go to login
  router.push({
    name: 'login',
    query: {
      redirect: `/invitations/accept/${token.value}`
    }
  })
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getRoleSeverity(role: OrgRole): 'success' | 'info' | 'secondary' | 'warning' {
  switch (role) {
    case 'owner': return 'success'
    case 'admin': return 'info'
    case 'member': return 'secondary'
    case 'viewer': return 'warning'
    default: return 'secondary'
  }
}
</script>
