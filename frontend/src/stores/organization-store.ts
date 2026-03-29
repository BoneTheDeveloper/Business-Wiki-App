/**
 * Organization store with Pinia.
 * Manages organization state, membership, and invitation operations.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

export type OrgRole = 'owner' | 'admin' | 'member' | 'viewer'
export type DocumentVisibility = 'public' | 'restricted' | 'private'

export interface Organization {
  id: string
  name: string
  slug: string
  owner_id: string
  max_documents: number
  max_storage_bytes: number
  current_documents: number
  current_storage_bytes: number
  settings: Record<string, unknown>
  is_active: boolean
  created_at: string
  member_count?: number
}

export interface OrganizationMember {
  id: string
  organization_id: string
  user_id: string
  role: OrgRole
  joined_at: string
  user?: {
    id: string
    email: string
    name?: string
    avatar_url?: string
  }
}

export interface Invitation {
  id: string
  organization_id: string
  invitee_email: string
  role: OrgRole
  created_at: string
  expires_at: string
  used: boolean
}

export interface Group {
  id: string
  organization_id: string
  name: string
  description?: string
  created_at: string
  member_count?: number
}

export interface GroupMember {
  id: string
  group_id: string
  user_id: string
  added_at: string
  user?: {
    id: string
    email: string
    name?: string
    avatar_url?: string
  }
}

export const useOrganizationStore = defineStore('organization', () => {
  // State
  const organizations = ref<Organization[]>([])
  const currentOrganization = ref<Organization | null>(null)
  const members = ref<OrganizationMember[]>([])
  const invitations = ref<Invitation[]>([])
  const groups = ref<Group[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const isOrgOwner = computed(() => {
    if (!currentOrganization.value) return false
    return currentOrganization.value.owner_id === localStorage.getItem('user_id')
  })

  const isOrgAdmin = computed(() => {
    const member = members.value.find(m => m.user_id === localStorage.getItem('user_id'))
    return member?.role === 'owner' || member?.role === 'admin'
  })

  const currentMemberRole = computed((): OrgRole | null => {
    const member = members.value.find(m => m.user_id === localStorage.getItem('user_id'))
    return member?.role || null
  })

  // Organization actions
  async function fetchOrganizations() {
    loading.value = true
    error.value = null

    try {
      const { data } = await api.get<Organization[]>('/organizations')
      organizations.value = data

      // Set current org if not set
      if (!currentOrganization.value && data.length > 0) {
        await setCurrentOrganization(data[0])
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to fetch organizations'
    } finally {
      loading.value = false
    }
  }

  async function getOrCreateDefaultOrganization(): Promise<Organization | null> {
    loading.value = true
    error.value = null

    try {
      const { data } = await api.get<Organization>('/organizations/default')
      if (!currentOrganization.value) {
        currentOrganization.value = data
      }
      return data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to get organization'
      return null
    } finally {
      loading.value = false
    }
  }

  async function createOrganization(name: string, slug?: string): Promise<Organization | null> {
    loading.value = true
    error.value = null

    try {
      const { data } = await api.post<Organization>('/organizations', { name, slug })
      organizations.value.push(data)
      return data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to create organization'
      return null
    } finally {
      loading.value = false
    }
  }

  async function setCurrentOrganization(org: Organization) {
    currentOrganization.value = org
    // Store in localStorage for persistence
    localStorage.setItem('current_org_id', org.id)

    // Fetch members and groups for this org
    await Promise.all([
      fetchMembers(org.id),
      fetchGroups(org.id)
    ])
  }

  async function fetchMembers(orgId: string) {
    try {
      const { data } = await api.get<OrganizationMember[]>(`/organizations/${orgId}/members`)
      members.value = data
    } catch (e) {
      console.error('Failed to fetch members:', e)
      members.value = []
    }
  }

  async function updateMemberRole(orgId: string, userId: string, role: OrgRole): Promise<boolean> {
    try {
      await api.patch(`/organizations/${orgId}/members/${userId}`, { role })
      await fetchMembers(orgId)
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to update member role'
      return false
    }
  }

  async function removeMember(orgId: string, userId: string): Promise<boolean> {
    try {
      await api.delete(`/organizations/${orgId}/members/${userId}`)
      await fetchMembers(orgId)
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to remove member'
      return false
    }
  }

  // Invitation actions
  async function fetchInvitations(orgId: string) {
    try {
      const { data } = await api.get<{ items: Invitation[] }>(`/invitations/organizations/${orgId}`)
      invitations.value = data.items
    } catch (e) {
      console.error('Failed to fetch invitations:', e)
      invitations.value = []
    }
  }

  async function sendInvitation(
    orgId: string,
    email: string,
    role: OrgRole
  ): Promise<Invitation | null> {
    try {
      const { data } = await api.post<Invitation>(
        `/invitations/organizations/${orgId}/invite`,
        { invitee_email: email, role }
      )
      invitations.value.push(data)
      return data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to send invitation'
      return null
    }
  }

  async function cancelInvitation(invitationId: string, orgId: string): Promise<boolean> {
    try {
      await api.delete(`/invitations/${invitationId}?org_id=${orgId}`)
      invitations.value = invitations.value.filter(i => i.id !== invitationId)
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to cancel invitation'
      return false
    }
  }

  async function getInvitationInfo(token: string): Promise<{
    organization_name: string
    invitee_email: string
    role: OrgRole
    expires_at: string
  } | null> {
    try {
      const { data } = await api.get(`/invitations/info/${token}`)
      return data
    } catch (e) {
      return null
    }
  }

  async function acceptInvitation(token: string): Promise<{ organization_id: string; organization_name: string } | null> {
    try {
      const { data } = await api.post('/invitations/accept', { token })
      // Refresh organizations list
      await fetchOrganizations()
      return data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to accept invitation'
      return null
    }
  }

  async function resendInvitation(invitationId: string, orgId: string): Promise<Invitation | null> {
    try {
      const { data } = await api.post<Invitation>(
        `/invitations/${invitationId}/resend`,
        null,
        { params: { org_id: orgId } }
      )
      // Update the invitation in the list
      const index = invitations.value.findIndex(i => i.id === invitationId)
      if (index !== -1) {
        invitations.value[index] = data
      }
      return data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to resend invitation'
      return null
    }
  }

  // Group actions
  async function fetchGroups(orgId: string) {
    try {
      const { data } = await api.get<Group[]>(`/organizations/${orgId}/groups`)
      groups.value = data
    } catch (e) {
      console.error('Failed to fetch groups:', e)
      groups.value = []
    }
  }

  async function createGroup(
    orgId: string,
    name: string,
    description?: string
  ): Promise<Group | null> {
    try {
      const { data } = await api.post<Group>(`/organizations/${orgId}/groups`, {
        name,
        description
      })
      groups.value.push(data)
      return data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to create group'
      return null
    }
  }

  async function deleteGroup(orgId: string, groupId: string): Promise<boolean> {
    try {
      await api.delete(`/organizations/${orgId}/groups/${groupId}`)
      groups.value = groups.value.filter(g => g.id !== groupId)
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to delete group'
      return false
    }
  }

  async function addGroupMember(
    orgId: string,
    groupId: string,
    userId: string
  ): Promise<boolean> {
    try {
      await api.post(`/organizations/${orgId}/groups/${groupId}/members`, {
        user_id: userId
      })
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to add member to group'
      return false
    }
  }

  async function removeGroupMember(
    orgId: string,
    groupId: string,
    userId: string
  ): Promise<boolean> {
    try {
      await api.delete(`/organizations/${orgId}/groups/${groupId}/members/${userId}`)
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to remove member from group'
      return false
    }
  }

  // Quota
  async function getQuotaUsage(orgId: string): Promise<{
    documents_used: number
    documents_limit: number
    storage_used_bytes: number
    storage_limit_bytes: number
    documents_percentage: number
    storage_percentage: number
  } | null> {
    try {
      const { data } = await api.get(`/organizations/${orgId}/quota`)
      return data
    } catch (e) {
      return null
    }
  }

  // Initialize - restore current org from localStorage
  async function init() {
    const currentOrgId = localStorage.getItem('current_org_id')
    if (currentOrgId) {
      const org = organizations.value.find(o => o.id === currentOrgId)
      if (org) {
        await setCurrentOrganization(org)
      }
    }
  }

  return {
    // State
    organizations,
    currentOrganization,
    members,
    invitations,
    groups,
    loading,
    error,

    // Computed
    isOrgOwner,
    isOrgAdmin,
    currentMemberRole,

    // Actions
    fetchOrganizations,
    getOrCreateDefaultOrganization,
    createOrganization,
    setCurrentOrganization,
    fetchMembers,
    updateMemberRole,
    removeMember,
    fetchInvitations,
    sendInvitation,
    cancelInvitation,
    getInvitationInfo,
    acceptInvitation,
    fetchGroups,
    createGroup,
    deleteGroup,
    addGroupMember,
    removeGroupMember,
    getQuotaUsage,
    init
  }
})
