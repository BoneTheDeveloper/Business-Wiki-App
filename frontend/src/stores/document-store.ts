/**
 * Document store with Pinia.
 * Manages document list, upload, delete operations.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

export interface Document {
  id: string
  filename: string
  file_size: number
  format: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  metadata: Record<string, any>
  created_at: string
  error_message?: string
}

export const useDocumentStore = defineStore('documents', () => {
  const documents = ref<Document[]>([])
  const currentDocument = ref<Document | null>(null)
  const loading = ref(false)
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const total = ref(0)
  const error = ref<string | null>(null)

  async function fetchDocuments(skip = 0, limit = 20, status?: string) {
    loading.value = true
    error.value = null

    try {
      const params: any = { skip, limit }
      if (status) params.status = status

      const { data } = await api.get('/documents', { params })
      documents.value = data.items
      total.value = data.total
      return data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to fetch documents'
      return null
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(file: File, onProgress?: (p: number) => void) {
    uploading.value = true
    uploadProgress.value = 0
    error.value = null

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
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Upload failed'
      throw e
    } finally {
      uploading.value = false
    }
  }

  async function fetchDocument(id: string) {
    loading.value = true
    error.value = null

    try {
      const { data } = await api.get(`/documents/${id}`)
      currentDocument.value = data
      return data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to fetch document'
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchDocumentStatus(id: string) {
    try {
      const { data } = await api.get(`/documents/${id}/status`)
      return data
    } catch (e: any) {
      return null
    }
  }

  async function deleteDocument(id: string) {
    try {
      await api.delete(`/documents/${id}`)
      documents.value = documents.value.filter(d => d.id !== id)
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Delete failed'
      return false
    }
  }

  function updateDocumentStatus(id: string, status: string, metadata?: any) {
    const doc = documents.value.find(d => d.id === id)
    if (doc) {
      doc.status = status as any
      if (metadata) doc.metadata = metadata
    }
    if (currentDocument.value?.id === id) {
      currentDocument.value.status = status as any
      if (metadata) currentDocument.value.metadata = metadata
    }
  }

  return {
    documents,
    currentDocument,
    loading,
    uploading,
    uploadProgress,
    total,
    error,
    fetchDocuments,
    uploadDocument,
    fetchDocument,
    fetchDocumentStatus,
    deleteDocument,
    updateDocumentStatus
  }
})
