<template>
  <div class="organization-members-view p-6">
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
          <h1 class="text-2xl font-bold text-gray-900">Members</h1>
        </div>
        <Button
          v-if="canManageMembers"
          label="Invite Member"
          icon="pi pi-user-plus"
          @click="showInviteDialog = true"
        />
      </div>

      <!-- Loading state -->
      <div v-if="loading" class="flex justify-center py-8">
        <ProgressSpinner />
      </div>

      <template v-else>
        <!-- Members Table -->
        <Card>
          <template #content>
            <DataTable :value="members" stripedRows>
              <Column field="user.email" header="User" style="min-width: 250px">
                <template #body="{ data }">
                  <div class="flex items-center gap-3">
                    <Avatar
                      :label="data.user?.name?.charAt(0) || data.user?.email?.charAt(0) || '?'"
                      shape="circle"
                    />
                    <div>
                      <div class="font-medium">{{ data.user?.name || data.user?.email }}</div>
                      <div class="text-sm text-gray-500">{{ data.user?.email }}</div>
                    </div>
                  </div>
                </template>
              </Column>

              <Column field="role" header="Role" style="width: 150px">
                <template #body="{ data }">
                  <Tag :value="data.role" :severity="getRoleSeverity(data.role)" />
                </template>
              </Column>

              <Column field="joined_at" header="Joined" style="width: 150px">
                <template #body="{ data }">
                  {{ formatDate(data.joined_at) }}
                </template>
              </Column>

              <Column header="Actions" style="width: 120px" v-if="canManageMembers">
                <template #body="{ data }">
                  <Button
                    v-if="canManageUser(data)"
                    icon="pi pi-ellipsis-v"
                    severity="secondary"
                    text
                    @click="showMemberMenu($event, data)"
                  />
                </template>
              </Column>
            </DataTable>
          </template>
        </Card>

        <!-- Pending Invitations -->
        <Card v-if="invitations.length > 0 && canManageMembers" class="mt-6">
          <template #title>Pending Invitations</template>
          <template #content>
            <DataTable :value="invitations" stripedRows>
              <Column field="invitee_email" header="Email" />
              <Column field="role" header="Role">
                <template #body="{ data }">
                  <Tag :value="data.role" :severity="getRoleSeverity(data.role)" />
                </template>
              </Column>
              <Column field="created_at" header="Sent">
                <template #body="{ data }">
                  {{ formatDate(data.created_at) }}
                </template>
              </Column>
              <Column field="expires_at" header="Expires">
                <template #body="{ data }">
                  {{ formatDate(data.expires_at) }}
                </template>
              </Column>
              <Column header="Actions" style="width: 150px">
                <template #body="{ data }">
                  <div class="flex gap-1">
                    <Button
                      icon="pi pi-refresh"
                      severity="secondary"
                      text
                      v-tooltip="'Resend'"
                      @click="handleResendInvitation(data)"
                    />
                    <Button
                      icon="pi pi-times"
                      severity="danger"
                      text
                      v-tooltip="'Cancel'"
                      @click="handleCancelInvitation(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
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
              :options="availableRoles"
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

      <!-- Member Menu -->
      <Menu ref="memberMenuRef" :model="memberMenuItems" :popup="true" />

      <!-- Change Role Dialog -->
      <Dialog
        v-model:visible="showRoleDialog"
        modal
        header="Change Role"
        :style="{ width: '400px' }"
      >
        <form @submit.prevent="handleUpdateRole" class="space-y-4">
          <p class="text-gray-600">
            Change role for <strong>{{ selectedMember?.user?.email }}</strong>
          </p>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              New Role *
            </label>
            <Select
              v-model="newRole"
              :options="availableRolesForChange"
              optionLabel="label"
              optionValue="value"
              class="w-full"
            />
          </div>

          <Message v-if="roleError" severity="error">{{ roleError }}</Message>

          <div class="flex justify-end gap-2">
            <Button
              label="Cancel"
              severity="secondary"
              @click="showRoleDialog = false"
            />
            <Button
              type="submit"
              label="Update"
              :loading="updatingRole"
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
import { useOrganizationStore, type OrgRole, type OrganizationMember, type Invitation } from '@/stores/organization-store'
import Button from 'primevue/button'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Avatar from 'primevue/avatar'
import Message from 'primevue/message'
import Menu from 'primevue/menu'
import ProgressSpinner from 'primevue/progressspinner'

const route = useRoute()
const router = useRouter()
const orgStore = useOrganizationStore()

const orgId = route.params.id as string
const members = ref<OrganizationMember[]>([])
const invitations = ref<Invitation[]>([])
const loading = ref(true)

const showInviteDialog = ref(false)
const inviteEmail = ref('')
const inviteRole = ref<OrgRole>('member')
const inviting = ref(false)
const inviteError = ref<string | null>(null)

const showRoleDialog = ref(false)
const selectedMember = ref<OrganizationMember | null>(null)
const newRole = ref<OrgRole>('member')
const updatingRole = ref(false)
const roleError = ref<string | null>(null)

const memberMenuRef = ref()
const memberMenuItems = ref<any[]>([])

const currentRole = computed(() => orgStore.currentMemberRole)

const canManageMembers = computed(() =>
  currentRole.value === 'owner' || currentRole.value === 'admin'
)

const availableRoles = computed(() => {
  // Cannot invite as owner
  const roles = [
    { label: 'Admin', value: 'admin' as OrgRole },
    { label: 'Member', value: 'member' as OrgRole },
    { label: 'Viewer', value: 'viewer' as OrgRole }
  ]
  return roles
})

const availableRolesForChange = computed(() => {
  const roles = availableRoles.value
  // Cannot change to owner
  return roles.filter(r => r.value !== 'owner')
})

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true

  try {
    await orgStore.fetchMembers(orgId)
    members.value = orgStore.members

    if (canManageMembers.value) {
      await orgStore.fetchInvitations(orgId)
      invitations.value = orgStore.invitations
    }
  } catch (e) {
    console.error('Failed to load members:', e)
  } finally {
    loading.value = false
  }
}

function canManageUser(member: OrganizationMember): boolean {
  // Cannot manage owners
  if (member.role === 'owner') return false

  // Admins can manage members and viewers
  if (currentRole.value === 'admin') {
    return member.role === 'member' || member.role === 'viewer'
  }

  // Only owners can manage admins
  return currentRole.value === 'owner'
}

function showMemberMenu(event: Event, member: OrganizationMember) {
  selectedMember.value = member
  newRole.value = member.role

  memberMenuItems.value = [
    {
      label: 'Change Role',
      icon: 'pi pi-pencil',
      command: () => { showRoleDialog.value = true }
    },
    {
      separator: true
    },
    {
      label: 'Remove',
      icon: 'pi pi-trash',
      class: 'text-red-500',
      command: () => handleRemoveMember(member)
    }
  ]

  memberMenuRef.value.toggle(event)
}

async function handleInvite() {
  if (!inviteEmail.value.trim()) return

  inviting.value = true
  inviteError.value = null

  try {
    const result = await orgStore.sendInvitation(
      orgId,
      inviteEmail.value.trim(),
      inviteRole.value
    )

    if (result) {
      showInviteDialog.value = false
      inviteEmail.value = ''
      inviteRole.value = 'member'
      await orgStore.fetchInvitations(orgId)
      invitations.value = orgStore.invitations
    } else {
      inviteError.value = orgStore.error || 'Failed to send invitation'
    }
  } finally {
    inviting.value = false
  }
}

async function handleUpdateRole() {
  if (!selectedMember.value || !newRole.value) return

  updatingRole.value = true
  roleError.value = null

  try {
    const success = await orgStore.updateMemberRole(
      orgId,
      selectedMember.value.user_id,
      newRole.value
    )

    if (success) {
      showRoleDialog.value = false
      members.value = orgStore.members
    } else {
      roleError.value = orgStore.error || 'Failed to update role'
    }
  } finally {
    updatingRole.value = false
  }
}

async function handleRemoveMember(member: OrganizationMember) {
  if (!confirm(`Remove ${member.user?.email} from this organization?`)) return

  const success = await orgStore.removeMember(orgId, member.user_id)
  if (success) {
    members.value = orgStore.members
  }
}

async function handleResendInvitation(invitation: Invitation) {
  const success = await orgStore.resendInvitation(invitation.id, orgId)
  if (success !== null) {
    await orgStore.fetchInvitations(orgId)
    invitations.value = orgStore.invitations
  }
}

async function handleCancelInvitation(invitation: Invitation) {
  if (!confirm(`Cancel invitation to ${invitation.invitee_email}?`)) return

  const success = await orgStore.cancelInvitation(invitation.id, orgId)
  if (success) {
    invitations.value = invitations.value.filter(i => i.id !== invitation.id)
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString()
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
