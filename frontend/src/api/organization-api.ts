/**
 * Organization API client.
 * Provides typed API calls for organization, member, invitation, and group operations.
 */
import api from './client'
import type { OrgRole, DocumentVisibility } from '@/stores/organization-store'

// Types
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

export interface QuotaUsage {
  documents_used: number
  documents_limit: number
  storage_used_bytes: number
  storage_limit_bytes: number
  documents_percentage: number
  storage_percentage: number
}

// Organization API
export const organizationApi = {
  // Organizations
  async list(): Promise<Organization[]> {
    const { data } = await api.get<Organization[]>('/organizations')
    return data
  },

  async get(orgId: string): Promise<Organization> {
    const { data } = await api.get<Organization>(`/organizations/${orgId}`)
    return data
  },

  async getDefault(): Promise<Organization> {
    const { data } = await api.get<Organization>('/organizations/default')
    return data
  },

  async create(name: string, slug?: string): Promise<Organization> {
    const { data } = await api.post<Organization>('/organizations', { name, slug })
    return data
  },

  async update(orgId: string, updates: { name?: string; settings?: Record<string, unknown> }): Promise<Organization> {
    const { data } = await api.patch<Organization>(`/organizations/${orgId}`, updates)
    return data
  },

  async getQuota(orgId: string): Promise<QuotaUsage> {
    const { data } = await api.get<QuotaUsage>(`/organizations/${orgId}/quota`)
    return data
  },

  // Members
  async listMembers(orgId: string): Promise<OrganizationMember[]> {
    const { data } = await api.get<OrganizationMember[]>(`/organizations/${orgId}/members`)
    return data
  },

  async addMember(orgId: string, userId: string, role: OrgRole): Promise<OrganizationMember> {
    const { data } = await api.post<OrganizationMember>(`/organizations/${orgId}/members`, {
      user_id: userId,
      role
    })
    return data
  },

  async updateMemberRole(orgId: string, userId: string, role: OrgRole): Promise<OrganizationMember> {
    const { data } = await api.patch<OrganizationMember>(
      `/organizations/${orgId}/members/${userId}`,
      { role }
    )
    return data
  },

  async removeMember(orgId: string, userId: string): Promise<void> {
    await api.delete(`/organizations/${orgId}/members/${userId}`)
  }
}

// Invitation API
export const invitationApi = {
  async list(orgId: string, includeUsed = false): Promise<Invitation[]> {
    const { data } = await api.get<{ items: Invitation[] }>(
      `/invitations/organizations/${orgId}`,
      { params: { include_used: includeUsed } }
    )
    return data.items
  },

  async send(orgId: string, email: string, role: OrgRole): Promise<Invitation> {
    const { data } = await api.post<Invitation>(
      `/invitations/organizations/${orgId}/invite`,
      { invitee_email: email, role }
    )
    return data
  },

  async cancel(invitationId: string, orgId: string): Promise<void> {
    await api.delete(`/invitations/${invitationId}`, { params: { org_id: orgId } })
  },

  async resend(invitationId: string, orgId: string): Promise<Invitation> {
    const { data } = await api.post<Invitation>(
      `/invitations/${invitationId}/resend`,
      null,
      { params: { org_id: orgId } }
    )
    return data
  },

  async getInfo(token: string): Promise<{
    organization_name: string
    invitee_email: string
    role: OrgRole
    expires_at: string
    is_valid: boolean
  }> {
    const { data } = await api.get(`/invitations/info/${token}`)
    return data
  },

  async accept(token: string): Promise<{
    message: string
    organization_id: string
    organization_name: string
  }> {
    const { data } = await api.post('/invitations/accept', { token })
    return data
  }
}

// Group API
export const groupApi = {
  async list(orgId: string): Promise<Group[]> {
    const { data } = await api.get<Group[]>(`/organizations/${orgId}/groups`)
    return data
  },

  async get(orgId: string, groupId: string): Promise<Group> {
    const { data } = await api.get<Group>(`/organizations/${orgId}/groups/${groupId}`)
    return data
  },

  async create(orgId: string, name: string, description?: string): Promise<Group> {
    const { data } = await api.post<Group>(`/organizations/${orgId}/groups`, {
      name,
      description
    })
    return data
  },

  async update(orgId: string, groupId: string, updates: { name?: string; description?: string }): Promise<Group> {
    const { data } = await api.patch<Group>(
      `/organizations/${orgId}/groups/${groupId}`,
      updates
    )
    return data
  },

  async delete(orgId: string, groupId: string): Promise<void> {
    await api.delete(`/organizations/${orgId}/groups/${groupId}`)
  },

  async listMembers(orgId: string, groupId: string): Promise<GroupMember[]> {
    const { data } = await api.get<GroupMember[]>(
      `/organizations/${orgId}/groups/${groupId}/members`
    )
    return data
  },

  async addMember(orgId: string, groupId: string, userId: string): Promise<GroupMember> {
    const { data } = await api.post<GroupMember>(
      `/organizations/${orgId}/groups/${groupId}/members`,
      { user_id: userId }
    )
    return data
  },

  async removeMember(orgId: string, groupId: string, userId: string): Promise<void> {
    await api.delete(`/organizations/${orgId}/groups/${groupId}/members/${userId}`)
  },

  async getUserGroups(orgId: string, userId: string): Promise<Group[]> {
    const { data } = await api.get<Group[]>(
      `/organizations/${orgId}/groups/user/${userId}`
    )
    return data
  }
}

// Document Access API
export const documentAccessApi = {
  async updateVisibility(
    documentId: string,
    visibility: DocumentVisibility
  ): Promise<void> {
    await api.patch(`/documents/${documentId}/visibility`, { visibility })
  },

  async grantAccess(
    documentId: string,
    access: { userId?: string; groupId?: string; accessLevel: 'view' | 'edit' }
  ): Promise<{ id: string; document_id: string; user_id?: string; group_id?: string; access_level: string }> {
    const { data } = await api.post(`/documents/${documentId}/access`, {
      user_id: access.userId,
      group_id: access.groupId,
      access_level: access.accessLevel
    })
    return data
  },

  async revokeAccess(documentId: string, accessId: string): Promise<void> {
    await api.delete(`/documents/${documentId}/access/${accessId}`)
  }
}

export default {
  organization: organizationApi,
  invitation: invitationApi,
  group: groupApi,
  documentAccess: documentAccessApi
}
