<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDocumentStore } from '@/stores/document-store'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import FileUpload from 'primevue/fileupload'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import ProgressBar from 'primevue/progressbar'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'

const router = useRouter()
const documentStore = useDocumentStore()
const toast = useToast()
const confirm = useConfirm()

const uploadProgress = ref(0)

onMounted(() => {
  documentStore.fetchDocuments()
})

async function onUpload(event: any) {
  const file = event.files[0]
  uploadProgress.value = 0

  try {
    await documentStore.uploadDocument(file, (p) => {
      uploadProgress.value = p
    })
    toast.add({ severity: 'success', summary: 'Uploaded', detail: `${file.name} uploaded successfully` })
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Upload Failed',
      detail: error.response?.data?.detail || 'Failed to upload file'
    })
  }
}

function confirmDelete(doc: any) {
  confirm.require({
    message: `Are you sure you want to delete "${doc.filename}"?`,
    header: 'Confirm Delete',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: async () => {
      const success = await documentStore.deleteDocument(doc.id)
      if (success) {
        toast.add({ severity: 'success', summary: 'Deleted', detail: 'Document deleted' })
      } else {
        toast.add({ severity: 'error', summary: 'Error', detail: documentStore.error || 'Delete failed' })
      }
    }
  })
}

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

function getFileIcon(format: string) {
  const icons: Record<string, string> = {
    pdf: 'pi-file-pdf',
    docx: 'pi-file-word',
    xlsx: 'pi-file-excel'
  }
  return icons[format] || 'pi-file'
}

function viewDocument(doc: any) {
  router.push(`/documents/${doc.id}`)
}
</script>

<template>
  <Toast />
  <ConfirmDialog />

  <div class="p-6 max-w-7xl mx-auto">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">Documents</h1>
      <div class="flex gap-2">
        <Button icon="pi pi-search" label="Search" outlined @click="router.push('/search')" />
        <Button icon="pi pi-comments" label="Chat" outlined @click="router.push('/chat')" />
      </div>
    </div>

    <!-- Upload Zone -->
    <Card class="mb-6">
      <template #content>
        <div class="flex items-center gap-4">
          <FileUpload
            mode="basic"
            accept=".pdf,.docx,.xlsx"
            :maxFileSize="50000000"
            customUpload
            @uploader="onUpload"
            :auto="true"
            chooseLabel="Upload Document (PDF, DOCX, XLSX)"
            class="flex-1"
          />
          <span class="text-sm text-gray-500">Max 50MB</span>
        </div>
        <ProgressBar v-if="documentStore.uploading" :value="uploadProgress" class="mt-4" />
      </template>
    </Card>

    <!-- Loading State -->
    <div v-if="documentStore.loading && !documentStore.documents.length" class="text-center py-12">
      <ProgressSpinner />
      <p class="text-gray-500 mt-4">Loading documents...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="!documentStore.documents.length" class="text-center py-12 bg-white rounded-lg">
      <i class="pi pi-folder-open text-6xl text-gray-300 mb-4"></i>
      <h3 class="text-lg font-medium text-gray-600">No documents yet</h3>
      <p class="text-gray-500">Upload your first document to get started</p>
    </div>

    <!-- Document Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <Card v-for="doc in documentStore.documents" :key="doc.id" class="hover:shadow-lg transition-shadow">
        <template #header>
          <div class="p-4 bg-gray-50 flex items-center justify-center">
            <i :class="['pi', getFileIcon(doc.format), 'text-4xl', 'text-gray-400']"></i>
          </div>
        </template>
        <template #title>
          <span class="truncate block" :title="doc.filename">{{ doc.filename }}</span>
        </template>
        <template #subtitle>
          <div class="flex items-center gap-2">
            <span class="uppercase text-xs font-semibold">{{ doc.format }}</span>
            <span class="text-gray-400">|</span>
            <span>{{ formatSize(doc.file_size) }}</span>
          </div>
        </template>
        <template #content>
          <div class="flex items-center justify-between">
            <Tag :value="doc.status" :severity="getStatusSeverity(doc.status)" />
            <span class="text-xs text-gray-500">
              {{ new Date(doc.created_at).toLocaleDateString() }}
            </span>
          </div>
          <p v-if="doc.status === 'completed' && doc.metadata?.word_count" class="text-xs text-gray-500 mt-2">
            {{ doc.metadata.word_count?.toLocaleString() }} words
          </p>
          <p v-if="doc.status === 'failed' && doc.error_message" class="text-xs text-red-500 mt-2 truncate">
            {{ doc.error_message }}
          </p>
        </template>
        <template #footer>
          <div class="flex gap-2">
            <Button
              label="View"
              icon="pi pi-eye"
              size="small"
              :disabled="doc.status !== 'completed'"
              @click="viewDocument(doc)"
            />
            <Button
              label="Delete"
              icon="pi pi-trash"
              severity="danger"
              size="small"
              outlined
              @click="confirmDelete(doc)"
            />
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>
