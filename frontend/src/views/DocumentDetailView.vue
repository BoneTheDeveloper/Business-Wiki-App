<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDocumentStore } from '@/stores/document-store'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import Toast from 'primevue/toast'

const route = useRoute()
const router = useRouter()
const documentStore = useDocumentStore()
const toast = useToast()

const documentId = computed(() => route.params.id as string)

onMounted(async () => {
  await documentStore.fetchDocument(documentId.value)
})

function formatSize(bytes: number) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
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

function goBack() {
  router.push('/')
}

function chatWithDocument() {
  router.push(`/chat?doc=${documentId.value}`)
}

function searchInDocument() {
  router.push(`/search?doc=${documentId.value}`)
}
</script>

<template>
  <Toast />

  <div class="p-6 max-w-4xl mx-auto">
    <!-- Loading State -->
    <div v-if="documentStore.loading" class="text-center py-12">
      <ProgressSpinner />
    </div>

    <!-- Document Content -->
    <div v-else-if="documentStore.currentDocument">
      <!-- Header -->
      <div class="flex items-center gap-4 mb-6">
        <Button icon="pi pi-arrow-left" outlined @click="goBack" />
        <div class="flex-1">
          <h1 class="text-2xl font-bold text-gray-800 truncate">
            {{ documentStore.currentDocument.filename }}
          </h1>
          <div class="flex items-center gap-3 mt-1 text-sm text-gray-500">
            <span class="uppercase font-semibold">{{ documentStore.currentDocument.format }}</span>
            <span>{{ formatSize(documentStore.currentDocument.file_size) }}</span>
            <Tag :value="documentStore.currentDocument.status" :severity="getStatusSeverity(documentStore.currentDocument.status)" />
          </div>
        </div>
        <div class="flex gap-2">
          <Button icon="pi pi-search" label="Search" outlined @click="searchInDocument" />
          <Button icon="pi pi-comments" label="Chat" @click="chatWithDocument" />
        </div>
      </div>

      <!-- Metadata Card -->
      <Card class="mb-6">
        <template #title>Document Information</template>
        <template #content>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p class="text-sm text-gray-500">Status</p>
              <Tag :value="documentStore.currentDocument.status" :severity="getStatusSeverity(documentStore.currentDocument.status)" />
            </div>
            <div>
              <p class="text-sm text-gray-500">Format</p>
              <p class="font-medium uppercase">{{ documentStore.currentDocument.format }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-500">File Size</p>
              <p class="font-medium">{{ formatSize(documentStore.currentDocument.file_size) }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-500">Uploaded</p>
              <p class="font-medium">{{ new Date(documentStore.currentDocument.created_at).toLocaleDateString() }}</p>
            </div>
          </div>
        </template>
      </Card>

      <!-- Processing Status -->
      <Card v-if="documentStore.currentDocument.status === 'processing'" class="mb-6">
        <template #content>
          <div class="flex items-center gap-4">
            <ProgressSpinner style="width: 30px; height: 30px" />
            <div>
              <p class="font-medium">Processing document...</p>
              <p class="text-sm text-gray-500">This may take a few moments</p>
            </div>
          </div>
        </template>
      </Card>

      <!-- Error Message -->
      <Card v-if="documentStore.currentDocument.status === 'failed'" class="mb-6 border-red-200">
        <template #title>
          <span class="text-red-600">Processing Failed</span>
        </template>
        <template #content>
          <p class="text-red-600">{{ documentStore.currentDocument.error_message || 'An error occurred while processing this document' }}</p>
        </template>
      </Card>

      <!-- Extracted Metadata -->
      <Card v-if="documentStore.currentDocument.metadata && Object.keys(documentStore.currentDocument.metadata).length" class="mb-6">
        <template #title>Extracted Metadata</template>
        <template #content>
          <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div v-for="(value, key) in documentStore.currentDocument.metadata" :key="key">
              <p class="text-sm text-gray-500 capitalize">{{ key.replace(/_/g, ' ') }}</p>
              <p class="font-medium">{{ value || '-' }}</p>
            </div>
          </div>
        </template>
      </Card>

      <!-- Extracted Text Preview -->
      <Card v-if="documentStore.currentDocument.status === 'completed'">
        <template #title>Content Preview</template>
        <template #content>
          <p class="text-sm text-gray-500 mb-2">
            {{ documentStore.currentDocument.metadata?.word_count?.toLocaleString() || 0 }} words extracted
          </p>
          <div class="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto">
            <p class="whitespace-pre-wrap text-sm text-gray-700">
              Document content has been processed and chunked for semantic search.
              Use the Search or Chat features to query this document.
            </p>
          </div>
        </template>
      </Card>
    </div>

    <!-- Not Found -->
    <div v-else class="text-center py-12">
      <i class="pi pi-exclamation-triangle text-6xl text-gray-300 mb-4"></i>
      <h3 class="text-lg font-medium text-gray-600">Document not found</h3>
      <Button label="Go back" class="mt-4" @click="goBack" />
    </div>
  </div>
</template>
