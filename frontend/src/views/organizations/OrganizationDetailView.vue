<template>
  <div class="organization-detail-view p-6">
    <div class="max-w-4xl mx-auto">
      <!-- Loading state -->
      <div v-if="loading" class="flex justify-center py-8">
        <ProgressSpinner />
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="text-center py-12">
        <i class="pi pi-exclamation-triangle text-6xl text-red-300 mb-4"></i>
        <h2 class="text-xl font-semibold text-gray-700 mb-2">Error Loading Organization</h2>
        <p class="text-gray-500">{{ error }}</p>
        <Button label="Go Back" icon="pi pi-arrow-left" @click="router.back()" class="mt-4" />
      </div>

      <template v-else-if="organization">
        <!-- Header -->
        <div class="flex justify-between items-start mb-6">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">{{ organization.name }}</h1>
            <p class="text-gray-500">{{ organization.slug }}</p>
          </div>
          <Button
            v-if="isOrgAdmin"
            label="Settings"
            icon="pi pi-cog"
            severity="secondary"
            @click="router.push({ name: 'organization-settings', params: { id: organization.id } })"
          />
        </div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card>
            <template #content>
              <div class="text-center">
                <i class="pi pi-users text-3xl text-blue-500 mb-2"></i>
                <div class="text-2xl font-bold">{{ memberCount }}</div>
                <div class="text-sm text-gray-500">Members</div>
              </div>
            </template>
          </Card>

          <Card>
            <template #content>
              <div class="text-center">
                <i class="pi pi-file text-3xl text-green-500 mb-2"></i>
                <div class="text-2xl font-bold">
                  {{ organization.current_documents }} / {{ organization.max_documents }}
                </div>
                <div class="text-sm text-gray-500">Documents</div>
                <ProgressBar
                  :value="documentUsagePercent"
                  :showValue="false"
                  class="h-2 mt-2"
                  :class="{ 'p-progressbar-value-warning': documentUsagePercent > 80 }"
                />
              </div>
            </template>
          </Card>

          <Card>
            <template #content>
              <div class="text-center">
                <i class="pi pi-database text-3xl text-purple-500 mb-2"></i>
                <div class="text-2xl font-bold">{{ formatStorage(organization.current_storage_bytes) }}</div>
                <div class="text-sm text-gray-500">of {{ formatStorage(organization.max_storage_bytes) }}</div>
                <ProgressBar
                  :value="storageUsagePercent"
                  :showValue="false"
                  class="h-2 mt-2"
                  :class="{ 'p-progressbar-value-warning': storageUsagePercent > 80 }"
                />
              </div>
            </template>
          </Card>
        </div>

        <!-- Quick Actions -->
        <Card class="mb-6">
          <template #title>Quick Actions</template>
          <template #content>
            <div class="flex flex-wrap gap-2">
              <Button
                label="View Members"
                icon="pi pi-users"
                severity="secondary"
                @click="router.push({ name: 'organization-members', params: { id: organization.id } })"
              />
              <Button
                label="Manage Groups"
                icon="pi pi-sitemap"
                severity="secondary"
                @click="router.push({ name: 'organization-groups', params: { id: organization.id } })"
              />
              <Button
                v-if="isOrgAdmin"
                label="Invite Member"
                icon="pi pi-user-plus"
                @click="showInviteDialog = true"
              />
            </div>
          </template>
        </Card>

        <!-- Recent Members -->
        <Card>
          <template #title>Recent Members</template>
          <template #content>
            <div v-if="members.length === 0" class="text-center py-4 text-gray-500">
              No members yet
            </div>
            <div v-else class="space-y-2">
              <div
                v-for="member in members.slice(0, 5)"
                :key="member.id"
                class="flex justify-between items-center p-2 hover:bg-gray-50 rounded"
              >
                <div class="flex items-center gap-3">
                  <Avatar
                    :label="member.user?.name?.charAt(0) || member.user?.email?.charAt(0) || '?'"
                    shape="circle"
                  />
                  <div>
                    <div class="font-medium">{{ member.user?.name || member.user?.email }}</div>
                    <div class="text-sm text-gray-500">{{ member.user?.email }}</div>
                  </div>
                </div>
                <Tag :value="member.role" :severity="getRoleSeverity(member.role)" />
              </div>
            </div>
            <Button
              v-if="members.length > 5"
              label="View All Members"
              link
              @click="router.push({ name: 'organization-members', params: { id: organization.id } })"
            />
          </template>
        </Card>
      </template>

      <!-- Invite Dialog -->
      <Dialog
        v-model:visible="showInviteDialog"
        modal
        header="Invite Member"
        :style="{ width: '450px' }"
      >
        <form @submit.prevent="handleInvite" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Email Address *
            </label>
            <InputText
              v-model="inviteEmail"
              type="email"
              placeholder="user@example.com"
              class="w-full"
              required
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Role *
            </label>
            <Select
              v-model="inviteRole"
              :options="roleOptions"
              optionLabel="label"
              optionValue="value"
              class="w-full"
            />
          </div>

          <Message v-if="inviteError" severity="error">{{ inviteError }}</Message>

          <div class="flex justify-end gap-2">
            <Button
              label="Cancel"
              severity="secondary"
              @click="showInviteDialog = false"
            />
            <Button
              type="submit"
              label="Send Invitation"
              :loading="inviting"
            />
          </div>
        </form>
      </Dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useOrganizationStore, type OrgRole } from '@/stores/organization-store'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Avatar from 'primevue/avatar'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'

const route = useRoute()
const router = useRouter()
const orgStore = useOrganizationStore()

const organization = ref(orgStore.currentOrganization)
const members = ref(orgStore.members)
const loading = ref(true)
const error = ref<string | null>(null)
const memberCount = ref(0)

const showInviteDialog = ref(false)
const inviteEmail = ref('')
const inviteRole = ref<OrgRole>('member')
const inviting = ref(false)
const inviteError = ref<string | null>(null)

const roleOptions = [
  { label: 'Admin', value: 'admin' },
  { label: 'Member', value: 'member' },
  { label: 'Viewer', value: 'viewer' }
]

const isOrgAdmin = computed(() => {
  const role = orgStore.currentMemberRole
  return role === 'owner' || role === 'admin'
})

const documentUsagePercent = computed(() => {
  if (!organization.value) return 0
  return Math.round((organization.value.current_documents / organization.value.max_documents) * 100)
})

const storageUsagePercent = computed(() => {
  if (!organization.value) return 0
  return Math.round((organization.value.current_storage_bytes / organization.value.max_storage_bytes) * 100)
})

onMounted(async () => {
  const orgId = route.params.id as string

  try {
    if (!orgStore.currentOrganization || orgStore.currentOrganization.id !== orgId) {
      await orgStore.fetchOrganizations()
      const org = orgStore.organizations.find(o => o.id === orgId)
      if (org) {
        await orgStore.setCurrentOrganization(org)
      } else {
        throw new Error('Organization not found')
      }
    }

    organization.value = orgStore.currentOrganization
    members.value = orgStore.members
    memberCount.value = await orgStore.getMemberCount(orgId) || orgStore.members.length
  } catch (e: any) {
    error.value = e.message || 'Failed to load organization'
  } finally {
    loading.value = false
  }
})

async function handleInvite() {
  if (!inviteEmail.value.trim()) return

  inviting.value = true
  inviteError.value = null

  try {
    const result = await orgStore.sendInvitation(
      organization.value!.id,
      inviteEmail.value.trim(),
      inviteRole.value
    )

    if (result) {
      showInviteDialog.value = false
      inviteEmail.value = ''
      inviteRole.value = 'member'
    } else {
      inviteError.value = orgStore.error || 'Failed to send invitation'
    }
  } finally {
    inviting.value = false
  }
}

function formatStorage(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
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
