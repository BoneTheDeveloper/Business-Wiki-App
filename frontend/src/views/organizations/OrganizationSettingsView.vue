<template>
  <div class="organization-settings-view p-6">
    <div class="max-w-2xl mx-auto">
      <!-- Header -->
      <div class="flex justify-between items-center mb-6">
        <div class="flex items-center gap-3">
          <Button
            icon="pi pi-arrow-left"
            severity="secondary"
            text
            @click="router.push({ name: 'organization-detail', params: { id: orgId } })"
          />
          <h1 class="text-2xl font-bold text-gray-900">Settings</h1>
        </div>
      </div>

      <!-- Loading state -->
      <div v-if="loading" class="flex justify-center py-8">
        <ProgressSpinner />
      </div>

      <!-- Permission denied -->
      <Card v-else-if="!canManage" class="text-center">
        <template #content>
          <i class="pi pi-lock text-6xl text-gray-300 mb-4"></i>
          <h2 class="text-xl font-semibold text-gray-700 mb-2">Access Denied</h2>
          <p class="text-gray-500">Only organization owners and admins can access settings.</p>
        </template>
      </Card>

      <template v-else-if="organization">
        <!-- General Settings -->
        <Card class="mb-6">
          <template #title>General Settings</template>
          <template #content>
            <form @submit.prevent="handleUpdateGeneral" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Organization Name
                </label>
                <InputText
                  v-model="form.name"
                  class="w-full"
                  :disabled="!isOwner"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  URL Slug
                </label>
                <InputText
                  v-model="form.slug"
                  class="w-full"
                  :disabled="!isOwner"
                />
                <p class="text-xs text-gray-500 mt-1">
                  Changing the slug will break existing links
                </p>
              </div>

              <Message v-if="generalError" severity="error">{{ generalError }}</Message>

              <div class="flex justify-end">
                <Button
                  type="submit"
                  label="Save Changes"
                  :loading="updatingGeneral"
                  :disabled="!hasGeneralChanges"
                />
              </div>
            </form>
          </template>
        </Card>

        <!-- Quota Information (Read-only) -->
        <Card class="mb-6">
          <template #title>Quota & Usage</template>
          <template #content>
            <div class="space-y-4">
              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span>Documents</span>
                  <span>{{ organization.current_documents }} / {{ organization.max_documents }}</span>
                </div>
                <ProgressBar
                  :value="documentUsagePercent"
                  :showValue="false"
                  :class="{ 'p-progressbar-value-warning': documentUsagePercent > 80 }"
                />
              </div>

              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span>Storage</span>
                  <span>{{ formatStorage(organization.current_storage_bytes) }} / {{ formatStorage(organization.max_storage_bytes) }}</span>
                </div>
                <ProgressBar
                  :value="storageUsagePercent"
                  :showValue="false"
                  :class="{ 'p-progressbar-value-warning': storageUsagePercent > 80 }"
                />
              </div>

              <Message v-if="documentUsagePercent > 80 || storageUsagePercent > 80" severity="warn">
                You're approaching your quota limits. Consider upgrading your plan.
              </Message>
            </div>
          </template>
        </Card>

        <!-- Danger Zone -->
        <Card v-if="isOwner" class="border-red-200">
          <template #title>
            <span class="text-red-600">Danger Zone</span>
          </template>
          <template #content>
            <div class="space-y-4">
              <div class="flex justify-between items-center">
                <div>
                  <h4 class="font-medium">Transfer Ownership</h4>
                  <p class="text-sm text-gray-500">Transfer this organization to another member</p>
                </div>
                <Button
                  label="Transfer"
                  severity="danger"
                  outlined
                  @click="showTransferDialog = true"
                />
              </div>

              <Divider />

              <div class="flex justify-between items-center">
                <div>
                  <h4 class="font-medium text-red-600">Delete Organization</h4>
                  <p class="text-sm text-gray-500">
                    Permanently delete this organization and all its data
                  </p>
                </div>
                <Button
                  label="Delete"
                  severity="danger"
                  @click="showDeleteDialog = true"
                />
              </div>
            </div>
          </template>
        </Card>

        <!-- Transfer Ownership Dialog -->
        <Dialog
          v-model:visible="showTransferDialog"
          modal
          header="Transfer Ownership"
          :style="{ width: '450px' }"
        >
          <form @submit.prevent="handleTransfer" class="space-y-4">
            <Message severity="warn">
              This will transfer full ownership to another member. You will become an admin.
            </Message>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                New Owner *
              </label>
              <Dropdown
                v-model="transferToUserId"
                :options="adminMembers"
                optionLabel="label"
                optionValue="value"
                placeholder="Select a member..."
                class="w-full"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Type "TRANSFER" to confirm *
              </label>
              <InputText
                v-model="transferConfirm"
                placeholder="TRANSFER"
                class="w-full"
              />
            </div>

            <Message v-if="transferError" severity="error">{{ transferError }}</Message>

            <div class="flex justify-end gap-2">
              <Button
                label="Cancel"
                severity="secondary"
                @click="showTransferDialog = false"
              />
              <Button
                type="submit"
                label="Transfer"
                severity="danger"
                :loading="transferring"
                :disabled="transferConfirm !== 'TRANSFER'"
              />
            </div>
          </form>
        </Dialog>

        <!-- Delete Organization Dialog -->
        <Dialog
          v-model:visible="showDeleteDialog"
          modal
          header="Delete Organization"
          :style="{ width: '450px' }"
        >
          <form @submit.prevent="handleDelete" class="space-y-4">
            <Message severity="error">
              This action cannot be undone. All documents, members, and data will be permanently deleted.
            </Message>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Type the organization name "{{ organization.name }}" to confirm *
              </label>
              <InputText
                v-model="deleteConfirm"
                :placeholder="organization.name"
                class="w-full"
              />
            </div>

            <Message v-if="deleteError" severity="error">{{ deleteError }}</Message>

            <div class="flex justify-end gap-2">
              <Button
                label="Cancel"
                severity="secondary"
                @click="showDeleteDialog = false"
              />
              <Button
                type="submit"
                label="Delete Organization"
                severity="danger"
                :loading="deleting"
                :disabled="deleteConfirm !== organization.name"
              />
            </div>
          </form>
        </Dialog>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useOrganizationStore, type OrgRole } from '@/stores/organization-store'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Message from 'primevue/message'
import Divider from 'primevue/divider'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'

const route = useRoute()
const router = useRouter()
const orgStore = useOrganizationStore()

const orgId = route.params.id as string
const organization = ref(orgStore.currentOrganization)
const members = ref(orgStore.members)
const loading = ref(true)

const form = reactive({
  name: '',
  slug: ''
})

const updatingGeneral = ref(false)
const generalError = ref<string | null>(null)

const showTransferDialog = ref(false)
const transferToUserId = ref('')
const transferConfirm = ref('')
const transferring = ref(false)
const transferError = ref<string | null>(null)

const showDeleteDialog = ref(false)
const deleteConfirm = ref('')
const deleting = ref(false)
const deleteError = ref<string | null>(null)

const currentRole = computed(() => orgStore.currentMemberRole)

const isOwner = computed(() => currentRole.value === 'owner')
const canManage = computed(() => isOwner.value || currentRole.value === 'admin')

const hasGeneralChanges = computed(() =>
  form.name !== organization.value?.name ||
  form.slug !== organization.value?.slug
)

const documentUsagePercent = computed(() => {
  if (!organization.value) return 0
  return Math.round((organization.value.current_documents / organization.value.max_documents) * 100)
})

const storageUsagePercent = computed(() => {
  if (!organization.value) return 0
  return Math.round((organization.value.current_storage_bytes / organization.value.max_storage_bytes) * 100)
})

const adminMembers = computed(() =>
  members.value
    .filter(m => m.role === 'admin' && m.user_id !== orgStore.currentMember?.user_id)
    .map(m => ({
      label: m.user?.name || m.user?.email || m.user_id,
      value: m.user_id
    }))
)

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true

  try {
    if (!orgStore.currentOrganization || orgStore.currentOrganization.id !== orgId) {
      await orgStore.fetchOrganizations()
      const org = orgStore.organizations.find(o => o.id === orgId)
      if (org) {
        await orgStore.setCurrentOrganization(org)
      }
    }

    organization.value = orgStore.currentOrganization
    members.value = orgStore.members

    if (organization.value) {
      form.name = organization.value.name
      form.slug = organization.value.slug
    }
  } catch (e) {
    console.error('Failed to load organization:', e)
  } finally {
    loading.value = false
  }
}

async function handleUpdateGeneral() {
  if (!hasGeneralChanges.value) return

  updatingGeneral.value = true
  generalError.value = null

  try {
    const success = await orgStore.updateOrganization(orgId, {
      name: form.name,
      slug: form.slug
    })

    if (success) {
      organization.value = orgStore.currentOrganization
    } else {
      generalError.value = orgStore.error || 'Failed to update settings'
    }
  } finally {
    updatingGeneral.value = false
  }
}

async function handleTransfer() {
  if (transferConfirm.value !== 'TRANSFER' || !transferToUserId.value) return

  transferring.value = true
  transferError.value = null

  try {
    const success = await orgStore.transferOwnership(orgId, transferToUserId.value)

    if (success) {
      showTransferDialog.value = false
      router.push({ name: 'organization-detail', params: { id: orgId } })
    } else {
      transferError.value = orgStore.error || 'Failed to transfer ownership'
    }
  } finally {
    transferring.value = false
  }
}

async function handleDelete() {
  if (deleteConfirm.value !== organization.value?.name) return

  deleting.value = true
  deleteError.value = null

  try {
    const success = await orgStore.deleteOrganization(orgId)

    if (success) {
      router.push({ name: 'organizations' })
    } else {
      deleteError.value = orgStore.error || 'Failed to delete organization'
    }
  } finally {
    deleting.value = false
  }
}

function formatStorage(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}
</script>
