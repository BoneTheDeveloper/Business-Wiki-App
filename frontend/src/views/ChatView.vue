<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Card from 'primevue/card'
import ProgressSpinner from 'primevue/progressspinner'
import Toast from 'primevue/toast'

const route = useRoute()
const toast = useToast()

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}

const messages = ref<Message[]>([])
const inputMessage = ref('')
const loading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

onMounted(() => {
  // Add welcome message
  messages.value.push({
    role: 'assistant',
    content: 'Hello! I can help you search and understand your documents. Ask me anything about your uploaded documents.'
  })
})

async function sendMessage() {
  if (!inputMessage.value.trim() || loading.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''

  // Add user message
  messages.value.push({ role: 'user', content: userMessage })

  loading.value = true

  try {
    const { data } = await api.post('/chat', {
      query: userMessage,
      document_ids: route.query.doc ? [route.query.doc] : undefined,
      top_k: 5
    })

    // Add assistant response
    messages.value.push({
      role: 'assistant',
      content: data.answer,
      sources: data.sources
    })

    // Scroll to bottom
    await nextTick()
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail || 'Chat failed' })
    // Remove user message on error
    messages.value.pop()
  } finally {
    loading.value = false
  }
}

function formatSource(source: any) {
  return `${source.filename} (${Math.round(source.similarity * 100)}% match)`
}
</script>

<template>
  <Toast />

  <div class="flex flex-col h-screen max-w-4xl mx-auto">
    <!-- Header -->
    <div class="p-4 border-b bg-white">
      <h1 class="text-xl font-bold text-gray-800">Chat with Documents</h1>
      <p class="text-sm text-gray-500">Ask questions about your uploaded documents</p>
    </div>

    <!-- Messages -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="[
          'flex',
          message.role === 'user' ? 'justify-end' : 'justify-start'
        ]"
      >
        <Card
          :class="[
            'max-w-[80%]',
            message.role === 'user' ? 'bg-blue-500 text-white' : 'bg-white'
          ]"
        >
          <template #content>
            <p class="whitespace-pre-wrap">{{ message.content }}</p>

            <!-- Sources -->
            <div v-if="message.sources && message.sources.length" class="mt-3 pt-3 border-t border-gray-200">
              <p class="text-xs text-gray-500 mb-2">Sources:</p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="source in message.sources"
                  :key="source.chunk_id"
                  class="text-xs bg-gray-100 px-2 py-1 rounded"
                >
                  {{ formatSource(source) }}
                </span>
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Loading indicator -->
      <div v-if="loading" class="flex justify-start">
        <Card class="bg-white">
          <template #content>
            <div class="flex items-center gap-2">
              <ProgressSpinner style="width: 20px; height: 20px" />
              <span class="text-gray-500">Thinking...</span>
            </div>
          </template>
        </Card>
      </div>
    </div>

    <!-- Input -->
    <div class="p-4 border-t bg-white">
      <form @submit.prevent="sendMessage" class="flex gap-2">
        <InputText
          v-model="inputMessage"
          placeholder="Ask a question about your documents..."
          class="flex-1"
          :disabled="loading"
        />
        <Button
          type="submit"
          icon="pi pi-send"
          label="Send"
          :loading="loading"
          :disabled="!inputMessage.trim()"
        />
      </form>
    </div>
  </div>
</template>
