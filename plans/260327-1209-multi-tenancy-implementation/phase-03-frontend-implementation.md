# Phase 3: Frontend Implementation

**Priority:** High
**Duration:** Week 4 (5 days)
**Status:** Pending
**Dependencies:** Phase 2 (Backend Services)

---

## Overview

Implement frontend UI components, stores, and views for multi-tenancy features.

### Key Objectives
- Organization management UI
- Member invitation flow
- Group management interface
- Document visibility controls
- Organization switching
- Permission-based UI rendering

---

## Requirements

### Functional Requirements
- Users can create and manage organizations
- Invite members via email form
- Accept invitation flow
- Create and manage groups
- Set document visibility
- View organization members

### Non-Functional Requirements
- Page load < 2 seconds
- Responsive design (mobile-friendly)
- Accessible (WCAG 2.1 AA)
- Real-time updates via WebSocket

---

## Architecture

### State Management

```
Pinia Stores
├── organization-store.ts (new)
│   ├── currentOrg
│   ├── members
│   ├── groups
│   └── invitations
├── auth-store.ts (update)
│   └── organizationId
└── document-store.ts (update)
    └── organizationFilter
```

### Component Structure

```
views/
├── OrganizationDashboardView.vue
├── OrganizationMembersView.vue
├── OrganizationGroupsView.vue
└── AcceptInvitationView.vue

components/
├── organizations/
│   ├── CreateOrganizationDialog.vue
│   ├── OrganizationSwitcher.vue
│   ├── InviteMemberDialog.vue
│   ├── MemberList.vue
│   └── GroupManager.vue
└── documents/
    ├── VisibilitySelector.vue
    ├── DocumentAccessManager.vue
    └── GroupSelector.vue
```

---

## Implementation Steps

### Step 1: Organization Store (Day 1)

**File:** `frontend/src/stores/organization-store.ts`

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Organization, Member, Group, Invitation } from '@/types/organization'
import { organizationApi } from '@/api/organization-api'
import { useToast } from 'primevue/usetoast'

export const useOrganizationStore = defineStore('organization', () => {
  const toast = useToast()

  // State
  const currentOrg = ref<Organization | null>(null)
  const organizations = ref<Organization[]>([])
  const members = ref<Member[]>([])
  const groups = ref<Group[]>([])
  const invitations = ref<Invitation[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const isAdmin = computed(() => {
    if (!currentOrg.value) return false
    const member = members.value.find(m => m.user_id === currentOrg.value?.owner_id)
    return member?.role === 'owner' || member?.role === 'admin'
  })

  const canInvite = computed(() => {
    if (!currentOrg.value) return false
    const member = members.value.find(m => m.user_id === currentOrg.value?.owner_id)
    return member?.role === 'owner' || member?.role === 'admin'
  })

  // Actions
  async function fetchOrganizations() {
    loading.value = true
    error.value = null

    try {
      const response = await organizationApi.list()
      organizations.value = response.data

      // Set current org if not set
      if (!currentOrg.value && organizations.value.length > 0) {
        await setCurrentOrg(organizations.value[0].id)
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch organizations'
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: error.value,
        life: 5000
      })
    } finally {
      loading.value = false
    }
  }

  async function setCurrentOrg(orgId: string) {
    loading.value = true
    error.value = null

    try {
      const response = await organizationApi.get(orgId)
      currentOrg.value = response.data

      // Fetch members and groups
      await Promise.all([
        fetchMembers(orgId),
        fetchGroups(orgId)
      ])

      // Store in localStorage
      localStorage.setItem('currentOrgId', orgId)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch organization'
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: error.value,
        life: 5000
      })
    } finally {
      loading.value = false
    }
  }

  async function createOrganization(data: { name: string; slug: string }) {
    loading.value = true
    error.value = null

    try {
      const response = await organizationApi.create(data)
      organizations.value.push(response.data)
      currentOrg.value = response.data

      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Organization created successfully',
        life: 3000
      })

      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to create organization'
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: error.value,
        life: 5000
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchMembers(orgId: string) {
    try {
      const response = await organizationApi.listMembers(orgId)
      members.value = response.data
    } catch (err: any) {
      console.error('Failed to fetch members:', err)
    }
  }

  async function inviteMember(email: string, role: string) {
    if (!currentOrg.value) return

    loading.value = true
    error.value = null

    try {
      const response = await organizationApi.invite(currentOrg.value.id, { email, role })
      invitations.value.push(response.data)

      toast.add({
        severity: 'success',
        summary: 'Invitation Sent',
        detail: `Invitation sent to ${email}`,
        life: 3000
      })

      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to send invitation'
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: error.value,
        life: 5000
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function removeMember(userId: string) {
    if (!currentOrg.value) return

    loading.value = true
    error.value = null

    try {
      await organizationApi.removeMember(currentOrg.value.id, userId)
      members.value = members.value.filter(m => m.user_id !== userId)

      toast.add({
        severity: 'success',
        summary: 'Member Removed',
        detail: 'Member has been removed from organization',
        life: 3000
      })
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to remove member'
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: error.value,
        life: 5000
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchGroups(orgId: string) {
    try {
      const response = await organizationApi.listGroups(orgId)
      groups.value = response.data
    } catch (err: any) {
      console.error('Failed to fetch groups:', err)
    }
  }

  async function createGroup(name: string, description?: string) {
    if (!currentOrg.value) return

    loading.value = true
    error.value = null

    try {
      const response = await organizationApi.createGroup(currentOrg.value.id, {
        name,
        description
      })
      groups.value.push(response.data)

      toast.add({
        severity: 'success',
        summary: 'Group Created',
        detail: `Group "${name}" created successfully`,
        life: 3000
      })

      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to create group'
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: error.value,
        life: 5000
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function acceptInvitation(token: string) {
    loading.value = true
    error.value = null

    try {
      const response = await organizationApi.acceptInvitation(token)
      const org = response.data

      // Add to organizations list
      organizations.value.push(org)

      // Set as current org
      currentOrg.value = org

      toast.add({
        severity: 'success',
        summary: 'Welcome!',
        detail: `You've joined ${org.name}`,
        life: 5000
      })

      return org
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to accept invitation'
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: error.value,
        life: 5000
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  function $reset() {
    currentOrg.value = null
    organizations.value = []
    members.value = []
    groups.value = []
    invitations.value = []
    loading.value = false
    error.value = null
  }

  return {
    // State
    currentOrg,
    organizations,
    members,
    groups,
    invitations,
    loading,
    error,

    // Computed
    isAdmin,
    canInvite,

    // Actions
    fetchOrganizations,
    setCurrentOrg,
    createOrganization,
    fetchMembers,
    inviteMember,
    removeMember,
    fetchGroups,
    createGroup,
    acceptInvitation,
    $reset
  }
})
```

---

### Step 2: Organization API Client (Day 1)

**File:** `frontend/src/api/organization-api.ts`

```typescript
import apiClient from './client'
import type {
  Organization,
  OrganizationCreate,
  Member,
  Group,
  GroupCreate,
  Invitation,
  InvitationCreate
} from '@/types/organization'

export const organizationApi = {
  // Organization CRUD
  list() {
    return apiClient.get<Organization[]>('/organizations')
  },

  get(orgId: string) {
    return apiClient.get<Organization>(`/organizations/${orgId}`)
  },

  create(data: OrganizationCreate) {
    return apiClient.post<Organization>('/organizations', data)
  },

  update(orgId: string, data: Partial<OrganizationCreate>) {
    return apiClient.patch<Organization>(`/organizations/${orgId}`, data)
  },

  delete(orgId: string) {
    return apiClient.delete(`/organizations/${orgId}`)
  },

  // Members
  listMembers(orgId: string) {
    return apiClient.get<Member[]>(`/organizations/${orgId}/members`)
  },

  invite(orgId: string, data: InvitationCreate) {
    return apiClient.post<Invitation>(`/organizations/${orgId}/invite`, data)
  },

  removeMember(orgId: string, userId: string) {
    return apiClient.delete(`/organizations/${orgId}/members/${userId}`)
  },

  updateMemberRole(orgId: string, userId: string, role: string) {
    return apiClient.patch(`/organizations/${orgId}/members/${userId}`, { role })
  },

  // Groups
  listGroups(orgId: string) {
    return apiClient.get<Group[]>(`/organizations/${orgId}/groups`)
  },

  createGroup(orgId: string, data: GroupCreate) {
    return apiClient.post<Group>(`/organizations/${orgId}/groups`, data)
  },

  updateGroup(groupId: string, data: Partial<GroupCreate>) {
    return apiClient.patch<Group>(`/groups/${groupId}`, data)
  },

  deleteGroup(groupId: string) {
    return apiClient.delete(`/groups/${groupId}`)
  },

  addGroupMember(groupId: string, userId: string) {
    return apiClient.post(`/groups/${groupId}/members`, { user_id: userId })
  },

  removeGroupMember(groupId: string, userId: string) {
    return apiClient.delete(`/groups/${groupId}/members/${userId}`)
  },

  // Invitations
  getInvitation(invitationId: string) {
    return apiClient.get<Invitation>(`/invitations/${invitationId}`)
  },

  acceptInvitation(token: string) {
    return apiClient.post<Organization>(`/invitations/${token}/accept`)
  },

  cancelInvitation(invitationId: string) {
    return apiClient.delete(`/invitations/${invitationId}`)
  },

  // Document Access
  grantDocumentAccess(docId: string, data: {
    user_id?: string
    group_id?: string
    access_level: 'view' | 'edit'
  }) {
    return apiClient.post(`/documents/${docId}/access`, data)
  },

  revokeDocumentAccess(docId: string, accessId: string) {
    return apiClient.delete(`/documents/${docId}/access/${accessId}`)
  },

  updateDocumentVisibility(docId: string, visibility: 'public' | 'restricted' | 'private') {
    return apiClient.patch(`/documents/${docId}/visibility`, null, {
      params: { visibility }
    })
  }
}
```

---

### Step 3: Organization Dashboard View (Day 2)

**File:** `frontend/src/views/OrganizationDashboardView.vue`

```vue
<template>
  <div class="organization-dashboard">
    <div class="grid">
      <!-- Organization Info -->
      <div class="col-12 md:col-6 lg:col-4">
        <Card>
          <template #title>
            <div class="flex align-items-center gap-2">
              <i class="pi pi-building"></i>
              <span>{{ orgStore.currentOrg?.name }}</span>
            </div>
          </template>
          <template #content>
            <div class="organization-stats">
              <div class="stat-item">
                <span class="stat-label">Members</span>
                <span class="stat-value">{{ orgStore.members.length }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Documents</span>
                <span class="stat-value">{{ orgStore.currentOrg?.current_documents || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Storage</span>
                <span class="stat-value">
                  {{ formatBytes(orgStore.currentOrg?.current_storage_bytes || 0) }}
                </span>
              </div>
            </div>

            <div class="quota-progress mt-4">
              <label>Storage Quota</label>
              <ProgressBar
                :value="storagePercent"
                :showValue="false"
                :class="{ 'quota-warning': storagePercent > 80 }"
              />
              <small class="quota-text">
                {{ formatBytes(orgStore.currentOrg?.current_storage_bytes || 0) }} /
                {{ formatBytes(orgStore.currentOrg?.max_storage_bytes || 0) }}
              </small>
            </div>
          </template>
        </Card>
      </div>

      <!-- Quick Actions -->
      <div class="col-12 md:col-6 lg:col-4">
        <Card>
          <template #title>Quick Actions</template>
          <template #content>
            <div class="action-buttons">
              <Button
                label="Invite Member"
                icon="pi pi-user-plus"
                @click="showInviteDialog = true"
                :disabled="!orgStore.canInvite"
                class="w-full mb-2"
              />
              <Button
                label="Create Group"
                icon="pi pi-users"
                @click="showGroupDialog = true"
                class="w-full mb-2"
              />
              <Button
                label="Upload Document"
                icon="pi pi-upload"
                @click="navigateToUpload"
                class="w-full"
              />
            </div>
          </template>
        </Card>
      </div>

      <!-- Recent Activity -->
      <div class="col-12 lg:col-4">
        <Card>
          <template #title>Recent Activity</template>
          <template #content>
            <div class="activity-list">
              <div v-if="recentActivity.length === 0" class="no-activity">
                <i class="pi pi-clock"></i>
                <p>No recent activity</p>
              </div>
              <div
                v-for="activity in recentActivity"
                :key="activity.id"
                class="activity-item"
              >
                <i :class="getActivityIcon(activity.type)"></i>
                <div class="activity-content">
                  <p>{{ activity.message }}</p>
                  <small>{{ formatTime(activity.timestamp) }}</small>
                </div>
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Members Section -->
      <div class="col-12">
        <Card>
          <template #title>
            <div class="flex justify-content-between align-items-center">
              <span>Members</span>
              <Button
                label="Manage"
                icon="pi pi-cog"
                @click="navigateToMembers"
                text
              />
            </div>
          </template>
          <template #content>
            <DataTable :value="orgStore.members.slice(0, 5)" :rows="5">
              <Column field="user_email" header="Email"></Column>
              <Column field="user_name" header="Name"></Column>
              <Column field="role" header="Role">
                <template #body="{ data }">
                  <Tag
                    :value="data.role"
                    :severity="getRoleSeverity(data.role)"
                  />
                </template>
              </Column>
              <Column field="joined_at" header="Joined">
                <template #body="{ data }">
                  {{ formatDate(data.joined_at) }}
                </template>
              </Column>
            </DataTable>
          </template>
        </Card>
      </div>
    </div>

    <!-- Invite Dialog -->
    <InviteMemberDialog
      v-model="showInviteDialog"
      @invited="handleMemberInvited"
    />

    <!-- Group Dialog -->
    <CreateGroupDialog
      v-model="showGroupDialog"
      @created="handleGroupCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOrganizationStore } from '@/stores/organization-store'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import InviteMemberDialog from '@/components/organizations/InviteMemberDialog.vue'
import CreateGroupDialog from '@/components/organizations/CreateGroupDialog.vue'
import { formatBytes, formatDate, formatTime } from '@/utils/formatters'

const router = useRouter()
const orgStore = useOrganizationStore()

const showInviteDialog = ref(false)
const showGroupDialog = ref(false)
const recentActivity = ref<any[]>([])

const storagePercent = computed(() => {
  if (!orgStore.currentOrg) return 0
  const used = orgStore.currentOrg.current_storage_bytes
  const max = orgStore.currentOrg.max_storage_bytes
  return Math.round((used / max) * 100)
})

onMounted(async () => {
  await orgStore.fetchOrganizations()
  await loadRecentActivity()
})

function navigateToUpload() {
  router.push('/documents/upload')
}

function navigateToMembers() {
  router.push(`/organizations/${orgStore.currentOrg?.id}/members`)
}

function handleMemberInvited() {
  showInviteDialog.value = false
  orgStore.fetchMembers(orgStore.currentOrg!.id)
}

function handleGroupCreated() {
  showGroupDialog.value = false
  orgStore.fetchGroups(orgStore.currentOrg!.id)
}

function getRoleSeverity(role: string) {
  const severities: Record<string, any> = {
    owner: 'danger',
    admin: 'warning',
    member: 'success',
    viewer: 'info'
  }
  return severities[role] || 'secondary'
}

function getActivityIcon(type: string) {
  const icons: Record<string, string> = {
    document_upload: 'pi pi-upload',
    member_join: 'pi pi-user-plus',
    group_create: 'pi pi-users'
  }
  return icons[type] || 'pi pi-info-circle'
}

async function loadRecentActivity() {
  // TODO: Implement activity feed API
  recentActivity.value = []
}
</script>

<style scoped>
.organization-dashboard {
  padding: 1rem;
}

.organization-stats {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.stat-value {
  font-weight: 600;
  font-size: 1.25rem;
}

.quota-progress {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.quota-text {
  color: var(--text-color-secondary);
}

.quota-warning :deep(.p-progressbar-value) {
  background-color: var(--orange-500);
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.activity-item {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}

.activity-content {
  flex: 1;
}

.activity-content p {
  margin: 0;
  font-size: 0.875rem;
}

.activity-content small {
  color: var(--text-color-secondary);
}

.no-activity {
  text-align: center;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.no-activity i {
  font-size: 2rem;
  margin-bottom: 0.5rem;
  opacity: 0.5;
}
</style>
```

---

### Step 4: Invite Member Dialog (Day 2)

**File:** `frontend/src/components/organizations/InviteMemberDialog.vue`

```vue
<template>
  <Dialog
    v-model:visible="dialogVisible"
    modal
    header="Invite Member"
    :style="{ width: '450px' }"
    @hide="resetForm"
  >
    <form @submit.prevent="handleSubmit">
      <div class="field">
        <label for="email">Email Address</label>
        <InputText
          id="email"
          v-model="form.email"
          type="email"
          placeholder="user@example.com"
          class="w-full"
          :class="{ 'p-invalid': errors.email }"
          required
        />
        <small v-if="errors.email" class="p-error">{{ errors.email }}</small>
      </div>

      <div class="field">
        <label for="role">Role</label>
        <Dropdown
          id="role"
          v-model="form.role"
          :options="roleOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Select role"
          class="w-full"
        />
        <small class="helper-text">
          <i class="pi pi-info-circle"></i>
          {{ getRoleDescription(form.role) }}
        </small>
      </div>

      <div class="field">
        <label>Role Permissions</label>
        <div class="permission-info">
          <div class="permission-item">
            <Tag :value="form.role" :severity="getRoleSeverity(form.role)" />
            <span>{{ getRoleSummary(form.role) }}</span>
          </div>
        </div>
      </div>
    </form>

    <template #footer>
      <Button
        label="Cancel"
        icon="pi pi-times"
        @click="dialogVisible = false"
        text
      />
      <Button
        label="Send Invitation"
        icon="pi pi-envelope"
        @click="handleSubmit"
        :loading="loading"
        autofocus
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'
import { useOrganizationStore } from '@/stores/organization-store'

interface Props {
  modelValue: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'invited': []
}>()

const orgStore = useOrganizationStore()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const form = ref({
  email: '',
  role: 'member'
})

const errors = ref({
  email: ''
})

const loading = ref(false)

const roleOptions = [
  { label: 'Admin', value: 'admin' },
  { label: 'Member', value: 'member' },
  { label: 'Viewer', value: 'viewer' }
]

function getRoleDescription(role: string): string {
  const descriptions: Record<string, string> = {
    admin: 'Can invite members, manage groups, and view all documents',
    member: 'Can upload documents and create groups',
    viewer: 'Can only view public documents'
  }
  return descriptions[role] || ''
}

function getRoleSummary(role: string): string {
  const summaries: Record<string, string> = {
    admin: 'Full access except owner actions',
    member: 'Upload, edit own docs, view shared',
    viewer: 'View public documents only'
  }
  return summaries[role] || ''
}

function getRoleSeverity(role: string) {
  const severities: Record<string, any> = {
    admin: 'warning',
    member: 'success',
    viewer: 'info'
  }
  return severities[role] || 'secondary'
}

function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

async function handleSubmit() {
  // Validate
  errors.value.email = ''

  if (!form.value.email) {
    errors.value.email = 'Email is required'
    return
  }

  if (!validateEmail(form.value.email)) {
    errors.value.email = 'Invalid email address'
    return
  }

  loading.value = true

  try {
    await orgStore.inviteMember(form.value.email, form.value.role)
    emit('invited')
    dialogVisible.value = false
  } catch (error) {
    // Error handled in store
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.value = {
    email: '',
    role: 'member'
  }
  errors.value = {
    email: ''
  }
}
</script>

<style scoped>
.field {
  margin-bottom: 1.5rem;
}

.helper-text {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-color-secondary);
  margin-top: 0.5rem;
}

.permission-info {
  background: var(--surface-50);
  padding: 1rem;
  border-radius: var(--border-radius);
}

.permission-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
</style>
```

---

### Step 5: Document Visibility Selector (Day 3)

**File:** `frontend/src/components/documents/VisibilitySelector.vue`

```vue
<template>
  <div class="visibility-selector">
    <label class="field-label">Document Visibility</label>

    <div class="visibility-options">
      <div
        v-for="option in visibilityOptions"
        :key="option.value"
        class="visibility-option"
        :class="{ 'selected': modelValue === option.value }"
        @click="selectVisibility(option.value)"
      >
        <div class="option-header">
          <i :class="option.icon" class="option-icon"></i>
          <RadioButton
            :value="option.value"
            :modelValue="modelValue"
            @update:modelValue="selectVisibility"
          />
        </div>
        <div class="option-content">
          <h4>{{ option.label }}</h4>
          <p>{{ option.description }}</p>
        </div>
      </div>
    </div>

    <!-- Access Configuration for Restricted -->
    <div v-if="modelValue === 'restricted'" class="access-config">
      <label class="field-label">Grant Access To</label>

      <TabView>
        <TabPanel header="Users">
          <div class="user-selector">
            <MultiSelect
              v-model="selectedUsers"
              :options="availableUsers"
              optionLabel="email"
              optionValue="id"
              placeholder="Select users"
              class="w-full"
              filter
            />
          </div>
        </TabPanel>

        <TabPanel header="Groups">
          <div class="group-selector">
            <MultiSelect
              v-model="selectedGroups"
              :options="availableGroups"
              optionLabel="name"
              optionValue="id"
              placeholder="Select groups"
              class="w-full"
            />
          </div>
        </TabPanel>
      </TabView>

      <div class="access-level-selector">
        <label>Access Level</label>
        <SelectButton
          v-model="accessLevel"
          :options="accessLevelOptions"
          optionLabel="label"
          optionValue="value"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import RadioButton from 'primevue/radiobutton'
import MultiSelect from 'primevue/multiselect'
import SelectButton from 'primevue/selectbutton'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import { useOrganizationStore } from '@/stores/organization-store'

interface Props {
  modelValue: 'public' | 'restricted' | 'private'
  documentId?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: 'public' | 'restricted' | 'private']
  'accessChange': [config: any]
}>()

const orgStore = useOrganizationStore()

const selectedUsers = ref<string[]>([])
const selectedGroups = ref<string[]>([])
const accessLevel = ref<'view' | 'edit'>('view')

const visibilityOptions = [
  {
    value: 'public',
    label: 'Public',
    icon: 'pi pi-globe',
    description: 'All organization members can view this document'
  },
  {
    value: 'restricted',
    label: 'Restricted',
    icon: 'pi pi-lock',
    description: 'Only selected users or groups can access'
  },
  {
    value: 'private',
    label: 'Private',
    icon: 'pi pi-shield',
    description: 'Only you and admins can access this document'
  }
]

const accessLevelOptions = [
  { label: 'View Only', value: 'view' },
  { label: 'Can Edit', value: 'edit' }
]

const availableUsers = computed(() => {
  return orgStore.members.map(m => ({
    id: m.user_id,
    email: m.user_email,
    name: m.user_name
  }))
})

const availableGroups = computed(() => {
  return orgStore.groups
})

function selectVisibility(value: 'public' | 'restricted' | 'private') {
  emit('update:modelValue', value)
}

watch([selectedUsers, selectedGroups, accessLevel], () => {
  if (props.modelValue === 'restricted') {
    emit('accessChange', {
      users: selectedUsers.value,
      groups: selectedGroups.value,
      accessLevel: accessLevel.value
    })
  }
}, { deep: true })
</script>

<style scoped>
.visibility-selector {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field-label {
  font-weight: 600;
  margin-bottom: 0.5rem;
  display: block;
}

.visibility-options {
  display: grid;
  gap: 0.75rem;
}

.visibility-option {
  border: 2px solid var(--surface-border);
  border-radius: var(--border-radius);
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.visibility-option:hover {
  border-color: var(--primary-color);
  background: var(--surface-50);
}

.visibility-option.selected {
  border-color: var(--primary-color);
  background: var(--primary-color-light);
}

.option-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.option-icon {
  font-size: 1.5rem;
  color: var(--primary-color);
}

.option-content h4 {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
}

.option-content p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.access-config {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}

.access-level-selector {
  margin-top: 1rem;
}

.access-level-selector label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}
</style>
```

---

### Step 6: Update Router (Day 4)

**File:** `frontend/src/router/index.ts` (modify existing)

```typescript
// Add organization routes

{
  path: '/organizations',
  component: () => import('@/views/OrganizationsLayout.vue'),
  children: [
    {
      path: '',
      name: 'organization-list',
      component: () => import('@/views/OrganizationsListView.vue')
    },
    {
      path: 'create',
      name: 'organization-create',
      component: () => import('@/views/CreateOrganizationView.vue')
    },
    {
      path: ':orgId',
      name: 'organization-dashboard',
      component: () => import('@/views/OrganizationDashboardView.vue'),
      meta: { requiresOrg: true }
    },
    {
      path: ':orgId/members',
      name: 'organization-members',
      component: () => import('@/views/OrganizationMembersView.vue'),
      meta: { requiresOrg: true, requiresAdmin: true }
    },
    {
      path: ':orgId/groups',
      name: 'organization-groups',
      component: () => import('@/views/OrganizationGroupsView.vue'),
      meta: { requiresOrg: true }
    }
  ]
},
{
  path: '/invitations/:token/accept',
  name: 'accept-invitation',
  component: () => import('@/views/AcceptInvitationView.vue'),
  meta: { requiresAuth: true }
}
```

---

## Testing Checklist

- [ ] Organization creation works
- [ ] Organization switching works
- [ ] Member invitation sends email
- [ ] Invitation acceptance joins org
- [ ] Group creation works
- [ ] Document visibility can be set
- [ ] Access grants work for restricted docs
- [ ] Permission-based UI hides/shows correctly
- [ ] Responsive on mobile devices
- [ ] All forms validate correctly

---

## Next Phase

→ [Phase 4: Security & RLS](./phase-04-security-rls.md)
