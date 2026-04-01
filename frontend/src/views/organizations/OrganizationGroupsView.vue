<template>
  <div class="organization-groups-view p-6">
    <div class="max-w-4xl mx-auto">
      <!-- Header -->
      <div class="flex justify-between items-center mb-6">
        <div class="flex items-center gap-3">
          <Button
            icon="pi pi-arrow-left"
            severity="secondary"
            text
            @click="router.push({ name: 'organization-detail', params: { id: orgId } })"
          />
          <h1 class="text-2xl font-bold text-gray-900">Groups</h1>
        </div>
        <Button
          v-if="canManageGroups"
          label="Create Group"
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
        v-else-if="groups.length === 0"
        class="text-center py-12 bg-gray-50 rounded-lg"
      >
        <i class="pi pi-sitemap text-6xl text-gray-300 mb-4"></i>
        <h2 class="text-xl font-semibold text-gray-700 mb-2">No groups yet</h2>
        <p class="text-gray-500 mb-4">
          Groups help you organize members and manage document access
        </p>
        <Button
          v-if="canManageGroups"
          label="Create Group"
          icon="pi pi-plus"
          @click="showCreateDialog = true"
        />
      </div>

      <!-- Groups Grid -->
      <div v-else class="grid gap-4 md:grid-cols-2">
        <Card
          v-for="group in groups"
          :key="group.id"
          class="cursor-pointer hover:shadow-md transition-shadow"
          @click="openGroupDetail(group)"
        >
          <template #content>
            <div class="flex justify-between items-start mb-3">
              <div>
                <h3 class="text-lg font-semibold text-gray-900">{{ group.name }}</h3>
                <p class="text-sm text-gray-500">{{ group.description || 'No description' }}</p>
              </div>
              <Button
                v-if="canManageGroups"
                icon="pi pi-ellipsis-v"
                severity="secondary"
                text
                @click.stop="showGroupMenu($event, group)"
              />
            </div>
            <div class="flex items-center gap-2 text-sm text-gray-600">
              <i class="pi pi-users"></i>
              <span>{{ group.member_count || 0 }} members</span>
            </div>
          </template>
        </Card>
      </div>

      <!-- Create Group Dialog -->
      <Dialog
        v-model:visible="showCreateDialog"
        modal
        header="Create Group"
        :style="{ width: '450px' }"
      >
        <form @submit.prevent="handleCreate" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Group Name *
            </label>
            <InputText
              v-model="newGroupName"
              placeholder="Engineering Team"
              class="w-full"
              required
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <Textarea
              v-model="newGroupDescription"
              placeholder="Optional description..."
              rows="3"
              class="w-full"
            />
          </div>

          <Message v-if="createError" severity="error">{{ createError }}</Message>

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

      <!-- Group Detail Dialog -->
      <Dialog
        v-model:visible="showDetailDialog"
        modal
        :header="selectedGroup?.name || 'Group Details'"
        :style="{ width: '600px' }"
      >
        <template v-if="selectedGroup">
          <p class="text-gray-600 mb-4">{{ selectedGroup.description || 'No description' }}</p>

          <div class="flex justify-between items-center mb-3">
            <h4 class="font-semibold">Members ({{ groupMembers.length }})</h4>
            <Button
              v-if="canManageGroups"
              label="Add Member"
              icon="pi pi-plus"
              size="small"
              @click="showAddMemberDialog = true"
            />
          </div>

          <div v-if="loadingMembers" class="flex justify-center py-4">
            <ProgressSpinner style="width: 30px; height: 30px" />
          </div>

          <div v-else-if="groupMembers.length === 0" class="text-center py-4 text-gray-500">
            No members in this group
          </div>

          <div v-else class="space-y-2 max-h-60 overflow-y-auto">
            <div
              v-for="member in groupMembers"
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
              <Button
                v-if="canManageGroups"
                icon="pi pi-times"
                severity="secondary"
                text
                size="small"
                @click="handleRemoveMember(member)"
              />
            </div>
          </div>
        </template>
      </Dialog>

      <!-- Add Member Dialog -->
      <Dialog
        v-model:visible="showAddMemberDialog"
        modal
        header="Add Member to Group"
        :style="{ width: '450px' }"
      >
        <form @submit.prevent="handleAddMember" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Select Member *
            </label>
            <Dropdown
              v-model="addMemberUserId"
              :options="availableMembers"
              optionLabel="label"
              optionValue="value"
              placeholder="Choose a member..."
              class="w-full"
              filter
            />
          </div>

          <Message v-if="addMemberError" severity="error">{{ addMemberError }}</Message>

          <div class="flex justify-end gap-2">
            <Button
              label="Cancel"
              severity="secondary"
              @click="showAddMemberDialog = false"
            />
            <Button
              type="submit"
              label="Add"
              :loading="addingMember"
            />
          </div>
        </form>
      </Dialog>

      <!-- Group Menu -->
      <Menu ref="groupMenuRef" :model="groupMenuItems" :popup="true" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useOrganizationStore, type Group, type GroupMember } from '@/stores/organization-store'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import Avatar from 'primevue/avatar'
import Message from 'primevue/message'
import Menu from 'primevue/menu'
import ProgressSpinner from 'primevue/progressspinner'

const route = useRoute()
const router = useRouter()
const orgStore = useOrganizationStore()

const orgId = route.params.id as string
const groups = ref<Group[]>([])
const members = ref<{ id: string; user_id: string; user?: { id: string; email: string; name?: string } }[]>([])
const loading = ref(true)

const showCreateDialog = ref(false)
const newGroupName = ref('')
const newGroupDescription = ref('')
const creating = ref(false)
const createError = ref<string | null>(null)

const showDetailDialog = ref(false)
const selectedGroup = ref<Group | null>(null)
const groupMembers = ref<GroupMember[]>([])
const loadingMembers = ref(false)

const showAddMemberDialog = ref(false)
const addMemberUserId = ref<string>('')
const addingMember = ref(false)
const addMemberError = ref<string | null>(null)

const groupMenuRef = ref()
const groupMenuItems = ref<any[]>([])

const currentRole = computed(() => orgStore.currentMemberRole)

const canManageGroups = computed(() =>
  currentRole.value === 'owner' || currentRole.value === 'admin' || currentRole.value === 'member'
)

const availableMembers = computed(() => {
  // Filter out members already in the group
  const groupMemberIds = new Set(groupMembers.value.map(m => m.user_id))
  return members.value
    .filter(m => !groupMemberIds.has(m.user_id))
    .map(m => ({
      label: m.user?.name || m.user?.email || m.user_id,
      value: m.user_id
    }))
})

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true

  try {
    await orgStore.fetchGroups(orgId)
    groups.value = orgStore.groups

    await orgStore.fetchMembers(orgId)
    members.value = orgStore.members
  } catch (e) {
    console.error('Failed to load groups:', e)
  } finally {
    loading.value = false
  }
}

async function openGroupDetail(group: Group) {
  selectedGroup.value = group
  showDetailDialog.value = true
  loadingMembers.value = true

  try {
    const { data } = await orgStore.fetchGroupMembers(orgId, group.id)
    groupMembers.value = data
  } catch (e) {
    groupMembers.value = []
  } finally {
    loadingMembers.value = false
  }
}

function showGroupMenu(event: Event, group: Group) {
  selectedGroup.value = group

  groupMenuItems.value = [
    {
      label: 'Edit',
      icon: 'pi pi-pencil',
      command: () => { /* TODO: Edit group */ }
    },
    {
      separator: true
    },
    {
      label: 'Delete',
      icon: 'pi pi-trash',
      class: 'text-red-500',
      command: () => handleDeleteGroup(group)
    }
  ]

  groupMenuRef.value.toggle(event)
}

async function handleCreate() {
  if (!newGroupName.value.trim()) return

  creating.value = true
  createError.value = null

  try {
    const result = await orgStore.createGroup(
      orgId,
      newGroupName.value.trim(),
      newGroupDescription.value.trim() || undefined
    )

    if (result) {
      showCreateDialog.value = false
      newGroupName.value = ''
      newGroupDescription.value = ''
      groups.value = orgStore.groups
    } else {
      createError.value = orgStore.error || 'Failed to create group'
    }
  } finally {
    creating.value = false
  }
}

async function handleDeleteGroup(group: Group) {
  if (!confirm(`Delete group "${group.name}"? This will remove all member assignments.`)) return

  const success = await orgStore.deleteGroup(orgId, group.id)
  if (success) {
    groups.value = groups.value.filter(g => g.id !== group.id)
  }
}

async function handleAddMember() {
  if (!addMemberUserId.value || !selectedGroup.value) return

  addingMember.value = true
  addMemberError.value = null

  try {
    const success = await orgStore.addGroupMember(
      orgId,
      selectedGroup.value.id,
      addMemberUserId.value
    )

    if (success) {
      showAddMemberDialog.value = false
      addMemberUserId.value = ''
      // Refresh group members
      await openGroupDetail(selectedGroup.value)
    } else {
      addMemberError.value = orgStore.error || 'Failed to add member'
    }
  } finally {
    addingMember.value = false
  }
}

async function handleRemoveMember(member: GroupMember) {
  if (!selectedGroup.value) return

  if (!confirm(`Remove ${member.user?.email} from this group?`)) return

  const success = await orgStore.removeGroupMember(
    orgId,
    selectedGroup.value.id,
    member.user_id
  )

  if (success) {
    groupMembers.value = groupMembers.value.filter(m => m.id !== member.id)
  }
}
</script>
