---
title: "Phase 2: RAG Service Rewrite"
description: "Replace AsyncOpenAI with google-genai for embeddings, add L2 normalization"
status: pending
priority: P1
effort: 45m
phase: 2
---

## Context Links
- [Plan Overview](plan.md)
- [Phase 1: Config & Dependencies](phase-01-config-and-dependencies.md)
- Current file: `backend/app/services/rag_service.py`

## Overview

Rewrite `RAGService` to use `google.genai.Client` for embeddings. The critical change is L2 normalization of embedding vectors -- Gemini embeddings at non-3072 dimensions require normalization for accurate cosine similarity with pgvector's `<=>` operator.

## Key Insights

1. **Normalization is NOT optional.** Gemini `gemini-embedding-001` at `output_dimensionality=1536` produces vectors that are NOT unit-normalized. pgvector's cosine distance (`<=>`) assumes normalized vectors for optimal performance. Without normalization, similarity scores will be wrong.
2. **Batch API difference.** OpenAI accepts `input=list[str]` in one call. Gemini `embed_content` accepts `contents=list[str]` natively -- no manual batching needed for reasonable sizes.
3. **Async API.** Use `client.aio.models.embed_content()` for async operations.

## Requirements

### Functional
- `embed(text: str) -> List[float]` -- single text embedding, L2-normalized
- `embed_batch(texts: List[str]) -> List[List[float]]` -- batch embedding, all L2-normalized
- `search(...)` -- unchanged SQL logic, receives normalized vectors
- `chunk_text(...)` -- completely unchanged (uses langchain text splitter)

### Non-Functional
- Embedding calls must be async (non-blocking)
- Graceful error when `GOOGLE_API_KEY` not set
- Singleton pattern preserved

## Architecture

```python
# Before (OpenAI)
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
response = await client.embeddings.create(model=..., input=..., dimensions=1536)

# After (Gemini)
from google import genai
from google.genai import types
client = genai.Client(api_key=settings.GOOGLE_API_KEY)
result = await client.aio.models.embed_content(
    model="gemini-embedding-001",
    contents=["text"],
    config=types.EmbedContentConfig(output_dimensionality=1536)
)
# result.embeddings[0].values -> list[float]
```

### Normalization Logic
```python
import numpy as np

def _normalize(values: list[float]) -> list[float]:
    arr = np.array(values, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return values
    return (arr / norm).tolist()
```

## Related Code Files

### Modify
- `backend/app/services/rag_service.py` -- full rewrite of embedding logic

### No Change
- `backend/app/services/rag_service.py` -- `chunk_text()` and `search()` SQL unchanged
- `backend/app/models/document.py` -- Vector(1536) column unchanged

## Implementation Steps

1. **Update imports**
   - Remove: `from openai import AsyncOpenAI`
   - Add: `from google import genai`, `from google.genai import types`, `import numpy as np`

2. **Update `__init__`**
   ```python
   self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
   self.embed_model = "gemini-embedding-001"
   self.embed_dimensions = 1536
   # splitter unchanged
   ```

3. **Add normalization helper** (private method)
   ```python
   @staticmethod
   def _normalize(values: list[float]) -> list[float]:
       arr = np.array(values, dtype=np.float32)
       norm = np.linalg.norm(arr)
       if norm == 0:
           return values
       return (arr / norm).tolist()
   ```

4. **Rewrite `embed()`**
   ```python
   async def embed(self, text: str) -> list[float]:
       if not settings.GOOGLE_API_KEY:
           raise ValueError("GOOGLE_API_KEY not configured")
       result = await self.client.aio.models.embed_content(
           model=self.embed_model,
           contents=[text],
           config=types.EmbedContentConfig(output_dimensionality=self.embed_dimensions)
       )
       return self._normalize(result.embeddings[0].values)
   ```

5. **Rewrite `embed_batch()`**
   ```python
   async def embed_batch(self, texts: list[str]) -> list[list[float]]:
       if not settings.GOOGLE_API_KEY:
           raise ValueError("GOOGLE_API_KEY not configured")
       if not texts:
           return []
       result = await self.client.aio.models.embed_content(
           model=self.embed_model,
           contents=texts,
           config=types.EmbedContentConfig(output_dimensionality=self.embed_dimensions)
       )
       return [self._normalize(e.values) for e in result.embeddings]
   ```
   Note: Gemini handles batching natively. If batch sizes exceed API limits (100+), add chunking logic similar to current OpenAI approach. Start without chunking -- Gemini handles large batches well.

6. **Leave `chunk_text()` and `search()` completely unchanged.** The search SQL uses `1 - (embedding <=> :embedding::vector)` which works correctly with normalized vectors.

## Todo List
- [ ] Replace imports in rag_service.py
- [ ] Update `__init__` to use genai.Client
- [ ] Add `_normalize()` static method
- [ ] Rewrite `embed()` with Gemini SDK + normalization
- [ ] Rewrite `embed_batch()` with Gemini SDK + normalization
- [ ] Verify `search()` needs no changes
- [ ] Verify `chunk_text()` needs no changes
- [ ] Run `uv run python -c "from app.services.rag_service import rag_service; print('OK')"` to verify import

## Success Criteria
- `rag_service.py` imports without error
- No `openai` or `AsyncOpenAI` references remain in file
- Every embedding returned is L2-normalized (unit vector)
- `search()` SQL and `chunk_text()` untouched

## Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| Gemini batch size limit hit on large documents | Medium | Add chunking if needed; Gemini limit is high (~100) |
| Normalization math error | High | Unit test: assert `abs(norm(result) - 1.0) < 1e-6` |
| `client.aio` not available in all SDK versions | Medium | Pin `google-genai>=1.0.0`; async supported since launch |

## Security Considerations
- API key never logged or exposed in responses
- Error messages should not leak key values

## Next Steps
- Phase 3 rewrites llm_service.py (chat completions)
