<template>
  <div class="organization-list-view p-6">
    <div class="max-w-4xl mx-auto">
      <!-- Header -->
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Organizations</h1>
        <Button
          label="Create Organization"
          icon="pi pi-plus"
          @click="showCreateDialog = true"
        />
      </div>

      <!-- Loading state -->
      <div v-if="loading" class="flex justify-center py-8">
        <ProgressSpinner />
      </div>

      <!-- Empty state -->
      <div
        v-else-if="organizations.length === 0"
        class="text-center py-12 bg-gray-50 rounded-lg"
      >
        <i class="pi pi-building text-6xl text-gray-300 mb-4"></i>
        <h2 class="text-xl font-semibold text-gray-700 mb-2">No organizations yet</h2>
        <p class="text-gray-500 mb-4">Create your first organization to get started</p>
        <Button
          label="Create Organization"
          icon="pi pi-plus"
          @click="showCreateDialog = true"
        />
      </div>

      <!-- Organization list -->
      <div v-else class="grid gap-4">
        <Card
          v-for="org in organizations"
          :key="org.id"
          class="cursor-pointer hover:shadow-md transition-shadow"
          @click="selectOrganization(org)"
        >
          <template #content>
            <div class="flex justify-between items-start">
              <div>
                <h3 class="text-lg font-semibold text-gray-900">{{ org.name }}</h3>
                <p class="text-sm text-gray-500">{{ org.slug }}</p>
                <div class="flex items-center gap-4 mt-2 text-sm text-gray-600">
                  <span>
                    <i class="pi pi-users mr-1"></i>
                    {{ org.member_count || 0 }} members
                  </span>
                  <span>
                    <i class="pi pi-file mr-1"></i>
                    {{ org.current_documents }} / {{ org.max_documents }} docs
                  </span>
                </div>
              </div>
              <Tag
                v-if="currentOrganization?.id === org.id"
                value="Active"
                severity="success"
              />
            </div>
          </template>
        </Card>
      </div>

      <!-- Create Organization Dialog -->
      <Dialog
        v-model:visible="showCreateDialog"
        modal
        header="Create Organization"
        :style="{ width: '450px' }"
      >
        <form @submit.prevent="handleCreate" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Organization Name *
            </label>
            <InputText
              v-model="newOrgName"
              placeholder="My Organization"
              class="w-full"
              required
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              URL Slug (optional)
            </label>
            <InputText
              v-model="newOrgSlug"
              placeholder="my-organization"
              class="w-full"
            />
            <p class="text-xs text-gray-500 mt-1">
              Leave empty to auto-generate from name
            </p>
          </div>

          <Message v-if="error" severity="error">{{ error }}</Message>

          <div class="flex justify-end gap-2">
            <Button
              label="Cancel"
              severity="secondary"
              @click="showCreateDialog = false"
            />
            <Button
              type="submit"
              label="Create"
              :loading="creating"
            />
          </div>
        </form>
      </Dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOrganizationStore, type Organization } from '@/stores/organization-store'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'

const router = useRouter()
const orgStore = useOrganizationStore()

const organizations = ref<Organization[]>([])
const currentOrganization = ref<Organization | null>(null)
const loading = ref(true)
const showCreateDialog = ref(false)
const newOrgName = ref('')
const newOrgSlug = ref('')
const creating = ref(false)
const error = ref<string | null>(null)

onMounted(async () => {
  await loadOrganizations()
})

async function loadOrganizations() {
  loading.value = true
  await orgStore.fetchOrganizations()
  organizations.value = orgStore.organizations
  currentOrganization.value = orgStore.currentOrganization
  loading.value = false
}

async function handleCreate() {
  if (!newOrgName.value.trim()) return

  creating.value = true
  error.value = null

  try {
    const org = await orgStore.createOrganization(
      newOrgName.value.trim(),
      newOrgSlug.value.trim() || undefined
    )

    if (org) {
      showCreateDialog.value = false
      newOrgName.value = ''
      newOrgSlug.value = ''
      await loadOrganizations()
    } else {
      error.value = orgStore.error || 'Failed to create organization'
    }
  } finally {
    creating.value = false
  }
}

function selectOrganization(org: Organization) {
  orgStore.setCurrentOrganization(org)
  router.push({ name: 'organization-detail', params: { id: org.id } })
}
</script>
