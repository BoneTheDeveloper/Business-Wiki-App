# Project Roadmap Timeline

> Source: [project-roadmap.md](../project-roadmap.md)

```mermaid
gantt
    title RAG Business Document Wiki - Development Roadmap
    dateFormat YYYY-MM-DD
    axisFormat %b %d

    section Phase 0 - Foundation
    Init Git repo               :done, p0a, 2026-03-17, 1d
    Setup Python + Poetry       :done, p0b, 2026-03-17, 1d
    Setup Vue 3 + TypeScript    :done, p0c, 2026-03-18, 1d
    Docker Compose config       :done, p0d, 2026-03-18, 1d
    JWT auth implementation     :done, p0e, 2026-03-19, 3d
    Database models             :done, p0f, 2026-03-19, 2d

    section Phase 1 - Document Mgmt
    Upload endpoint             :active, p1a, 2026-03-31, 3d
    MinIO integration           :active, p1b, 2026-03-31, 2d
    File validation             :active, p1c, 2026-04-02, 2d
    Celery task processing      :p1d, 2026-04-02, 2d
    PDF/DOCX/XLSX parsing       :p1e, 2026-04-07, 3d
    Document deletion           :p1f, 2026-04-09, 2d

    section Phase 2 - Semantic Search
    Embedding generation        :p2a, 2026-04-14, 3d
    Text chunking (500/50)      :p2b, 2026-04-14, 2d
    pgvector similarity search  :p2c, 2026-04-16, 2d
    Search endpoint             :p2d, 2026-04-16, 2d
    Search UI + results         :p2e, 2026-04-18, 3d

    section Phase 3 - RAG Chat
    Chat endpoint               :p3a, 2026-04-28, 3d
    RAG prompt builder          :p3b, 2026-04-28, 2d
    OpenAI chat integration     :p3c, 2026-04-30, 2d
    Chat UI + citations         :p3d, 2026-05-02, 3d

    section Phase 4 - Admin
    Admin dashboard             :p4a, 2026-05-05, 3d
    User management             :p4b, 2026-05-05, 2d
    Document statistics         :p4c, 2026-05-07, 2d

    section Phase 5 - Real-time
    WebSocket connection        :p5a, 2026-05-12, 2d
    Status broadcasting         :p5b, 2026-05-14, 2d
    Reconnection handling       :p5c, 2026-05-14, 1d

    section Phase 6 - Testing
    Backend unit tests          :p6a, 2026-05-19, 2d
    Integration tests           :p6b, 2026-05-21, 2d
    Documentation               :p6c, 2026-05-21, 1d

    section Phase 7 - Release
    Final testing               :p7a, 2026-05-26, 2d
    Bug fixes                   :p7b, 2026-05-28, 2d
    Production deployment       :p7c, 2026-05-28, 1d
```

## Milestones

```mermaid
graph LR
    M1["M1: Foundation<br/>Week 2<br/>✅ Complete"]
    M2["M2: Document Upload<br/>Week 4<br/>🔄 In Progress"]
    M3["M3: Search & Chat<br/>Week 8"]
    M4["M4: Admin Dashboard<br/>Week 9"]
    M5["M5: MVP Release<br/>Week 12"]
    M6["M6: Post-MVP<br/>Month 4"]

    M1 --> M2 --> M3 --> M4 --> M5 --> M6

    style M1 fill:#dcfce7,stroke:#16a34a
    style M2 fill:#fef3c7,stroke:#d97706
    style M3 fill:#e2e8f0,stroke:#64748b
    style M4 fill:#e2e8f0,stroke:#64748b
    style M5 fill:#e2e8f0,stroke:#64748b
    style M6 fill:#e2e8f0,stroke:#64748b
```

## Phase Details

| Phase | Duration | Status | Key Deliverable |
|-------|----------|--------|-----------------|
| 0 - Foundation | Week 1-2 | Complete | Auth + DB models + Docker |
| 1 - Document Mgmt | Week 3-4 | In Progress | Upload + Parse + MinIO |
| 2 - Semantic Search | Week 5-6 | Pending | Embeddings + Vector search |
| 3 - RAG Chat | Week 7-8 | Pending | Chat + Citations |
| 4 - Admin Dashboard | Week 9 | Pending | User mgmt + Stats |
| 5 - Real-time Updates | Week 10 | Pending | WebSocket + Status |
| 6 - Testing & Docs | Week 11 | Pending | 60% coverage + Docs |
| 7 - MVP Release | Week 12 | Pending | Production deployment |
