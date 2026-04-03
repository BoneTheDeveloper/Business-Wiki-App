/**
 * WebSocket composable for real-time updates.
 * Handles connection, reconnection, and message handling.
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth-store'
import { supabase } from '@/lib/supabase'

export interface WebSocketMessage {
  type: string
  [key: string]: any
}

export function useWebSocket(url: string = 'ws://localhost:8000/ws/documents') {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const messages = ref<WebSocketMessage[]>([])
  const error = ref<string | null>(null)
  const authStore = useAuthStore()

  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 5

  async function connect() {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) {
      error.value = 'No authentication token'
      return
    }

    const wsUrl = `${url}?token=${session.access_token}`

    try {
      ws.value = new WebSocket(wsUrl)

      ws.value.onopen = () => {
        connected.value = true
        error.value = null
        reconnectAttempts = 0
        console.log('WebSocket connected')
      }

      ws.value.onclose = (event) => {
        connected.value = false
        console.log('WebSocket closed:', event.code, event.reason)

        // Attempt reconnection
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectTimer = setTimeout(() => {
            reconnectAttempts++
            console.log(`Reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`)
            connect()
          }, 3000)
        }
      }

      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          messages.value.push(data)

          // Keep only last 100 messages
          if (messages.value.length > 100) {
            messages.value = messages.value.slice(-100)
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.value.onerror = (e) => {
        error.value = 'WebSocket connection error'
        console.error('WebSocket error:', e)
      }
    } catch (e) {
      error.value = 'Failed to create WebSocket connection'
      console.error('WebSocket creation error:', e)
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    if (ws.value) {
      ws.value.close()
      ws.value = null
    }

    connected.value = false
  }

  function send(data: any) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(typeof data === 'string' ? data : JSON.stringify(data))
    } else {
      console.warn('WebSocket not connected, cannot send message')
    }
  }

  function ping() {
    send('ping')
  }

  function clearMessages() {
    messages.value = []
  }

  onMounted(() => {
    if (authStore.isAuthenticated) {
      connect()
    }
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    ws,
    connected,
    messages,
    error,
    connect,
    disconnect,
    send,
    ping,
    clearMessages
  }
}
