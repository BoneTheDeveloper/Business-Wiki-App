<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth-store'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Dropdown from 'primevue/dropdown'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import ProgressSpinner from 'primevue/progressspinner'
import api from '@/api/client'

const authStore = useAuthStore()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()

interface User {
  id: string
  email: string
  role: string
  is_active: boolean
  created_at: string
}

interface Stats {
  total_documents: number
  total_users: number
  active_users: number
  total_chunks: number
  queries_today: number
  documents_by_status: Record<string, number>
  documents_by_format: Record<string, number>
}

const loading = ref(true)
const users = ref<User[]>([])
const stats = ref<Stats | null>(null)

const roles = [
  { label: 'User', value: 'user' },
  { label: 'Editor', value: 'editor' },
  { label: 'Admin', value: 'admin' }
]

onMounted(async () => {
  if (!authStore.isAdmin) {
    router.push('/')
    return
  }
  await loadData()
})

async function loadData() {
  loading.value = true
  try {
    const [usersRes, statsRes] = await Promise.all([
      api.get('/admin/users', { params: { limit: 100 } }),
      api.get('/admin/stats')
    ])
    users.value = usersRes.data.items
    stats.value = statsRes.data
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load admin data' })
  } finally {
    loading.value = false
  }
}

async function changeRole(user: User, newRole: string) {
  try {
    await api.patch(`/admin/users/${user.id}`, { role: newRole })
    user.role = newRole
    toast.add({ severity: 'success', summary: 'Updated', detail: 'User role changed' })
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail })
  }
}

function confirmToggleActive(user: User) {
  confirm.require({
    message: user.is_active
      ? `Disable account for ${user.email}?`
      : `Enable account for ${user.email}?`,
    header: user.is_active ? 'Disable User' : 'Enable User',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: user.is_active ? 'p-button-danger' : 'p-button-success',
    accept: async () => {
      try {
        await api.patch(`/admin/users/${user.id}`, { is_active: !user.is_active })
        user.is_active = !user.is_active
        toast.add({ severity: 'success', summary: 'Updated', detail: 'User status changed' })
      } catch (error: any) {
        toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail })
      }
    }
  })
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString()
}
</script>

<template>
  <Toast />
  <ConfirmDialog />

  <div class="p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">Admin Dashboard</h1>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12">
      <ProgressSpinner />
    </div>

    <template v-else>
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <template #content>
            <p class="text-sm text-gray-500">Total Documents</p>
            <p class="text-3xl font-bold text-blue-600">{{ stats?.total_documents || 0 }}</p>
          </template>
        </Card>
        <Card>
          <template #content>
            <p class="text-sm text-gray-500">Active Users</p>
            <p class="text-3xl font-bold text-green-600">{{ stats?.active_users || 0 }}</p>
          </template>
        </Card>
        <Card>
          <template #content>
            <p class="text-sm text-gray-500">Total Chunks</p>
            <p class="text-3xl font-bold text-purple-600">{{ stats?.total_chunks || 0 }}</p>
          </template>
        </Card>
        <Card>
          <template #content>
            <p class="text-sm text-gray-500">Queries Today</p>
            <p class="text-3xl font-bold text-orange-600">{{ stats?.queries_today || 0 }}</p>
          </template>
        </Card>
      </div>

      <!-- User Management -->
      <Card class="mb-6">
        <template #title>User Management</template>
        <template #content>
          <DataTable :value="users" stripedRows paginator :rows="10">
            <Column field="email" header="Email" sortable />
            <Column field="role" header="Role" sortable>
              <template #body="{ data }">
                <Dropdown
                  v-model="data.role"
                  :options="roles"
                  optionLabel="label"
                  optionValue="value"
                  size="small"
                  @change="changeRole(data, data.role)"
                />
              </template>
            </Column>
            <Column field="is_active" header="Status" sortable>
              <template #body="{ data }">
                <Tag
                  :value="data.is_active ? 'Active' : 'Disabled'"
                  :severity="data.is_active ? 'success' : 'danger'"
                />
              </template>
            </Column>
            <Column field="created_at" header="Created" sortable>
              <template #body="{ data }">
                {{ formatDate(data.created_at) }}
              </template>
            </Column>
            <Column header="Actions">
              <template #body="{ data }">
                <Button
                  :label="data.is_active ? 'Disable' : 'Enable'"
                  :severity="data.is_active ? 'danger' : 'success'"
                  size="small"
                  outlined
                  @click="confirmToggleActive(data)"
                />
              </template>
            </Column>
          </DataTable>
        </template>
      </Card>

      <!-- Document Stats -->
      <Card>
        <template #title>Document Statistics</template>
        <template #content>
          <div class="grid grid-cols-2 gap-6">
            <div>
              <h4 class="font-semibold mb-3">By Status</h4>
              <div class="space-y-2">
                <div v-for="(count, status) in stats?.documents_by_status" :key="status" class="flex justify-between">
                  <span class="capitalize">{{ status }}</span>
                  <span class="font-medium">{{ count }}</span>
                </div>
              </div>
            </div>
            <div>
              <h4 class="font-semibold mb-3">By Format</h4>
              <div class="space-y-2">
                <div v-for="(count, format) in stats?.documents_by_format" :key="format" class="flex justify-between">
                  <span class="uppercase">{{ format }}</span>
                  <span class="font-medium">{{ count }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </Card>
    </template>
  </div>
</template>
