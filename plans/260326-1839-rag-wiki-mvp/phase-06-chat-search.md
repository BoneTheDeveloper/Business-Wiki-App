# Phase 06 - Chat & Search

**Priority:** P0 | **Duration:** 3 days | **Status:** Pending

## Overview

Implement chat interface with RAG-powered responses and semantic search UI with real-time WebSocket updates.

## Key Insights

- Chat uses retrieved chunks as context for LLM
- OpenAI GPT-4o-mini for cost-effective responses
- WebSocket for real-time document processing status
- Source citations link to original documents

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Chat Flow                                                   │
├─────────────────────────────────────────────────────────────┤
│  User Query                                                  │
│      ↓                                                       │
│  Vector Search (Top-K chunks)                               │
│      ↓                                                       │
│  Build Prompt (query + context)                             │
│      ↓                                                       │
│  LLM Generate (GPT-4o-mini)                                 │
│      ↓                                                       │
│  Response + Sources                                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  WebSocket Flow                                              │
├─────────────────────────────────────────────────────────────┤
│  Client connects: ws://localhost:8000/ws/documents          │
│      ↓                                                       │
│  Subscribe to document events                                │
│      ↓                                                       │
│  Server pushes: status updates, progress                    │
│      ↓                                                       │
│  Client updates UI in real-time                             │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

### Functional
- Chat with document context
- Source citations with page numbers
- Semantic search with filters
- Real-time processing status via WebSocket
- Search result highlighting

### Non-Functional
- Chat response < 5s
- Search latency < 500ms
- WebSocket reconnection on disconnect

## Related Files

**Create:**
- `backend/app/api/v1/routes/chat.py` - Chat endpoint
- `backend/app/services/llm_service.py` - LLM integration
- `backend/app/utils/websocket.py` - WebSocket manager
- `frontend/src/views/ChatView.vue`
- `frontend/src/views/SearchView.vue`
- `frontend/src/composables/useWebSocket.ts`

## Implementation Steps

### 1. LLM Service

```python
# backend/app/services/llm_service.py
from openai import AsyncOpenAI
from typing import List, Dict, Any
from app.config import settings
from app.services.rag_service import rag_service

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

    async def chat(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        conversation_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """Generate chat response with RAG context"""

        # Build context from chunks
        context_text = "\n\n".join([
            f"[Document: {c['filename']}, Page: {c['metadata'].get('page', 'N/A')}]\n{c['content']}"
            for c in context_chunks
        ])

        # System prompt
        system_prompt = """You are a helpful assistant that answers questions based on the provided document context.
- Only use information from the context to answer questions
- If the answer is not in the context, say so
- Always cite sources using the format [Document: filename, Page: X]
- Be concise but thorough"""

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"}
        ]

        # Add conversation history if provided
        if conversation_history:
            messages = [
                {"role": "system", "content": system_prompt},
                *conversation_history[-4:],  # Last 4 messages for context
                {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"}
            ]

        # Generate response
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )

        return {
            "answer": response.choices[0].message.content,
            "sources": [
                {
                    "document_id": c["document_id"],
                    "filename": c["filename"],
                    "chunk_id": c["chunk_id"],
                    "similarity": c["similarity"],
                    "page": c["metadata"].get("page")
                }
                for c in context_chunks
            ],
            "model": self.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        }

llm_service = LLMService()
```

### 2. Chat Routes

```python
# backend/app/api/v1/routes/chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from app.models.database import get_db
from app.models.models import User
from app.dependencies import get_current_user
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    document_ids: Optional[List[str]] = None
    conversation_history: Optional[List[ChatMessage]] = None
    top_k: int = 5

class Source(BaseModel):
    document_id: str
    filename: str
    chunk_id: str
    similarity: float
    page: Optional[int]

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    model: str
    usage: dict

@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Chat with documents using RAG"""

    if len(request.query) < 3:
        raise HTTPException(400, "Query too short")

    # Retrieve relevant chunks
    chunks = await rag_service.search(
        db=db,
        query=request.query,
        top_k=request.top_k,
        document_ids=request.document_ids
    )

    if not chunks:
        return ChatResponse(
            answer="I couldn't find any relevant information in your documents. Please try a different query or upload more documents.",
            sources=[],
            model="none",
            usage={"prompt_tokens": 0, "completion_tokens": 0}
        )

    # Generate response
    history = None
    if request.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in request.conversation_history]

    response = await llm_service.chat(
        query=request.query,
        context_chunks=chunks,
        conversation_history=history
    )

    return ChatResponse(**response)
```

### 3. WebSocket Manager

```python
# backend/app/utils/websocket.py
from fastapi import WebSocket
from typing import Dict, Set
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        # user_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: str):
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections for a user"""
        async with self._lock:
            connections = self.active_connections.get(user_id, set()).copy()

        dead_connections = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        for dead in dead_connections:
            await self.disconnect(dead, user_id)

    async def broadcast(self, message: dict):
        """Broadcast to all connected users"""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)

manager = ConnectionManager()

# WebSocket endpoint
from fastapi import APIRouter, WebSocketDisconnect, Depends
from app.auth.security import decode_token

ws_router = APIRouter(tags=["websocket"])

@ws_router.websocket("/ws/documents")
async def websocket_endpoint(websocket: WebSocket):
    # Get token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload.get("sub")
    await manager.connect(websocket, user_id)

    try:
        while True:
            # Keep connection alive, wait for any client message
            data = await websocket.receive_text()
            # Could handle ping/pong or subscription messages here
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
    except Exception:
        await manager.disconnect(websocket, user_id)
```

### 4. Frontend Chat View

```vue
<!-- frontend/src/views/ChatView.vue -->
<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Chip from 'primevue/chip'
import ProgressSpinner from 'primevue/progressspinner'
import api from '@/api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}

interface ChatResponse {
  answer: string
  sources: any[]
  model: string
  usage: { prompt_tokens: number; completion_tokens: number }
}

const toast = useToast()
const messages = ref<Message[]>([])
const inputMessage = ref('')
const loading = ref(false)
const messagesContainer = ref<HTMLElement>()

async function sendMessage() {
  if (!inputMessage.value.trim() || loading.value) return

  const query = inputMessage.value.trim()
  inputMessage.value = ''

  // Add user message
  messages.value.push({ role: 'user', content: query })

  loading.value = true
  try {
    const { data } = await api.post<ChatResponse>('/chat', {
      query,
      conversation_history: messages.value.slice(-4).map(m => ({
        role: m.role,
        content: m.content
      })),
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
    messagesContainer.value?.scrollTo({
      top: messagesContainer.value.scrollHeight,
      behavior: 'smooth'
    })
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail })
  } finally {
    loading.value = false
  }
}

function openSource(source: any) {
  // Navigate to document with chunk highlighted
  window.open(`/documents/${source.document_id}?chunk=${source.chunk_id}`, '_blank')
}
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-64px)]">
    <!-- Header -->
    <div class="border-b px-6 py-4">
      <h1 class="text-xl font-semibold">💬 Chat with your documents</h1>
      <p class="text-sm text-gray-500">Ask questions about your uploaded documents</p>
    </div>

    <!-- Messages -->
    <div ref="messagesContainer" class="flex-1 overflow-auto p-6 space-y-6">
      <div v-if="messages.length === 0" class="text-center text-gray-400 py-12">
        <p class="text-lg">Start a conversation</p>
        <p class="text-sm mt-2">Ask questions about your documents</p>
      </div>

      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']"
      >
        <div
          :class="[
            'max-w-2xl rounded-2xl px-4 py-3',
            msg.role === 'user'
              ? 'bg-blue-600 text-white rounded-br-md'
              : 'bg-gray-100 rounded-bl-md'
          ]"
        >
          <p class="whitespace-pre-wrap">{{ msg.content }}</p>

          <!-- Sources -->
          <div v-if="msg.sources?.length" class="mt-3 pt-3 border-t border-gray-200">
            <p class="text-xs text-gray-500 mb-2">Sources:</p>
            <div class="flex flex-wrap gap-2">
              <Chip
                v-for="source in msg.sources"
                :key="source.chunk_id"
                :label="source.filename"
                class="cursor-pointer hover:bg-blue-50"
                @click="openSource(source)"
              />
            </div>
          </div>
        </div>
      </div>

      <div v-if="loading" class="flex justify-start">
        <div class="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
          <ProgressSpinner style="width: 24px; height: 24px" />
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="border-t p-4">
      <form @submit.prevent="sendMessage" class="flex gap-3 max-w-4xl mx-auto">
        <InputText
          v-model="inputMessage"
          placeholder="Type your message..."
          class="flex-1"
          :disabled="loading"
        />
        <Button type="submit" label="Send" :loading="loading" />
      </form>
    </div>
  </div>
</template>
```

### 5. Search View

```vue
<!-- frontend/src/views/SearchView.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Chip from 'primevue/chip'
import ProgressSpinner from 'primevue/progressspinner'
import api from '@/api/client'

interface SearchResult {
  chunk_id: string
  content: string
  document_id: string
  filename: string
  format: string
  similarity: number
  metadata: any
}

const toast = useToast()
const query = ref('')
const results = ref<SearchResult[]>([])
const loading = ref(false)
const selectedFormat = ref<string | null>(null)

const formats = [
  { label: 'All', value: null },
  { label: 'PDF', value: 'pdf' },
  { label: 'DOCX', value: 'docx' },
  { label: 'XLSX', value: 'xlsx' }
]

async function search() {
  if (!query.value.trim() || loading.value) return

  loading.value = true
  try {
    const { data } = await api.post('/search', {
      query: query.value,
      top_k: 20,
      filters: selectedFormat.value ? { format: selectedFormat.value } : null
    })
    results.value = data.results
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail })
  } finally {
    loading.value = false
  }
}

function highlightText(text: string, query: string) {
  if (!query) return text
  const regex = new RegExp(`(${query})`, 'gi')
  return text.replace(regex, '<mark class="bg-yellow-200">$1</mark>')
}

function formatSimilarity(score: number) {
  return Math.round(score * 100) + '%'
}
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto">
    <h1 class="text-2xl font-bold mb-6">🔍 Search Documents</h1>

    <!-- Search Bar -->
    <form @submit.prevent="search" class="mb-6">
      <div class="flex gap-3">
        <InputText
          v-model="query"
          placeholder="Search your documents..."
          class="flex-1 text-lg"
        />
        <Button type="submit" label="Search" :loading="loading" />
      </div>

      <!-- Filters -->
      <div class="flex gap-2 mt-3">
        <Chip
          v-for="fmt in formats"
          :key="fmt.value"
          :label="fmt.label"
          :class="{ 'bg-blue-100 text-blue-700': selectedFormat === fmt.value }"
          class="cursor-pointer"
          @click="selectedFormat = fmt.value"
        />
      </div>
    </form>

    <!-- Results -->
    <div v-if="loading" class="text-center py-8">
      <ProgressSpinner />
    </div>

    <div v-else-if="results.length === 0 && query" class="text-center text-gray-400 py-8">
      No results found. Try a different search term.
    </div>

    <div v-else class="space-y-4">
      <Card v-for="result in results" :key="result.chunk_id" class="hover:shadow-md transition">
        <template #title>
          <div class="flex justify-between items-center">
            <span class="text-blue-600">{{ result.filename }}</span>
            <span class="text-sm text-green-600 font-medium">{{ formatSimilarity(result.similarity) }}</span>
          </div>
        </template>
        <template #content>
          <p
            class="text-gray-600"
            v-html="highlightText(result.content.slice(0, 300) + '...', query)"
          />
          <div class="flex items-center gap-4 text-xs text-gray-400 mt-2">
            <span>Format: {{ result.format.toUpperCase() }}</span>
            <span v-if="result.metadata?.page">Page: {{ result.metadata.page }}</span>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>
```

### 6. WebSocket Composable

```typescript
// frontend/src/composables/useWebSocket.ts
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/authStore'

export function useWebSocket(url: string) {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const messages = ref<any[]>([])

  function connect() {
    const authStore = useAuthStore()
    const wsUrl = `${url}?token=${authStore.accessToken}`

    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      connected.value = true
    }

    ws.value.onclose = () => {
      connected.value = false
      // Reconnect after 3 seconds
      setTimeout(connect, 3000)
    }

    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data)
      messages.value.push(data)
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  function send(data: any) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(data))
    }
  }

  onMounted(connect)

  onUnmounted(() => {
    ws.value?.close()
  })

  return {
    connected,
    messages,
    send
  }
}
```

## Todo List

- [ ] Create llm_service.py with chat generation
- [ ] Create chat.py routes
- [ ] Create websocket.py manager
- [ ] Add WebSocket endpoint to main.py
- [ ] Create ChatView.vue
- [ ] Create SearchView.vue
- [ ] Create useWebSocket composable
- [ ] Add streaming response support (optional)
- [ ] Test: Chat returns answer with sources
- [ ] Test: Search returns ranked results
- [ ] Test: WebSocket connects and receives updates

## Success Criteria

1. Chat answers include relevant document sources
2. Sources link to original documents
3. Search returns results with similarity scores
4. Filter by format works
5. WebSocket updates UI in real-time

## Next Steps

- Phase 07: Admin dashboard
