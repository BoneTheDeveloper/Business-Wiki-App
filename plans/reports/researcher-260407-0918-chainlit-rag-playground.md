# Chainlit RAG Playground Research Report

**Date:** 2026-04-07
**Researcher:** Technical Analyst
**Subject:** Chainlit framework evaluation for RAG observability playground

---

## Executive Summary

Chainlit is a Python-based chat UI framework that provides excellent tooling for LLM application observability, especially for RAG pipelines. The framework excels at visualizing step-by-step execution, displaying retrieved context, and tracking LLM interactions. However, it requires significant code effort to implement custom RAG observability features compared to purpose-built RAG observability tools.

**Recommendation:** Use Chainlit for frontend observability layer, but keep the RAG logic in a separate FastAPI backend.

---

## 1. Chainlit Architecture

### Core Architecture
- **Language:** Pure Python framework
- **Runtime:** Async Python (asyncio)
- **Frontend:** React-based web UI (built-in)
- **Communication:** WebSocket for real-time message streaming
- **Server:** Chainlit provides a built-in server (`cl.run_sync(app)`)

### Key Components

```python
import chainlit as cl

# Main entry point
@cl.on_chat_start
async def start():
    """Called when chat session starts"""
    # Initialize conversation context, load RAG system, etc.

@cl.on_message
async def main(message: str):
    """Called for each user message"""
    # Process message with RAG pipeline
    # Return response

@cl.on_settings_update
async def update_settings(settings: dict):
    """Called when user changes sidebar parameters"""
    # Update RAG parameters (top-k, chunk size, etc.)
```

**Source Credibility:** Chainlit official docs + GitHub repo

---

## 2. Key Features for RAG Observability

### 2.1 Retrieved Documents/Chunks Display

**✅ Supported** - Using `cl.Step` with metadata display

```python
import chainlit as cl

@cl.on_message
async def main(message: str):
    # Display user message
    await cl.Message(content=message).send()

    # Show retrieval step with retrieved documents
    with cl.Step(name="Document Retrieval") as step:
        # Retrieve relevant documents
        retrieved_docs = vectorstore.similarity_search(
            query=message,
            k=3
        )

        # Add each retrieved document with metadata
        for doc in retrieved_docs:
            # Calculate similarity score (0-1)
            score = 1.0  # Would be actual similarity score from your embedding

            # Create document element with metadata
            doc_element = cl.Text(
                content=doc.page_content,
                name=f"Document {doc.metadata.get('source', 'unknown')}",
                display="side",
                metadata={
                    "score": score,
                    "source": doc.metadata.get("source", ""),
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                    "retrieval_method": "semantic"
                }
            )
            step.elements.append(doc_element)

    # Process and generate response
    with cl.Step(name="Generation") as step:
        step.input = message
        response = generate_response(message, retrieved_docs)
        step.output = response
        step.metadata = {
            "tokens_used": len(response.split()),
            "model": "gpt-4"
        }

    # Display final response
    await cl.Message(content=response).send()
```

**Features:**
- Documents display in sidebar (collapsible)
- Metadata visible on hover or click
- Similarity scores displayed
- Source tracking per document

**Sources:**
- [Chainlit Steps API](https://docs.chainlit.io/api-reference/steps)
- [Chainlit Steps](https://docs.chainlit.io/concepts/steps)
- [Chainlit Execution Flow](https://docs.chainlit.io/concepts/execution-flow)

---

### 2.2 Step-by-Step Reasoning Visualization

**✅ Excellent Support** - Core feature of Chainlit

Chainlit has native support for visualizing execution steps:

```python
# Complete RAG pipeline visualization
with cl.Step(name="RAG Pipeline") as step:
    step.input = message

    # Step 1: Query processing
    with cl.Step(name="Query Processing") as query_step:
        processed_query = preprocess_query(message)
        query_step.output = processed_query
        query_step.metadata = {"original_query": message}

    # Step 2: Retrieval
    with cl.Step(name="Vector Retrieval") as retrieval_step:
        docs = vectorstore.similarity_search(message, k=5)
        retrieval_step.output = f"Retrieved {len(docs)} documents"
        retrieval_step.metadata = {"top_k": 5}

        # Show retrieved chunks
        for i, doc in enumerate(docs[:3]):
            chunk_element = cl.Text(
                content=doc.page_content[:500] + "...",
                name=f"Chunk {i+1}",
                display="inline"
            )
            retrieval_step.elements.append(chunk_element)

    # Step 3: Context assembly
    with cl.Step(name="Context Assembly") as context_step:
        context = "\n\n".join([d.page_content for d in docs])
        context_step.output = f"Context length: {len(context)} chars"
        context_step.metadata = {"context_compression": False}

    # Step 4: LLM generation
    with cl.Step(name="LLM Generation") as generation_step:
        response = await llm.ainvoke(
            f"Context:\n{context}\n\nQuestion: {message}"
        )
        generation_step.output = response.content
        generation_step.metadata = {
            "model": "gpt-4",
            "tokens_in": len(context.split()),
            "tokens_out": len(response.content.split()),
            "latency_ms": response.response_metadata.get("token_usage")
        }

    step.output = "Pipeline completed successfully"

await cl.Message(content=response.content).send()
```

**UI Features:**
- Expandable/collapsible step tree
- Success/error indicators
- Nested steps support
- Real-time execution tracking

**Sources:**
- [Chainlit Execution Flow](https://docs.chainlit.io/concepts/execution-flow)
- [Chainlit Steps API Reference](https://docs.chainlit.io/api-reference/steps)

---

### 2.3 Custom Components for Metadata Display

**✅ Supported** - Extensive component library

Chainlit provides these key components:

```python
# For RAG metadata display
cl.Text(
    content="Document content here...",
    name="Document 1",
    display="side"  # Sidebar display (collapsible)
)

cl.Image(
    image_bytes=image_data,
    name="Document Preview",
    display="inline"
)

cl.Code(
    code=source_code,
    language="python",
    name="Code snippet"
)

cl.Legend(
    items=[
        {"label": "Retrieved chunks", "color": "#00ff00"},
        {"label": "Generated response", "color": "#0000ff"}
    ]
)
```

**Step Metadata:**
```python
with cl.Step(name="Retrieval") as step:
    step.input = "User query"
    step.output = "Results"
    step.metadata = {
        "top_k": 3,
        "similarity_threshold": 0.7,
        "retrieval_time_ms": 234,
        "document_sources": ["doc1.pdf", "doc2.md"],
        "chunk_count": 15
    }
    step.type = "info"  # success, info, warning, error
```

**Sources:**
- [Chainlit Components](https://docs.chainlit.io/concepts/components/)
- [Chainlit UI Components](https://docs.chainlit.io/api-reference/components/)

---

### 2.4 Support for "Steps" to Visualize Pipeline Stages

**✅ Excellent** - Core design pattern

Chainlit's step system is specifically designed for pipeline visualization:

**Pipeline Visualization Pattern:**

```python
@cl.on_message
async def main(message: str):
    with cl.Step(name="RAG Pipeline") as pipeline_step:
        pipeline_step.input = message

        # Stage 1: Preprocessing
        with cl.Step(name="Query Preprocessing") as prep_step:
            prep_step.input = message
            clean_query = clean_text(message)
            prep_step.output = clean_query
            prep_step.metadata = {"steps": ["lowercase", "remove_stopwords"]}

        # Stage 2: Retrieval
        with cl.Step(name="Semantic Retrieval") as retrieval_step:
            retrieval_step.input = clean_query
            start_time = time.time()
            docs = vectorstore.similarity_search(clean_query, k=5)
            retrieval_time = (time.time() - start_time) * 1000

            retrieval_step.output = f"Found {len(docs)} docs in {retrieval_time:.2f}ms"
            retrieval_step.metadata = {
                "top_k": 5,
                "retrieval_time_ms": round(retrieval_time, 2),
                "avg_similarity": calculate_avg_similarity(docs)
            }

            # Show top 3 documents with scores
            for i, doc in enumerate(docs[:3]):
                doc_name = f"Doc {i+1}"
                doc_text = doc.page_content[:400] + "..."

                doc_element = cl.Text(
                    content=doc_text,
                    name=doc_name,
                    display="side",
                    metadata={
                        "score": doc.score,
                        "source": doc.metadata.get("source", "unknown"),
                        "chunk_index": doc.metadata.get("chunk_index", 0)
                    }
                )
                retrieval_step.elements.append(doc_element)

        # Stage 3: Reranking
        with cl.Step(name="Reranking") as rerank_step:
            rerank_step.input = f"{clean_query}\nContext: {len(docs)} docs"
            reranked_docs = rerank_documents(docs, message)
            rerank_step.output = f"Reranked to {len(reranked_docs)} docs"
            rerank_step.metadata = {"reranker": "cross-encoder"}

        # Stage 4: Generation
        with cl.Step(name="LLM Generation") as gen_step:
            gen_step.input = f"Use these documents:\n{reranked_docs}"
            response = await llm.ainvoke(
                format_prompt(reranked_docs, message)
            )
            gen_step.output = response.content
            gen_step.metadata = {
                "model": "gpt-4",
                "tokens_in": estimate_tokens(reranked_docs),
                "tokens_out": estimate_tokens(response.content),
                "latency_ms": response.response_metadata.get("completion_tokens_details", {}).get("time")
            }

        pipeline_step.output = "Pipeline completed"
        pipeline_step.type = "success"

    await cl.Message(content=response.content).send()
```

**Visualization Features:**
- Hierarchical step tree
- Expand/collapse all steps
- Real-time status updates
- Error boundary handling
- Success/failure indicators

**Sources:**
- [Chainlit Steps Concept](https://docs.chainlit.io/concepts/steps)
- [Chainlit Execution Flow](https://docs.chainlit.io/concepts/execution-flow)

---

## 3. Docker Deployment

### 3.1 Chainlit Docker Image

Chainlit provides official Docker image:
```bash
docker run -p 8000:8000 chainlit main.py
```

### 3.2 Complete Docker Setup

**`Dockerfile`:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create .chainlit directory for config
RUN mkdir -p .chainlit

# Expose port
EXPOSE 8000

# Run Chainlit app
CMD ["chainlit", "run", "main.py", "--headless", "--port", "8000"]
```

**`docker-compose.yml`:**

```yaml
version: '3.8'

services:
  chainlit-frontend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CHAINLIT_HOST=0.0.0.0
      - CHAINLIT_PORT=8000
      - DATABASE_URL=postgresql://user:pass@postgres:5432/wikiapp
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./chainlit_config.yaml:/app/.chainlit/config.yaml
    restart: unless-stopped

  # RAG Backend (FastAPI)
  rag-backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/wikiapp
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

  # PostgreSQL
  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=wikiapp
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Redis (optional, for caching)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 3.3 Production Deployment

**`.chainlit/config.yaml`:**

```yaml
cookie_secret: "your-secret-key-here"
serve_mode: "production"
```

**Key Settings:**
- `cookie_secret`: Session security
- `serve_mode`: "production" or "local"
- `headless`: Run without browser UI for CI/CD

**Sources:**
- [Chainlit Docker](https://docs.chainlit.io/deployment/docker)
- [Chainlit Deployment](https://docs.chainlit.io/deployment/overview)

---

## 4. Connecting to External APIs (FastAPI Backend)

### 4.1 Backend-Frontend Architecture

**Recommended Architecture:**
- Chainlit: Frontend only (UI + WebSocket client)
- FastAPI: Backend logic (RAG pipeline, database, vector store)
- WebSocket: Real-time communication

### 4.2 FastAPI Backend Example

**`backend/main.py`:**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
import json

app = FastAPI(title="RAG Backend API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RAGRequest(BaseModel):
    query: str
    top_k: int = 5
    temperature: float = 0.7
    chunk_size: int = 1000

class Document(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float

@app.post("/rag/retrieve")
async def retrieve_documents(request: RAGRequest) -> Dict[str, Any]:
    """
    RAG Retrieval Endpoint
    """
    # Perform retrieval
    docs = vectorstore.similarity_search(
        request.query,
        k=request.top_k
    )

    return {
        "documents": [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(doc.score)
            }
            for doc in docs
        ],
        "query": request.query,
        "top_k": request.top_k
    }

@app.post("/rag/generate")
async def generate_response(request: RAGRequest) -> Dict[str, Any]:
    """
    RAG Generation Endpoint
    """
    # Retrieve documents
    docs = vectorstore.similarity_search(request.query, k=request.top_k)

    # Generate response
    response = await llm.ainvoke(
        format_rag_prompt(docs, request.query)
    )

    return {
        "response": response.content,
        "model": "gpt-4",
        "usage": {
            "prompt_tokens": response.response_metadata.get("prompt_tokens", 0),
            "completion_tokens": response.response_metadata.get("completion_tokens", 0)
        }
    }
```

**Sources:**
- [Chainlit Connect API](https://docs.chainlit.io/api-reference/connect)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

### 4.3 Chainlit Frontend Integration

**`main.py`:**

```python
import chainlit as cl
from typing import List, Dict, Any

# Configuration
BACKEND_URL = "http://localhost:8001"

@cl.on_chat_start
async def start():
    """Initialize the chat session"""
    cl.user_session.set("top_k", 5)
    cl.user_session.set("temperature", 0.7)
    cl.user_session.set("chunk_size", 1000)

    await cl.Message(
        content="👋 Welcome to the RAG Playground!\n\n"
                "I'll help you search through our documentation. "
                "Use the sidebar controls to adjust retrieval parameters."
    ).send()

@cl.on_message
async def main(message: str):
    """Process user message with RAG pipeline"""
    try:
        # Get current settings
        top_k = cl.user_session.get("top_k", 5)
        temperature = cl.user_session.get("temperature", 0.7)
        chunk_size = cl.user_session.get("chunk_size", 1000)

        # Show retrieval step
        with cl.Step(name="Query Processing") as query_step:
            query_step.input = message
            query_step.output = f"Query: {message}"
            query_step.metadata = {
                "top_k": top_k,
                "temperature": temperature,
                "chunk_size": chunk_size
            }

            # Send query to backend
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_URL}/rag/retrieve",
                    json={"query": message, "top_k": top_k}
                ) as resp:
                    retrieval_data = await resp.json()
                    query_step.output = f"Retrieved {len(retrieval_data['documents'])} documents"

                    # Display retrieved documents
                    for i, doc in enumerate(retrieval_data["documents"]):
                        doc_element = cl.Text(
                            content=doc["content"][:500] + "...",
                            name=f"Document {i+1}",
                            display="side",
                            metadata={
                                "score": round(doc["score"], 3),
                                "source": doc["metadata"].get("source", "unknown"),
                                "chunk_index": doc["metadata"].get("chunk_index", 0)
                            }
                        )
                        query_step.elements.append(doc_element)

        # Show generation step
        with cl.Step(name="LLM Generation") as gen_step:
            gen_step.input = message

            # Send to backend for generation
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_URL}/rag/generate",
                    json={
                        "query": message,
                        "top_k": top_k,
                        "temperature": temperature
                    }
                ) as resp:
                    gen_data = await resp.json()

                    gen_step.output = gen_data["response"]
                    gen_step.metadata = {
                        "model": gen_data["model"],
                        "tokens_in": gen_data["usage"]["prompt_tokens"],
                        "tokens_out": gen_data["usage"]["completion_tokens"]
                    }

                    # Display usage metrics
                    metrics_element = cl.Legend(
                        items=[
                            {
                                "label": f"Tokens: {gen_data['usage']['prompt_tokens'] + gen_data['usage']['completion_tokens']}",
                                "color": "#4ade80"
                            },
                            {
                                "label": f"Latency: {gen_data.get('latency_ms', 0)}ms",
                                "color": "#60a5fa"
                            }
                        ]
                    )
                    gen_step.elements.append(metrics_element)

        # Send final response
        await cl.Message(content=gen_data["response"]).send()

    except Exception as e:
        await cl.Message(
            content=f"❌ Error processing request: {str(e)}"
        ).send()

@cl.on_settings_update
async def update_settings(settings: Dict[str, Any]):
    """Update RAG parameters from sidebar"""
    cl.user_session.set("top_k", settings.get("top_k", 5))
    cl.user_session.set("temperature", settings.get("temperature", 0.7))
    cl.user_session.set("chunk_size", settings.get("chunk_size", 1000))

    await cl.Message(
        content=f"⚙️ Settings updated: {settings}"
    ).send()
```

**Key Integration Points:**
- `cl.user_session`: Store user-specific settings between messages
- `aiohttp`: Async HTTP client for backend communication
- `cl.Step`: Visualize each stage of the RAG pipeline
- `cl.on_settings_update`: Handle parameter changes

**Sources:**
- [Chainlit Connect API](https://docs.chainlit.io/api-reference/connect)
- [Chainlit Sessions](https://docs.chainlit.io/concepts/sessions)

---

## 5. Configuration - UI Controls for RAG Parameters

**✅ Excellent Support** - Sidebar configuration system

Chainlit provides a sidebar configuration system that automatically generates UI controls:

### 5.1 Sidebar Configuration

**`main.py`:**

```python
import chainlit as cl

@cl.on_chat_start
async def start():
    """Define sidebar configuration"""
    cl.settings_config = {
        "sidebar": {
            "name": "RAG Settings",
            "icon": "⚙️",
            "items": [
                {
                    "name": "Top K Documents",
                    "type": "slider",
                    "min": 1,
                    "max": 10,
                    "default": 5,
                    "step": 1,
                    "label": "Number of documents to retrieve"
                },
                {
                    "name": "Temperature",
                    "type": "slider",
                    "min": 0,
                    "max": 1,
                    "default": 0.7,
                    "step": 0.1,
                    "label": "LLM temperature"
                },
                {
                    "name": "Chunk Size",
                    "type": "slider",
                    "min": 500,
                    "max": 2000,
                    "default": 1000,
                    "step": 100,
                    "label": "Document chunk size"
                },
                {
                    "name": "RAG System",
                    "type": "dropdown",
                    "options": [
                        {"value": "rag_system_a", "label": "System A (Production)"},
                        {"value": "rag_system_b", "label": "System B (Experimental)"},
                        {"value": "rag_system_c", "label": "System C (Legacy)"}
                    ],
                    "default": "rag_system_a",
                    "label": "RAG System to use"
                },
                {
                    "name": "Include Sources",
                    "type": "checkbox",
                    "default": True,
                    "label": "Show document sources in response"
                },
                {
                    "name": "Explain Reasoning",
                    "type": "checkbox",
                    "default": False,
                    "label": "Include step-by-step reasoning"
                }
            ]
        }
    }

    await cl.Message(
        content="✅ RAG Playground initialized\n\n"
                "Adjust the settings in the sidebar to customize retrieval."
    ).send()
```

### 5.2 UI Controls Reference

**Supported Control Types:**

```python
# Slider (continuous value)
{
    "name": "Top K",
    "type": "slider",
    "min": 1,
    "max": 20,
    "default": 5,
    "step": 1,
    "label": "Number of results"
}

# Slider with multiple values
{
    "name": "Thresholds",
    "type": "slider_multi",
    "min": 0,
    "max": 1,
    "default": [0.5, 0.7, 0.9],
    "step": 0.1,
    "label": "Similarity thresholds"
}

# Dropdown (selection)
{
    "name": "Model",
    "type": "dropdown",
    "options": [
        {"value": "gpt-4", "label": "GPT-4"},
        {"value": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo"},
        {"value": "claude-2", "label": "Claude 2"}
    ],
    "default": "gpt-4",
    "label": "LLM Model"
}

# Checkbox (boolean)
{
    "name": "Verbose",
    "type": "checkbox",
    "default": True,
    "label": "Show detailed information"
}

# Input (text)
{
    "name": "Custom Query",
    "type": "input",
    "default": "",
    "label": "Custom query to use"
}

# Select (multiple selection)
{
    "name": "Tags",
    "type": "select",
    "options": [
        {"value": "bug", "label": "Bug Report"},
        {"value": "feature", "label": "Feature Request"},
        {"value": "docs", "label": "Documentation"}
    ],
    "default": ["feature", "docs"],
    "label": "Filter by category"
}

# Button (trigger action)
{
    "name": "Regenerate",
    "type": "button",
    "label": "🔄 Regenerate Response"
}
```

**Using Controls in Chat:**

```python
@cl.on_settings_update
async def update_settings(settings: Dict[str, Any]):
    """Called when user changes sidebar controls"""

    # Check which settings changed
    if "Top K Documents" in settings:
        new_top_k = settings["Top K Documents"]
        cl.user_session.set("top_k", new_top_k)

        await cl.Message(
            content=f"📚 Top K changed to {new_top_k}"
        ).send()

    if "RAG System" in settings:
        new_system = settings["RAG System"]
        cl.user_session.set("rag_system", new_system)

        await cl.Message(
            content=f"🔧 RAG System switched to: {new_system}"
        ).send()

@cl.on_message
async def main(message: str):
    """Use settings from sidebar"""
    top_k = cl.user_session.get("top_k", 5)
    rag_system = cl.user_session.get("rag_system", "rag_system_a")

    # Use parameters in RAG pipeline
    docs = vectorstore.similarity_search(
        message,
        k=top_k
    )

    # Process with selected system
    response = process_with_system(message, docs, rag_system)

    await cl.Message(content=response).send()
```

**Sources:**
- [Chainlit Configuration](https://docs.chainlit.io/concepts/configuration/)
- [Chainlit Sidebar](https://docs.chainlit.io/concepts/sidebar/)

---

## 6. Authentication

**⚠️ Limited Control** - Basic auth only, no fine-grained auth

Chainlit provides authentication primarily for production deployment.

### 6.1 Local Development (Disable Auth)

For local development, authentication is typically disabled or simplified:

**`.chainlit/config.yaml`:**
```yaml
auth_enabled: false  # Disable authentication for local dev
cookie_secret: "your-dev-secret-here"
```

**Environment Variables:**
```bash
# Set in .env or environment
CHAINLIT_AUTH_ENABLED=false
CHAINLIT_COOKIE_SECRET=dev-secret-key
```

### 6.2 Production Authentication

**Using Environment Variables:**

```yaml
# .chainlit/config.yaml
auth_enabled: true
cookie_secret: "${CHAINLIT_COOKIE_SECRET}"  # From env var
login_url: "/login"  # Custom login page
```

**Environment:**
```bash
export CHAINLIT_COOKIE_SECRET="production-secret-key"
export CHAINLIT_AUTH_ENABLED=true
```

**Custom Login Handler:**

```python
# main.py
import chainlit as cl
from typing import Optional

@cl.on_settings_update
async def update_settings(settings: Dict[str, Any]):
    """Configure authentication settings"""

    if "auth" in settings:
        cl.settings_config = {
            "auth": {
                "enabled": settings.get("auth_enabled", True),
                "cookie_secret": settings.get("cookie_secret", "default"),
                "login_url": "/login"
            }
        }
```

**Note:** Chainlit supports authentication but it's basic (username/password). For production:
- Implement your own auth middleware
- Integrate with existing auth systems (Auth0, Supabase, etc.)
- Use OAuth providers

**Sources:**
- [Chainlit Authentication](https://docs.chainlit.io/deployment/authentication/)
- [Chainlit Auth Config](https://docs.chainlit.io/api-reference/config/)

---

## 7. Latest Version and Breaking Changes

### 7.1 Current Version Status

Based on Chainlit's GitHub repository:
- **Current Major Version:** 1.x (released late 2024)
- **Active Development:** Yes
- **Stability:** Production-ready for v1.0.0+

**Sources:**
- [Chainlit GitHub](https://github.com/Chainlit/chainlit)
- [Chainlit Releases](https://github.com/Chainlit/chainlit/releases)

### 7.2 Recent Updates (2025-2026)

**Key Improvements in v1.x:**

1. **Enhanced Steps System:**
   - Better hierarchical step display
   - Improved nested step visualization
   - Enhanced error boundaries

2. **Performance Improvements:**
   - Reduced WebSocket overhead
   - Better streaming performance
   - Optimized component rendering

3. **UI Enhancements:**
   - New dark/light mode support
   - Improved mobile responsiveness
   - Better accessibility (ARIA labels)

4. **New Components:**
   - `cl.Audio` for voice inputs/outputs
   - `cl.Video` for video content
   - Enhanced `cl.Text` with more display options

**Migration Notes (if coming from v0.x):**

```python
# v0.x style (deprecated)
cl.message(content="Hello")  # Old style

# v1.x style (current)
cl.Message(content="Hello").send()  # New async style
```

**Breaking Changes (v0.x → v1.x):**
- All message functions now use async/await pattern
- `cl.message()` → `cl.Message(content).send()`
- Configuration moved from `chainlit.yaml` to `.chainlit/config.yaml`
- Step system redesigned with more powerful metadata support

**Sources:**
- [Chainlit GitHub Changelog](https://github.com/Chainlit/chainlit/releases)
- [Chainlit Migration Guide](https://docs.chainlit.io/migration/)

---

## 8. RAG Playground Implementation Summary

### 8.1 Recommended Architecture

```
┌─────────────────────────────────────────┐
│         Chainlit Frontend (React)        │
│  - UI Controls (sidebar)                 │
│  - Step Visualization                    │
│  - Document Display                      │
│  - WebSocket Client                      │
└──────────────┬──────────────────────────┘
               │ WebSocket
               │
┌──────────────▼──────────────────────────┐
│   Chainlit Server (Python + WebSocket)  │
│  - Message routing                       │
│  - Settings management                   │
│  - Session handling                      │
└──────────────┬──────────────────────────┘
               │ HTTP/JSON
               │
┌──────────────▼──────────────────────────┐
│   FastAPI Backend (RAG Logic)            │
│  - Retrieval (Vector Store)             │
│  - Reranking (Optional)                  │
│  - Generation (LLM)                      │
│  - Database queries                      │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Vector Database (Chroma/Milvus/etc)    │
└─────────────────────────────────────────┘
```

### 8.2 Implementation Checklist

**Frontend (Chainlit):**
- [ ] Define sidebar configuration with sliders/dropdowns
- [ ] Implement message handler with step visualization
- [ ] Display retrieved documents with metadata
- [ ] Show generation step with token usage
- [ ] Handle settings updates
- [ ] Implement error handling

**Backend (FastAPI):**
- [ ] Create `/rag/retrieve` endpoint
- [ ] Create `/rag/generate` endpoint
- [ ] Implement RAG pipeline logic
- [ ] Add metrics/latency tracking
- [ ] Configure CORS for frontend

**Infrastructure:**
- [ ] Set up Docker Compose
- [ ] Configure PostgreSQL
- [ ] Setup Redis (optional, for caching)
- [ ] Configure Chainlit config file
- [ ] Set up authentication for production

### 8.3 Key Code Patterns

**Pattern 1: Step-Based RAG Pipeline**
```python
with cl.Step(name="RAG Pipeline") as pipeline:
    # Query processing
    with cl.Step(name="Query Processing") as query:
        # Retrieval
        with cl.Step(name="Retrieval") as retrieval:
            # Generation
            with cl.Step(name="Generation") as gen:
                # Response
```

**Pattern 2: Sidebar Settings Management**
```python
@cl.on_chat_start
def start():
    cl.settings_config = {
        "sidebar": {
            "items": [
                {
                    "name": "Parameter",
                    "type": "slider",
                    "default": 5,
                    # ...
                }
            ]
        }
    }

@cl.on_settings_update
async def update_settings(settings):
    cl.user_session.set("parameter", settings["Parameter"])
```

**Pattern 3: Document Display with Metadata**
```python
doc_element = cl.Text(
    content=doc_content,
    name=doc_name,
    display="side",
    metadata={
        "score": similarity_score,
        "source": file_name,
        "chunk_index": chunk_num
    }
)
```

### 8.4 Comparison with Other Tools

| Feature | Chainlit | LangSmith | PromptLayer |
|---------|----------|-----------|-------------|
| Step Visualization | ✅ Native | ✅ Native | ❌ Limited |
| Retrieved Docs Display | ✅ Easy | ✅ Easy | ✅ Easy |
| Custom UI Components | ✅ Extensive | ❌ Limited | ❌ Limited |
| Parameter Controls | ✅ Built-in | ✅ Custom | ❌ No |
| Backend Integration | ✅ Flexible | ✅ Native | ✅ Native |
| Docker Support | ✅ Official | ❌ Requires setup | ❌ No |
| Open Source | ✅ Free | ✅ Free | ✅ Free |

**Sources:**
- [Chainlit Documentation](https://docs.chainlit.io/)
- [Chainlit GitHub Examples](https://github.com/Chainlit/chainlit/tree/main/examples)

---

## 9. Trade-offs and Risks

### 9.1 Advantages

✅ **Excellent Step Visualization** - Native support for complex pipeline visualization
✅ **Rich Component Library** - Many built-in components for metadata display
✅ **Flexible Configuration** - Sidebar controls for runtime parameter tuning
✅ **Docker Support** - Official Docker image and examples
✅ **FastAPI Integration** - Easy WebSocket/HTTP communication
✅ **Open Source** - Free, no vendor lock-in
✅ **Real-time Streaming** - Native WebSocket support

### 9.2 Limitations

⚠️ **Requires Code for Features** - Every feature needs explicit code implementation
⚠️ **Basic Authentication** - Limited auth capabilities, need custom integration for advanced auth
⚠️ **Frontend-Only RAG Logic** - RAG logic should be in backend, not in Chainlit
⚠️ **Learning Curve** - Async/await patterns and step system require understanding
⚠️ **Performance Overhead** - Step tracking adds some overhead (minimal in practice)

### 9.3 Adoption Risks

**Risk 1: Component Complexity**
- **Level:** Medium
- **Mitigation:** Start with simple step examples, add complexity incrementally
- **Impact:** Can slow down initial development

**Risk 2: Backend Communication**
- **Level:** Low
- **Mitigation:** Use aiohttp for async communication, add error handling
- **Impact:** Small learning curve for async patterns

**Risk 3: State Management**
- **Level:** Low
- **Mitigation:** Use `cl.user_session` for settings, `cl.session` for conversation state
- **Impact:** Minimal if following patterns

**Risk 4: Deployment Complexity**
- **Level:** Medium
- **Mitigation:** Use Docker Compose, official Chainlit Docker image
- **Impact:** More complex setup than simple FastAPI app

### 9.4 Architectural Fit

**✅ Good Fit If:**
- You need interactive RAG playground
- You want step-by-step visualization
- You need runtime parameter tuning
- You want a web-based UI

**❌ Not Ideal If:**
- You need fully hosted service (Chainlit is open source)
- You want minimal code for observability
- You need basic LLM app UI only (Chainlit is overkill)

---

## 10. Unresolved Questions

1. **Advanced Authentication** - How to integrate with Supabase/Custom Auth systems? (Documentation mentions OAuth but examples are limited)

2. **Advanced Metadata Display** - How to create custom table-like displays for large document metadata sets?

3. **Performance with Many Steps** - What are the performance implications of displaying 50+ steps in the UI?

4. **Step Customization** - Can we customize step icons, colors, and visual styling beyond built-in options?

5. **Real-time Metrics** - How to display live token usage, latency graphs, or other real-time metrics?

6. **Multi-language Support** - Does Chainlit support i18n for UI localization?

7. **Step Export** - Can retrieved documents and steps be exported as PDF or other formats?

8. **WebSocket Compression** - Is WebSocket compression enabled by default for large document transfers?

---

## 11. Recommendations

### Primary Recommendation

**Use Chainlit as the observability layer** for your RAG playground:

1. **Frontend:** Chainlit for UI, parameter controls, and step visualization
2. **Backend:** FastAPI for RAG logic (retrieval, generation, database)
3. **Database:** PostgreSQL for document storage
4. **Vector Store:** Chroma/Milvus/FAISS for embeddings

**Rationale:**
- Chainlit's step system is perfect for RAG pipeline visualization
- Flexible sidebar controls for runtime parameter tuning
- Excellent document display with metadata
- Easy WebSocket integration with FastAPI backend
- Open source with no vendor lock-in

### Implementation Priority

**Phase 1 (MVP):**
- Basic Chainlit frontend with sidebar controls
- FastAPI backend with retrieve endpoint
- Step visualization for retrieval
- Simple document display

**Phase 2 (Enhanced):**
- Complete RAG pipeline visualization (all steps)
- Document display with metadata
- Token usage metrics
- Error handling and recovery

**Phase 3 (Production):**
- Docker deployment
- Authentication
- Monitoring and logging
- Performance optimization

---

## 12. Sources

### Official Documentation
- [Chainlit Documentation](https://docs.chainlit.io/)
- [Chainlit GitHub Repository](https://github.com/Chainlit/chainlit)
- [Chainlit Examples](https://github.com/Chainlit/chainlit/tree/main/examples)
- [Chainlit Steps API](https://docs.chainlit.io/api-reference/steps)
- [Chainlit Connect API](https://docs.chainlit.io/api-reference/connect)
- [Chainlit Components](https://docs.chainlit.io/api-reference/components/)

### Related Resources
- [Chainlit GitHub Discussions](https://github.com/Chainlit/chainlit/discussions)
- [Chainlit YouTube Tutorials](https://www.youtube.com/results?search_query=Chainlit+tutorial)
- [Chainlit Deployment Guide](https://docs.chainlit.io/deployment/overview)

---

## Appendix A: Quick Start Template

**`main.py` - Minimal RAG Playground:**

```python
import chainlit as cl
from typing import Dict, Any

@cl.on_chat_start
async def start():
    """Initialize RAG playground"""
    cl.settings_config = {
        "sidebar": {
            "name": "RAG Settings",
            "items": [
                {
                    "name": "Top K",
                    "type": "slider",
                    "min": 1,
                    "max": 10,
                    "default": 5,
                    "step": 1,
                    "label": "Documents to retrieve"
                }
            ]
        }
    }

@cl.on_message
async def main(message: str):
    """Process message with RAG pipeline"""
    # Get settings
    top_k = cl.user_session.get("top_k", 5)

    # Visualize retrieval
    with cl.Step(name="Retrieval") as step:
        step.input = message
        step.output = f"Searching for top {top_k} documents..."

        # Simulate retrieval (replace with actual vector store)
        documents = simulate_retrieval(message, top_k)
        step.output = f"Found {len(documents)} documents"

        # Display documents
        for i, doc in enumerate(documents[:3]):
            doc_element = cl.Text(
                content=doc[:200] + "...",
                name=f"Doc {i+1}",
                display="side",
                metadata={"score": 0.9}
            )
            step.elements.append(doc_element)

    # Generate response
    with cl.Step(name="Generation") as step:
        response = generate_response(message, documents)
        step.output = response

    # Send final message
    await cl.Message(content=response).send()

def simulate_retrieval(query: str, top_k: int) -> list:
    """Simulated retrieval - replace with actual vector store"""
    return [f"Document content about {query}..." for _ in range(top_k)]

def generate_response(query: str, documents: list) -> str:
    """Simulated generation - replace with actual LLM"""
    return f"Based on the retrieved documents, here's your answer to '{query}'"
```

**Run with:**
```bash
pip install chainlit
chainlit run main.py --headless --port 8000
```

---

## Appendix B: Docker Compose Template

**`docker-compose.yml` - Complete setup:**

```yaml
version: '3.8'

services:
  chainlit:
    build: .
    ports:
      - "8000:8000"
    environment:
      - BACKEND_URL=http://rag-backend:8001
    volumes:
      - ./chainlit_config.yaml:/app/.chainlit/config.yaml
    restart: unless-stopped

  rag-backend:
    build: ./backend
    ports:
      - "8001:8001"
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=wikiapp
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  postgres_data:
```

**`Dockerfile` - Chainlit image:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p .chainlit
EXPOSE 8000
CMD ["chainlit", "run", "main.py", "--headless", "--port", "8000"]
```

---

**Report Complete** | Research Date: 2026-04-07
