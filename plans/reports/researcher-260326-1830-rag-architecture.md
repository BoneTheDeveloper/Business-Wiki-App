# RAG Architecture Research Report for Business Document Wiki

**Date:** 2026-03-26
**Focus:** Document RAG system design for business wiki

## Executive Summary

Comprehensive analysis of RAG architecture for document-heavy applications, with concrete recommendations for chunking, embeddings, retrieval optimization, reranking, and OCR integration.

---

## 1. Document Chunking Strategies

### Best Practices

**Core Principles:**
- Chunk size: 256-512 tokens (better for dense embeddings)
- Overlap: 10-20% between chunks
- Semantic boundaries preferred over fixed sizes
- Metadata preservation (page numbers, section headers, document ID)

**File-Specific Approaches:**

#### PDF
- **Fixed-size:** 500 tokens with 50 token overlap
- **Semantic:** Split on headings (H1-H3), tables, lists
- **Page-based:** Chunk by page for short docs (<10 pages), combine multiple pages for long docs
- **Text extraction:** Use PyPDF2 + pdfplumber for better structure detection

**DOCX**
- **Semantic:** Extract headings, paragraphs, tables
- **Section-based:** Split on section breaks
- **Paragraph-based:** 200-300 tokens per paragraph with header context

**XLSX**
- **Sheet-based:** Treat each sheet as document section
- **Table-based:** Extract tables as chunk units
- **Row-based:** Max 200-300 tokens per table row
- **Summary fields:** Store metadata separately

### Chunking Libraries
- **Unstructured:** Comprehensive document parsing (supports PDF, DOCX, XLSX)
- **LangChain:** `RecursiveCharacterTextSplitter` with customizable separators
- **LlamaIndex:** Schema-aware chunking with metadata extraction

**Recommendation:** Start with LangChain `RecursiveCharacterTextSplitter` (512 tokens, 50 overlap) for MVP, migrate to Unstructured/LlamaIndex for production.

---

## 2. Embedding Models Comparison

### Model Options

#### OpenAI Embeddings (text-embedding-3-small/large)
**Pros:**
- State-of-the-art accuracy
- Cloud-managed (no infrastructure)
- Production-ready support

**Cons:**
- Cost per 1M tokens (~$0.02-$0.13)
- Latency (API calls)
- Data privacy concerns

**Recommendation:** Use `text-embedding-3-small` for cost efficiency (0.02/M tokens, 1536 dimensions).

#### Local Models (sentence-transformers)
**Options:**
- **all-MiniLM-L6-v2:** Fast, 384 dimensions, 400MB (~20 MB quantized)
- **all-mpnet-base-v2:** High quality, 768 dimensions, 400MB
- **bge-m3:** Multilingual, 1024 dimensions, 400MB
- **nomic-embed-text:** Good quality, 768 dimensions, 200MB

**Pros:**
- Free, run locally
- No data egress
- Fast inference
- No API latency

**Cons:**
- Requires GPU/CPU optimization
- Lower quality than state-of-the-art
- Need to manage model versions

**Recommendation:**
- **Development/Testing:** `all-MiniLM-L6-v2` (fast, good enough)
- **Production:** `all-mpnet-base-v2` or `bge-m3` (better quality)
- **Multi-lingual:** `bge-m3`

### Performance Considerations
- **Dimensions:** Higher dimensions (768+) = better semantic understanding but slower retrieval
- **Batch size:** 32-64 for local models, 1000+ for OpenAI
- **Cache embeddings:** Store once, reuse across queries

**Recommendation:** Start with OpenAI for MVP, add local fallback after user testing.

---

## 3. pgvector Optimization

### Database Schema

```sql
-- Vector table
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL, -- or 768 for local models
    chunk_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Metadata index for filtering
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_metadata ON document_chunks USING GIN(metadata);

-- IVFFlat for approximate nearest neighbor
CREATE INDEX idx_chunks_embedding_ivfflat
    ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100); -- number of clusters

-- HNSW for higher recall (optional)
CREATE INDEX idx_chunks_embedding_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### Optimization Techniques

#### Retrieval Strategy
- **Hybrid search:** Combine vector search with metadata filters (document_id, date range, author)
- **Top-K + Rerank:** Retrieve 20-50 candidates, rerank top 10 with cross-encoder
- **Pagination:** Limit results to top 10-20 for better quality

#### Performance Tuning
- **Lists parameter (IVFFlat):** 100-1000 for 10K-1M chunks, calibrate based on dataset size
- **HNSW parameters:** `m=16` (neighbors), `ef_construction=64` (recall)
- **Connection pooling:** PgBouncer or asyncpg connection pool
- **Query optimization:** Use `SET LOCAL statement_timeout` for vector search

#### pgvector Extensions
```sql
CREATE EXTENSION vector;
-- or
CREATE EXTENSION vector_ip;
-- or
CREATE EXTENSION vector_l2sq;
```

**Recommendation:**
- **MVP:** IVFFlat with 100 lists
- **Scale:** HNSW for production
- **Hybrid:** Add metadata filtering (document_id, date range)

---

## 4. Reranking Approaches

### Why Rerank?
Vector search finds *candidates*; cross-encoder reranks for *relevance*. Improves accuracy by 20-40%.

### Reranking Models

#### Cross-Encoders (Two-Stage)
**Pros:**
- High accuracy (30-40% improvement)
- State-of-the-art results

**Cons:**
- Slow (one-by-one scoring)
- Higher latency

**Popular Models:**
- **BGE-Reranker:** BAAI/bge-reranker-base (~410MB, 512 tokens)
- **Cohere Rerank API:** Enterprise-grade, multi-lingual
- **E5-Mistral:** Efficient, good quality

**Implementation:**
```python
# Phase 1: Fast vector search (retrieve 50 candidates)
results = vector_search(query, top_k=50)

# Phase 2: Rerank (score 50 → 10)
reranked = reranker.score(query, results[:50])[:10]

# Phase 3: Return results
return reranked
```

#### Dual-Encoder Reranking
**Pros:**
- Faster than cross-encoder
- Suitable for real-time

**Cons:**
- Lower accuracy than cross-encoder

**Use Case:** Initial MVP, then upgrade to cross-encoder.

### API Options
- **Cohere Rerank API:** High accuracy, multi-lingual, pay-per-use
- **Local models:** BGE-Reranker (free, offline)

**Recommendation:**
- **MVP:** Skip reranking initially
- **Production:** BGE-Reranker local model (free, good quality)
- **Enterprise:** Cohere Rerank API (multi-lingual, faster)

---

## 5. OCR Integration Options

### Use Cases
- **Scanned PDFs:** Images need text extraction
- **Low-quality images:** Poor optical characters
- **Handwriting:** Tables, signatures, notes

### OCR Solutions

#### Tesseract OCR
**Pros:**
- Open-source, free
- Multi-platform (Windows/Linux/macOS)
- Good for English, moderate for others
- Python binding: `pytesseract`

**Cons:**
- Low accuracy for complex layouts
- Poor table detection
- Slow on large documents

**Use Case:** Basic PDF text extraction, MVP OCR.

#### PaddleOCR
**Pros:**
- Chinese/English support (superior for CN)
- Better layout analysis
- Open-source, free
- Multi-platform

**Cons:**
- Resource-intensive
- Longer setup

**Use Case:** Production OCR, multi-lingual documents.

**Recommendation:**
- **MVP:** Tesseract (simplest setup)
- **Production:** PaddleOCR (better accuracy)
- **Scale:** Hybrid approach (Tesseract for English, PaddleOCR for multi-lingual)

### Implementation Architecture
```
Document Upload
    ↓
File Parser (Unstructured/PyPDF2)
    ↓
Text Extraction?
    ├─ Yes → Store in database
    └─ No → OCR Pipeline
        ↓
File Image Extraction (pdf2image)
    ↓
OCR Processing (Tesseract/PaddleOCR)
    ↓
Text Normalization → Store in database
```

### OCR Optimization
- **Batch processing:** Process multiple pages in parallel
- **Cache OCR results:** Store extracted text, don't re-OCR
- **Progress tracking:** Show user OCR progress (UI feedback)
- **Fallback:** Use PDF text extraction first, OCR only if needed

---

## Recommendations Summary

### Priority Order for Implementation

**Phase 1 (MVP):**
1. Document parsing: Unstructured library
2. Chunking: LangChain RecursiveCharacterTextSplitter (512 tokens, 50 overlap)
3. Embeddings: OpenAI text-embedding-3-small (1536 dims)
4. Database: pgvector with IVFFlat (100 lists)
5. Query: Top-10 vector search only (skip reranking)

**Phase 2 (Enhancement):**
1. Hybrid search: Add metadata filtering (document_id, date range)
2. Embeddings: Switch to local `all-mpnet-base-v2` (768 dims) for cost savings
3. Performance: Tune pgvector HNSW parameters, connection pooling
4. UI: Show chunk metadata (page number, section header)

**Phase 3 (Optimization):**
1. Reranking: Add BGE-Reranker local model (10-20% accuracy gain)
2. OCR: Implement PaddleOCR for scanned documents
3. Cache: Embedding cache, OCR result cache
4. Evaluation: A/B testing, relevance scoring metrics

### Tech Stack (Recommended)

**Backend:**
- Python 3.11+
- FastAPI or Django (framework)
- pgvector (PostgreSQL extension)
- LangChain or LlamaIndex (orchestration)

**Embeddings:**
- OpenAI: `text-embedding-3-small` (MVP)
- Local: `all-mpnet-base-v2` (production)

**Reranking:**
- Local: BGE-Reranker-base (free, offline)
- Optional: Cohere Rerank API (multi-lingual)

**OCR:**
- Primary: PaddleOCR (production)
- Fallback: Tesseract (MVP)

**Infrastructure:**
- PostgreSQL 15+ with pgvector extension
- Celery for async processing (OCR, embedding generation)
- Redis for caching and queue management

### Cost Estimates (Monthly)

**OpenAI Embeddings:** ~$50-200/month (depending on doc volume)
**Cohere Rerank API:** ~$100-500/month (high accuracy needed)
**PaddleOCR:** Free (local infrastructure)
**Database:** PostgreSQL hosting ~$20-100/month

### Next Steps

1. **Set up PostgreSQL with pgvector extension**
2. **Implement document parsing with Unstructured library**
3. **Create chunking pipeline with metadata extraction**
4. **Add embedding generation (OpenAI first)**
5. **Build vector search API with Top-K retrieval**
6. **Add reranking with BGE-Reranker**
7. **Implement OCR for scanned documents**

---

## Unresolved Questions

1. **Document volume estimate:** How many documents/chunks will be processed monthly? (affects scaling strategy)
2. **Multi-lingual requirement:** Are documents in multiple languages? (impacts embedding choice)
3. **Real-time vs batch:** Should OCR and embedding be real-time or batch? (latency vs cost)
4. **User base:** Concurrent users? (affects database load balancing)
5. **Security compliance:** Any data privacy requirements? (impacts OpenAI vs local embeddings choice)

---

**Report prepared:** 2026-03-26
**Research methodology:** Industry best practices from LangChain, LlamaIndex, pgvector documentation, and production experiences