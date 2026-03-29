# Phase 07 - Admin Dashboard

**Priority:** P1 | **Duration:** 2 days | **Status:** Pending

## Overview

Implement admin dashboard with user management, system statistics, and processing queue monitoring.

## Key Insights

- Role-based access (ADMIN only)
- Real-time queue status via WebSocket
- User management (list, disable, change role)
- System stats (documents, users, queries)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Admin Dashboard                           │
├─────────────────────────────────────────────────────────────┤
│  Stats Cards                                                 │
│  - Total Documents  - Active Users                          │
│  - Total Chunks     - Queries Today                         │
├─────────────────────────────────────────────────────────────┤
│  User Management                                             │
│  - List users with filters                                  │
│  - Change role (user/editor/admin)                          │
│  - Enable/disable accounts                                  │
├─────────────────────────────────────────────────────────────┤
│  Processing Queue                                            │
│  - Pending tasks                                            │
│  - Processing status                                        │
│  - Failed tasks (with retry)                                │
├─────────────────────────────────────────────────────────────┤
│  Activity Log                                                │
│  - Recent uploads                                           │
│  - Recent queries                                           │
│  - System events                                            │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

### Functional
- View all users (paginated)
- Change user role
- Enable/disable user accounts
- View system statistics
- Monitor processing queue
- View recent activity

### Non-Functional
- Admin-only access (RBAC)
- Stats refresh every 30s
- Queue status real-time via WebSocket

## Related Files

**Create:**
- `backend/app/api/v1/routes/admin.py` - Admin endpoints
- `frontend/src/views/AdminView.vue`

## Implementation Steps

### 1. Admin Routes

```python
# backend/app/api/v1/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID

from app.models.database import get_db
from app.models.models import User, UserRole, Document, DocumentStatus, DocumentChunk
from app.models.schemas import UserResponse
from app.dependencies import get_current_user, require_role
from app.services.celery_tasks import celery_app

router = APIRouter(prefix="/admin", tags=["admin"])

# All routes require admin role
admin_only = Depends(require_role([UserRole.ADMIN]))

class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int

class StatsResponse(BaseModel):
    total_documents: int
    total_users: int
    total_chunks: int
    queries_today: int
    documents_by_status: dict
    documents_by_format: dict

class QueueTask(BaseModel):
    task_id: str
    name: str
    status: str
    args: list
    result: Optional[str]

class ActivityItem(BaseModel):
    type: str
    user_email: str
    description: str
    timestamp: datetime

@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = admin_only
):
    """List all users with optional filters"""
    query = select(User)

    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    users = result.scalars().all()

    count_query = select(func.count(User.id))
    if role:
        count_query = count_query.where(User.role == role)
    if is_active is not None:
        count_query = count_query.where(User.is_active == is_active)

    total = (await db.execute(count_query)).scalar()

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total
    )

@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = admin_only
):
    """Update user role or status"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    # Prevent self-demotion
    if user.id == current_user.id and data.role and data.role != UserRole.ADMIN:
        raise HTTPException(400, "Cannot demote yourself")

    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active

    await db.commit()
    await db.refresh(user)
    return user

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = admin_only
):
    """Get system statistics"""
    # Document counts
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar()
    chunk_count = (await db.execute(select(func.count(DocumentChunk.id)))).scalar()

    # User count
    user_count = (await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )).scalar()

    # Documents by status
    status_result = await db.execute(
        select(Document.status, func.count(Document.id))
        .group_by(Document.status)
    )
    by_status = {row[0].value: row[1] for row in status_result}

    # Documents by format
    format_result = await db.execute(
        select(Document.format, func.count(Document.id))
        .group_by(Document.format)
    )
    by_format = {row[0]: row[1] for row in format_result}

    # Queries today (from a hypothetical query_logs table)
    # For MVP, return 0 or implement logging
    queries_today = 0

    return StatsResponse(
        total_documents=doc_count,
        total_users=user_count,
        total_chunks=chunk_count,
        queries_today=queries_today,
        documents_by_status=by_status,
        documents_by_format=by_format
    )

@router.get("/queue", response_model=List[QueueTask])
async def get_queue_status(current_user: User = admin_only):
    """Get Celery queue status"""
    inspect = celery_app.control.inspect()

    # Get active, reserved, and scheduled tasks
    active = inspect.active() or {}
    reserved = inspect.reserved() or {}

    tasks = []

    for worker, task_list in active.items():
        for task in task_list:
            tasks.append(QueueTask(
                task_id=task['id'],
                name=task['name'],
                status='active',
                args=task.get('args', []),
                result=None
            ))

    for worker, task_list in reserved.items():
        for task in task_list:
            tasks.append(QueueTask(
                task_id=task['id'],
                name=task['name'],
                status='pending',
                args=task.get('args', []),
                result=None
            ))

    return tasks

@router.post("/queue/{task_id}/retry")
async def retry_task(
    task_id: str,
    current_user: User = admin_only
):
    """Retry a failed task"""
    celery_app.control.retry(task_id)
    return {"message": "Task retry initiated"}

@router.get("/activity", response_model=List[ActivityItem])
async def get_activity(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = admin_only
):
    """Get recent activity"""
    # Get recent document uploads
    recent_docs = await db.execute(
        select(Document, User)
        .join(User)
        .order_by(Document.created_at.desc())
        .limit(limit)
    )

    activities = []
    for doc, user in recent_docs:
        activities.append(ActivityItem(
            type="document_upload",
            user_email=user.email,
            description=f"Uploaded {doc.filename}",
            timestamp=doc.created_at
        ))

    return activities
```

### 2. Admin View

```vue
<!-- frontend/src/views/AdminView.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Dropdown from 'primevue/dropdown'
import ProgressSpinner from 'primevue/progressspinner'
import api from '@/api/client'

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
  total_chunks: number
  queries_today: number
  documents_by_status: Record<string, number>
  documents_by_format: Record<string, number>
}

interface QueueTask {
  task_id: string
  name: string
  status: string
  args: any[]
}

const toast = useToast()
const users = ref<User[]>([])
const stats = ref<Stats | null>(null)
const queueTasks = ref<QueueTask[]>([])
const loading = ref(false)

const roles = [
  { label: 'User', value: 'user' },
  { label: 'Editor', value: 'editor' },
  { label: 'Admin', value: 'admin' }
]

onMounted(async () => {
  await Promise.all([fetchUsers(), fetchStats(), fetchQueue()])
})

async function fetchUsers() {
  const { data } = await api.get('/admin/users', { params: { limit: 100 } })
  users.value = data.items
}

async function fetchStats() {
  const { data } = await api.get('/admin/stats')
  stats.value = data
}

async function fetchQueue() {
  const { data } = await api.get('/admin/queue')
  queueTasks.value = data
}

async function changeRole(user: User, newRole: string) {
  try {
    await api.patch(`/admin/users/${user.id}`, { role: newRole })
    user.role = newRole
    toast.add({ severity: 'success', summary: 'Role updated' })
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail })
  }
}

async function toggleActive(user: User) {
  try {
    await api.patch(`/admin/users/${user.id}`, { is_active: !user.is_active })
    user.is_active = !user.is_active
    toast.add({ severity: 'success', summary: 'Status updated' })
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail })
  }
}

async function retryTask(taskId: string) {
  try {
    await api.post(`/admin/queue/${taskId}/retry`)
    toast.add({ severity: 'success', summary: 'Task retry initiated' })
    await fetchQueue()
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail })
  }
}

function getRoleSeverity(role: string) {
  const map: Record<string, any> = {
    admin: 'danger',
    editor: 'warn',
    user: 'info'
  }
  return map[role] || 'info'
}
</script>

<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold mb-6">Admin Dashboard</h1>

    <!-- Stats Cards -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <Card>
        <template #content>
          <p class="text-sm text-gray-500">Total Documents</p>
          <p class="text-3xl font-bold text-blue-600">{{ stats?.total_documents || 0 }}</p>
        </template>
      </Card>
      <Card>
        <template #content>
          <p class="text-sm text-gray-500">Active Users</p>
          <p class="text-3xl font-bold text-green-600">{{ stats?.total_users || 0 }}</p>
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
        <DataTable :value="users" stripedRows>
          <Column field="email" header="Email" sortable />
          <Column field="role" header="Role" sortable>
            <template #body="{ data }">
              <Dropdown
                v-model="data.role"
                :options="roles"
                optionLabel="label"
                optionValue="value"
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
          <Column header="Actions">
            <template #body="{ data }">
              <Button
                :label="data.is_active ? 'Disable' : 'Enable'"
                :severity="data.is_active ? 'danger' : 'success'"
                size="small"
                outlined
                @click="toggleActive(data)"
              />
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Processing Queue -->
    <Card>
      <template #title>
        <div class="flex justify-between items-center">
          <span>Processing Queue</span>
          <Button label="Refresh" size="small" outlined @click="fetchQueue" />
        </div>
      </template>
      <template #content>
        <DataTable :value="queueTasks" stripedRows>
          <Column field="name" header="Task" />
          <Column field="status" header="Status">
            <template #body="{ data }">
              <Tag
                :value="data.status"
                :severity="data.status === 'active' ? 'success' : 'info'"
              />
            </template>
          </Column>
          <Column header="Actions">
            <template #body="{ data }">
              <Button
                v-if="data.status !== 'active'"
                label="Retry"
                size="small"
                outlined
                @click="retryTask(data.task_id)"
              />
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
  </div>
</template>
```

## Todo List

- [ ] Create admin.py routes
- [ ] Add RBAC check (admin only)
- [ ] Create AdminView.vue
- [ ] Add stats API endpoint
- [ ] Add queue status endpoint
- [ ] Add user management endpoints
- [ ] Add activity log endpoint
- [ ] Test: Non-admin cannot access
- [ ] Test: Admin can change user role
- [ ] Test: Stats return correct counts

## Success Criteria

1. Only ADMIN role can access dashboard
2. User list displays all users with pagination
3. Admin can change user roles
4. Admin can enable/disable accounts
5. Stats show accurate system metrics
6. Queue status shows active/pending tasks

## Next Steps

- Phase 08: Testing & Polish
