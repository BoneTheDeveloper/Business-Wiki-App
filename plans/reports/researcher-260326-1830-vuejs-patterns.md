# Vue.js 3 Research Report for Document Wiki Application

**Date:** 2026-03-26
**Focus:** Frontend patterns for RAG-based document wiki

## Executive Summary

Vue.js 3 with Composition API provides excellent foundation for document-heavy wiki applications with real-time features.

---

## 1. Project Structure

### Recommended Structure
```
src/
├── components/          # Reusable UI components
│   ├── common/          # Button, Input, Modal, etc.
│   ├── document/        # Upload, Viewer, Card, etc.
│   ├── chat/            # Message, Input, Thread, etc.
│   └── search/          # Bar, Filters, Results, etc.
├── composables/         # Composition API hooks
│   ├── useAuth.ts
│   ├── useWebSocket.ts
│   ├── useUpload.ts
│   └── useSearch.ts
├── stores/              # Pinia stores
│   ├── auth.ts
│   ├── documents.ts
│   ├── chat.ts
│   └── search.ts
├── views/               # Page components
├── router/              # Vue Router config
├── api/                 # API client modules
└── utils/               # Helper functions
```

---

## 2. State Management: Pinia

### Why Pinia over Vuex
- TypeScript-first design
- Simpler API (no mutations)
- Better devtools integration
- Smaller bundle size

### Store Pattern
```typescript
// stores/documents.ts
export const useDocumentStore = defineStore('documents', () => {
  const documents = ref<Document[]>([])
  const loading = ref(false)

  async function fetchDocuments() { ... }
  async function uploadDocument(file: File) { ... }

  return { documents, loading, fetchDocuments, uploadDocument }
})
```

---

## 3. Real-time Updates with WebSocket

### Composable Pattern
```typescript
// composables/useWebSocket.ts
export function useWebSocket(url: string) {
  const ws = ref<WebSocket | null>(null)
  const messages = ref<Message[]>([])
  const connected = ref(false)

  function connect() {
    ws.value = new WebSocket(url)
    ws.value.onmessage = (e) => messages.value.push(JSON.parse(e.data))
  }

  function send(data: object) {
    ws.value?.send(JSON.stringify(data))
  }

  return { messages, connected, connect, send }
}
```

### Usage in Chat Component
```vue
<script setup lang="ts">
const { messages, send, connected } = useWebSocket(WS_URL)
</script>
```

---

## 4. File Upload Handling

### Large File Upload with Progress
```typescript
// composables/useUpload.ts
export function useUpload() {
  const progress = ref(0)
  const uploading = ref(false)

  async function uploadChunked(file: File) {
    const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB
    const chunks = Math.ceil(file.size / CHUNK_SIZE)

    for (let i = 0; i < chunks; i++) {
      const chunk = file.slice(
        i * CHUNK_SIZE,
        Math.min((i + 1) * CHUNK_SIZE, file.size)
      )
      await uploadChunk(chunk, i, chunks, file.name)
      progress.value = ((i + 1) / chunks) * 100
    }
  }

  return { progress, uploading, uploadChunked }
}
```

### Drag & Drop Component
```vue
<template>
  <div
    @dragover.prevent="dragover = true"
    @dragleave="dragover = false"
    @drop.prevent="handleDrop"
    :class="{ 'border-blue-500': dragover }"
  >
    <slot />
  </div>
</template>
```

---

## 5. Search UI Patterns

### Autocomplete with Debounce
```typescript
// composables/useSearch.ts
export function useSearch() {
  const query = ref('')
  const results = ref<SearchResult[]>([])
  const loading = ref(false)

  const debouncedSearch = useDebounceFn(async () => {
    if (!query.value) return
    loading.value = true
    results.value = await api.search(query.value)
    loading.value = false
  }, 300)

  watch(query, debouncedSearch)

  return { query, results, loading }
}
```

### Faceted Search Pattern
```typescript
interface SearchFilters {
  documentType: string[]
  dateRange: [Date, Date]
  author: string[]
  tags: string[]
}

// Apply filters client-side or server-side
function applyFilters(results: SearchResult[], filters: SearchFilters) {
  return results.filter(r =>
    filters.documentType.includes(r.type) &&
    r.date >= filters.dateRange[0] &&
    r.date <= filters.dateRange[1]
  )
}
```

---

## 6. Admin Dashboard Libraries

### Recommended Stack
| Library | Purpose |
|---------|---------|
| **PrimeVue** | Full-featured UI kit with data tables, charts |
| **Naive UI** | TypeScript-first, good tree-shaking |
| **Vuestic** | Admin-focused with dashboard widgets |
| **Headless UI** | Unstyled, accessible components |

### For MVP
- **PrimeVue** for data tables, charts, file upload
- **Tailwind CSS** for styling
- **Chart.js** or **ECharts** for analytics

---

## 7. Component Library Recommendations

### MVP Stack
- **Vue 3** + **Vite** + **TypeScript**
- **Pinia** for state
- **Vue Router** for navigation
- **PrimeVue** for UI components
- **Tailwind CSS** for styling
- **VueUse** for composables

### Key VueUse Composables
- `useStorage` - Persist state to localStorage
- `useDebounceFn` - Debounced functions
- `useThrottleFn` - Throttled functions
- `useIntersectionObserver` - Lazy loading
- `useDropZone` - File drag & drop

---

## 8. Performance Optimizations

### Lazy Loading
```typescript
// router/index.ts
const routes = [
  {
    path: '/admin',
    component: () => import('@/views/Admin.vue') // Lazy load
  }
]
```

### Virtual Scrolling for Long Lists
```vue
<template>
  <VirtualScroller
    :items="documents"
    :item-size="60"
    v-slot="{ item }"
  >
    <DocumentCard :document="item" />
  </VirtualScroller>
</template>
```

---

## Recommendations Summary

### Tech Stack (MVP)
| Layer | Technology |
|-------|------------|
| Framework | Vue 3 + Composition API |
| Build | Vite |
| Language | TypeScript |
| State | Pinia |
| Routing | Vue Router |
| UI | PrimeVue + Tailwind CSS |
| HTTP | Axios or fetch |
| WebSocket | Native WebSocket |
| Utilities | VueUse |

### Key Patterns
1. **Composables** for reusable logic (auth, upload, search, ws)
2. **Pinia stores** for global state
3. **Chunked uploads** for large files
4. **Debounced search** for autocomplete
5. **Virtual scrolling** for long lists
6. **Lazy loading** for routes

---

## Unresolved Questions
1. Mobile-first vs desktop-first responsive design?
2. Dark mode requirement?
3. Offline/PWA support needed?
4. Accessibility (WCAG) compliance level?

---

**Report prepared:** 2026-03-26
