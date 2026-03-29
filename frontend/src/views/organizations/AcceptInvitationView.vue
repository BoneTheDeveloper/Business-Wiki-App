<template>
  <div class="accept-invitation-view min-h-screen flex items-center justify-center bg-gray-50">
    <div class="max-w-md w-full p-6">
      <!-- Loading state -->
      <Card v-if="loading" class="text-center">
        <template #content>
          <ProgressSpinner class="mb-4" />
          <p class="text-gray-600">Processing invitation...</p>
        </template>
      </Card>

      <!-- Error state -->
      <Card v-else-if="error" class="text-center">
        <template #content>
          <i class="pi pi-exclamation-triangle text-6xl text-red-300 mb-4"></i>
          <h2 class="text-xl font-semibold text-gray-900 mb-2">Invalid Invitation</h2>
          <p class="text-gray-600 mb-4">{{ error }}</p>
          <div class="flex justify-center gap-2">
            <Button
              label="Go to Login"
              @click="router.push({ name: 'login' })"
            />
            <Button
              v-if="isAuthenticated"
              label="Go to Dashboard"
              severity="secondary"
              @click="router.push({ name: 'dashboard' })"
            />
          </div>
        </template>
      </Card>

      <!-- Success state -->
      <Card v-else-if="success" class="text-center">
        <template #content>
          <i class="pi pi-check-circle text-6xl text-green-500 mb-4"></i>
          <h2 class="text-xl font-semibold text-gray-900 mb-2">Welcome!</h2>
          <p class="text-gray-600 mb-4">
            You've successfully joined <strong>{{ organizationName }}</strong>
          </p>
          <Button
            label="Go to Organization"
            @click="router.push({ name: 'organization-detail', params: { id: organizationId } })"
          />
        </template>
      </Card>

      <!-- Preview state -->
      <Card v-else-if="invitationInfo" class="text-center">
        <template #content>
          <i class="pi pi-building text-6xl text-blue-500 mb-4"></i>
          <h2 class="text-xl font-semibold text-gray-900 mb-2">
            Invitation to Join
          </h2>
          <div class="bg-gray-50 rounded-lg p-4 mb-4 text-left">
            <div class="mb-2">
              <span class="text-gray-500 text-sm">Organization:</span>
              <div class="font-semibold">{{ invitationInfo.organization_name }}</div>
            </div>
            <div class="mb-2">
              <span class="text-gray-500 text-sm">Email:</span>
              <div>{{ invitationInfo.invitee_email }}</div>
            </div>
            <div class="mb-2">
              <span class="text-gray-500 text-sm">Role:</span>
              <Tag :value="invitationInfo.role" :severity="getRoleSeverity(invitationInfo.role)" class="ml-1" />
            </div>
            <div>
              <span class="text-gray-500 text-sm">Expires:</span>
              <div>{{ formatDate(invitationInfo.expires_at) }}</div>
            </div>
          </div>

          <!-- If not logged in -->
          <template v-if="!isAuthenticated">
            <p class="text-gray-600 mb-4">
              Please log in or create an account to accept this invitation.
            </p>
            <div class="flex justify-center gap-2">
              <Button
                label="Login"
                @click="router.push({ name: 'login', query: { redirect: route.fullPath } })"
              />
              <Button
                label="Register"
                severity="secondary"
                @click="router.push({ name: 'register', query: { redirect: route.fullPath } })"
              />
            </div>
          </template>

          <!-- If logged in -->
          <template v-else>
            <Message v-if="emailMismatch" severity="warn">
              This invitation was sent to <strong>{{ invitationInfo.invitee_email }}</strong>,
              but you're logged in as <strong>{{ currentUserEmail }}</strong>.
            </Message>

            <Button
              v-else
              label="Accept Invitation"
              :loading="accepting"
              @click="handleAccept"
            />
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
const invitationInfo = ref<{
  organization_name: string
  invitee_email: string
  role: OrgRole
  expires_at: string
  is_valid: boolean
} | null>(null)

const accepting = ref(false)
const success = ref(false)
const organizationId = ref('')
const organizationName = ref('')

const isAuthenticated = computed(() => authStore.isAuthenticated)
const currentUserEmail = computed(() => authStore.user?.email)

const emailMismatch = computed(() => {
  if (!invitationInfo.value || !currentUserEmail.value) return false
  return invitationInfo.value.invitee_email.toLowerCase() !== currentUserEmail.value.toLowerCase()
})

onMounted(async () => {
  await loadInvitationInfo()
})

async function loadInvitationInfo() {
  loading.value = true
  error.value = null

  try {
    const info = await orgStore.getInvitationInfo(token.value)

    if (!info || !info.is_valid) {
      error.value = 'This invitation is invalid or has expired.'
      return
    }

    invitationInfo.value = info

    // If authenticated, try to accept automatically
    if (isAuthenticated.value && !emailMismatch.value) {
      await handleAccept()
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to load invitation'
  } finally {
    loading.value = false
  }
}

async function handleAccept() {
  accepting.value = true
  error.value = null

  try {
    const result = await orgStore.acceptInvitation(token.value)

    if (result) {
      success.value = true
      organizationId.value = result.organization_id
      organizationName.value = result.organization_name
    } else {
      error.value = orgStore.error || 'Failed to accept invitation'
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to accept invitation'
  } finally {
    accepting.value = false
  }
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
