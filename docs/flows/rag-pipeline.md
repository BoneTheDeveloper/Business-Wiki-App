# RAG Pipeline Flow

> Source: [system-architecture.md](../system-architecture.md) - RAG Pipeline

```mermaid
flowchart LR
    subgraph INPUT["1. INPUT"]
        A[Uploaded Document]
    end

    subgraph PARSE["2. PARSING"]
        B{File Format?}
        B -->|PDF| C1[PyPDF2 + pdfplumber]
        B -->|DOCX| C2[python-docx]
        B -->|XLSX| C3[openpyxl]
        C1 --> D[Extracted Text]
        C2 --> D
        C3 --> D
    end

    subgraph CHUNK["3. CHUNKING"]
        E["RecursiveCharacterTextSplitter<br/>chunk_size=500<br/>chunk_overlap=50"]
    end

    subgraph EMBED["4. EMBEDDING"]
        F["Google Gemini gemini-embedding-001<br/>1536 dimensions"]
    end

    subgraph STORE["5. STORAGE"]
        G["PostgreSQL + pgvector<br/>document_chunks table"]
    end

    subgraph QUERY["6. QUERY"]
        H[User Query]
        I[Generate Query Embedding]
        J["Cosine Similarity Search<br/>Top 10 chunks"]
    end

    subgraph GENERATE["7. GENERATION"]
        K[Build RAG Prompt]
        L["Google Gemini 2.0 Flash<br/>Chat Completion"]
        M[Response + Citations]
    end

    A --> B
    D --> E
    E --> F
    F --> G

    H --> I --> J
    J --> K --> L --> M

    G -.->|vector search| J
```

## Pipeline Parameters

| Stage | Parameter | Value |
|-------|-----------|-------|
| Parsing | Supported formats | PDF, DOCX, XLSX |
| Chunking | Chunk size | 500 characters |
| Chunking | Chunk overlap | 50 characters |
| Chunking | Max chunks per doc | 1000 |
| Embedding | Model | gemini-embedding-001 |
| Embedding | Dimensions | 1536 |
| Search | Similarity metric | Cosine similarity |
| Search | Top-K results | 10 chunks |
| Generation | LLM model | gemini-2.0-flash |
| Generation | Max context messages | 5 (conversation history) |
