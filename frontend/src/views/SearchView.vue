<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Card from 'primevue/card'
import ProgressSpinner from 'primevue/progressspinner'
import Toast from 'primevue/toast'
import Slider from 'primevue/slider'

const route = useRoute()
const toast = useToast()

const query = ref((route.query.q as string) || '')
const results = ref<any[]>([])
const loading = ref(false)
const topK = ref(10)

async function search() {
  if (!query.value.trim() || query.value.length < 3) {
    toast.add({ severity: 'warn', summary: 'Warning', detail: 'Query must be at least 3 characters' })
    return
  }

  loading.value = true

  try {
    const { data } = await api.post('/search', {
      query: query.value,
      top_k: topK.value,
      document_ids: route.query.doc ? [route.query.doc] : undefined
    })
    results.value = data.results
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail || 'Search failed' })
  } finally {
    loading.value = false
  }
}

function formatSimilarity(score: number) {
  return `${Math.round(score * 100)}%`
}

onMounted(() => {
  if (query.value) {
    search()
  }
})
</script>

<template>
  <Toast />

  <div class="p-6 max-w-4xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-800 mb-6">Semantic Search</h1>

    <!-- Search Form -->
    <Card class="mb-6">
      <template #content>
        <div class="flex gap-4 mb-4">
          <InputText
            v-model="query"
            placeholder="Search your documents..."
            class="flex-1"
            @keyup.enter="search"
          />
          <Button label="Search" icon="pi pi-search" :loading="loading" @click="search" />
        </div>

        <div class="flex items-center gap-4">
          <span class="text-sm text-gray-500">Results: {{ topK }}</span>
          <Slider v-model="topK" :min="5" :max="50" :step="5" class="flex-1" />
        </div>
      </template>
    </Card>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <ProgressSpinner />
      <p class="text-gray-500 mt-4">Searching documents...</p>
    </div>

    <!-- Results -->
    <div v-else-if="results.length" class="space-y-4">
      <p class="text-sm text-gray-500">{{ results.length }} results found</p>

      <Card v-for="(result, index) in results" :key="result.chunk_id" class="hover:shadow-md transition-shadow">
        <template #subtitle>
          <div class="flex items-center justify-between">
            <span class="font-medium">{{ result.filename }}</span>
            <span class="text-sm text-gray-500">{{ formatSimilarity(result.similarity) }} match</span>
          </div>
        </template>
        <template #content>
          <p class="text-sm text-gray-700 line-clamp-4">{{ result.content }}</p>
          <div class="flex items-center gap-2 mt-3 text-xs text-gray-500">
            <span class="uppercase font-semibold px-2 py-1 bg-gray-100 rounded">{{ result.format }}</span>
            <span v-if="result.metadata?.page">Page {{ result.metadata.page }}</span>
          </div>
        </template>
      </Card>
    </div>

    <!-- Empty State -->
    <div v-else-if="query && !loading" class="text-center py-12">
      <i class="pi pi-search text-6xl text-gray-300 mb-4"></i>
      <h3 class="text-lg font-medium text-gray-600">No results found</h3>
      <p class="text-gray-500">Try a different search term</p>
    </div>

    <!-- Initial State -->
    <div v-else class="text-center py-12">
      <i class="pi pi-search text-6xl text-gray-300 mb-4"></i>
      <h3 class="text-lg font-medium text-gray-600">Search your documents</h3>
      <p class="text-gray-500">Enter a query to find relevant content across your documents</p>
    </div>
  </div>
</template>
