# Phase 05 - Frontend Core

**Priority:** P0 | **Duration:** 3 days | **Status:** Pending

## Overview

Set up Vue.js 3 frontend with TypeScript, PrimeVue, Tailwind CSS. Implement authentication, document upload, and document list views.

## Key Insights

- Vite for fast development
- Pinia for state management
- Vue Router for navigation
- PrimeVue components
- Axios for API calls

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Vue.js 3 Frontend                         │
├─────────────────────────────────────────────────────────────┤
│  Views:                                                      │
│  - LoginView.vue                                            │
│  - RegisterView.vue                                         │
│  - DashboardView.vue (document list)                        │
│  - DocumentDetailView.vue                                   │
│  - ChatView.vue                                             │
│  - SearchView.vue                                           │
│  - AdminView.vue                                            │
├─────────────────────────────────────────────────────────────┤
│  Stores (Pinia):                                             │
│  - authStore (user, tokens, login/logout)                   │
│  - documentStore (documents, upload, status)                │
├─────────────────────────────────────────────────────────────┤
│  Composables:                                                │
│  - useApi (axios instance with auth)                        │
│  - useToast (notifications)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

### Functional
- Login/Register forms with validation
- JWT token storage and refresh
- Document upload with drag-drop
- Document list with pagination
- Document detail view

### Non-Functional
- Page load < 2s
- Responsive design (mobile-first)
- Dark mode support (future)

## Related Files

**Create:**
- `frontend/src/main.ts`
- `frontend/src/App.vue`
- `frontend/src/router/index.ts`
- `frontend/src/stores/authStore.ts`
- `frontend/src/stores/documentStore.ts`
- `frontend/src/api/client.ts`
- `frontend/src/views/*.vue`
- `frontend/src/components/*.vue`

## Implementation Steps

### 1. Main Entry

```typescript
// frontend/src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import App from './App.vue'
import router from './router'
import './assets/main.css'

import 'primevue/resources/themes/lara-light-blue/theme.css'
import 'primevue/resources/primevue.min.css'
import 'primeicons/primeicons.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue)
app.use(ToastService)
app.use(ConfirmationService)

app.mount('#app')
```

### 2. Router

```typescript
// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { guest: true }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/documents/:id',
    name: 'DocumentDetail',
    component: () => import('@/views/DocumentDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('@/views/SearchView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.guest && authStore.isAuthenticated) {
    next({ name: 'Dashboard' })
  } else if (to.meta.requiresAdmin && authStore.user?.role !== 'admin') {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router
```

### 3. API Client

```typescript
// frontend/src/api/client.ts
import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const authStore = useAuthStore()
        await authStore.refreshToken()
        originalRequest.headers.Authorization = `Bearer ${authStore.accessToken}`
        return api(originalRequest)
      } catch (refreshError) {
        const authStore = useAuthStore()
        authStore.logout()
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default api
```

### 4. Auth Store

```typescript
// frontend/src/stores/authStore.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

interface User {
  id: string
  email: string
  role: 'user' | 'editor' | 'admin'
  is_active: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(email: string, password: string) {
    const { data } = await api.post('/auth/login', { email, password })

    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token

    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)

    await fetchUser()
  }

  async function register(email: string, password: string) {
    await api.post('/auth/register', { email, password })
  }

  async function fetchUser() {
    const { data } = await api.get('/auth/me')
    user.value = data
  }

  async function refreshAccessToken() {
    const { data } = await api.post('/auth/refresh', {
      refresh_token: refreshToken.value
    })

    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token

    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
  }

  function logout() {
    user.value = null
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return {
    user,
    accessToken,
    isAuthenticated,
    isAdmin,
    login,
    register,
    fetchUser,
    refreshAccessToken,
    logout
  }
})
```

### 5. Document Store

```typescript
// frontend/src/stores/documentStore.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

interface Document {
  id: string
  filename: string
  file_size: number
  format: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  metadata: Record<string, any>
  created_at: string
}

export const useDocumentStore = defineStore('documents', () => {
  const documents = ref<Document[]>([])
  const currentDocument = ref<Document | null>(null)
  const loading = ref(false)
  const uploading = ref(false)
  const uploadProgress = ref(0)

  async function fetchDocuments(skip = 0, limit = 20) {
    loading.value = true
    try {
      const { data } = await api.get('/documents', { params: { skip, limit } })
      documents.value = data.items
      return data
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(file: File, onProgress?: (p: number) => void) {
    uploading.value = true
    uploadProgress.value = 0

    try {
      const formData = new FormData()
      formData.append('file', file)

      const { data } = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) {
            uploadProgress.value = Math.round((e.loaded / e.total) * 100)
            onProgress?.(uploadProgress.value)
          }
        }
      })

      documents.value.unshift(data)
      return data
    } finally {
      uploading.value = false
    }
  }

  async function deleteDocument(id: string) {
    await api.delete(`/documents/${id}`)
    documents.value = documents.value.filter(d => d.id !== id)
  }

  async function fetchDocument(id: string) {
    loading.value = true
    try {
      const { data } = await api.get(`/documents/${id}`)
      currentDocument.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  return {
    documents,
    currentDocument,
    loading,
    uploading,
    uploadProgress,
    fetchDocuments,
    uploadDocument,
    deleteDocument,
    fetchDocument
  }
})
```

### 6. Dashboard View

```vue
<!-- frontend/src/views/DashboardView.vue -->
<script setup lang="ts">
import { onMounted } from 'vue'
import { useDocumentStore } from '@/stores/documentStore'
import { useToast } from 'primevue/usetoast'
import FileUpload from 'primevue/fileupload'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'

const documentStore = useDocumentStore()
const toast = useToast()

onMounted(() => {
  documentStore.fetchDocuments()
})

async function onUpload(event: any) {
  const file = event.files[0]
  try {
    await documentStore.uploadDocument(file)
    toast.add({ severity: 'success', summary: 'Uploaded', detail: file.name })
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail })
  }
}

function formatSize(bytes: number) {
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

function getStatusSeverity(status: string) {
  const map: Record<string, any> = {
    completed: 'success',
    processing: 'warn',
    pending: 'info',
    failed: 'danger'
  }
  return map[status] || 'info'
}
</script>

<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold mb-6">Documents</h1>

    <!-- Upload Zone -->
    <FileUpload
      mode="basic"
      accept=".pdf,.docx,.xlsx"
      :maxFileSize="50000000"
      customUpload
      @uploader="onUpload"
      :auto="true"
      chooseLabel="Upload Document"
      class="mb-6"
    />

    <!-- Progress -->
    <ProgressSpinner v-if="documentStore.uploading" />

    <!-- Document Grid -->
    <div v-if="documentStore.loading" class="text-center py-8">
      <ProgressSpinner />
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card v-for="doc in documentStore.documents" :key="doc.id">
        <template #title>
          <div class="flex items-center gap-2">
            <span class="text-2xl">{{ doc.format === 'pdf' ? '📄' : doc.format === 'docx' ? '📝' : '📊' }}</span>
            <span class="truncate">{{ doc.filename }}</span>
          </div>
        </template>
        <template #content>
          <p class="text-sm text-gray-500">{{ formatSize(doc.file_size) }}</p>
          <Tag :value="doc.status" :severity="getStatusSeverity(doc.status)" class="mt-2" />
        </template>
        <template #footer>
          <div class="flex gap-2">
            <Button label="View" size="small" @click="$router.push(`/documents/${doc.id}`)" />
            <Button label="Delete" severity="danger" size="small" outlined @click="documentStore.deleteDocument(doc.id)" />
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>
```

## Todo List

- [ ] Create main.ts with Vue app setup
- [ ] Create router with auth guards
- [ ] Create api/client.ts with interceptors
- [ ] Create authStore with login/logout/refresh
- [ ] Create documentStore with CRUD
- [ ] Create LoginView.vue
- [ ] Create RegisterView.vue
- [ ] Create DashboardView.vue
- [ ] Create DocumentDetailView.vue
- [ ] Create AppLayout.vue (sidebar + header)
- [ ] Test: Login redirects to dashboard
- [ ] Test: Upload shows in list
- [ ] Test: Token refresh on 401

## Success Criteria

1. User can register and login
2. JWT tokens stored and refreshed automatically
3. Document upload with progress indicator
4. Document list with pagination
5. Responsive layout works on mobile

## Next Steps

- Phase 06: Chat & Search interfaces
