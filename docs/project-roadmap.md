# Project Roadmap - RAG Business Document Wiki

**Project:** RAG Business Document Wiki
**Version:** 0.1.0 → 1.0.0
**Last Updated:** 2026-03-27
**Total Duration:** Q2 2026 (4 months)

---

## Phase 0: Foundation (COMPLETED)

**Duration:** Week 1-2
**Status:** ✅ Completed

### Objectives
- Set up development environment
- Establish project structure
- Create basic authentication system

### Tasks Completed
- [x] Initialize Git repository
- [x] Set up Python 3.11 environment with Poetry
- [x] Set up Vue 3 + TypeScript environment
- [x] Configure Docker Compose for local development
- [x] Implement JWT authentication (register, login, refresh)
- [x] Create database models (User, Document, DocumentChunk)

### Deliverables
- `backend/pyproject.toml` - Python dependencies
- `frontend/package.json` - NPM dependencies
- `docker-compose.yml` - Development infrastructure
- Authentication endpoints working

---

## Phase 1: Document Management (IN PROGRESS)

**Duration:** Week 3-4
**Status:** 🔄 In Progress

### Objectives
- Implement document upload functionality
- Add document parsing for PDF/DOCX/XLSX
- Create document storage with MinIO
- Implement document deletion

### Tasks

**Week 3: Upload & Storage**
- [ ] Create POST /upload endpoint
- [ ] Implement file validation (size, type)
- [ ] Integrate MinIO for object storage
- [ ] Create Document record in database
- [ ] Implement Celery task for processing

**Week 4: Parsing & Persistence**
- [ ] Implement PDF parsing (PyPDF2 + pdfplumber)
- [ ] Implement DOCX parsing (python-docx)
- [ ] Implement XLSX parsing (openpyxl)
- [ ] Store extracted text and metadata
- [ ] Implement document deletion with cascade

### Deliverables
- `backend/app/api/v1/routes/documents.py`
- `backend/app/services/parsing.py`
- `backend/app/services/minio_service.py`
- Document upload working
- Document CRUD operations

### Success Criteria
- Users can upload files up to 50MB
- Files are stored in MinIO
- Extracted text is saved to database
- Processing status updates via WebSocket

---

## Phase 2: Semantic Search (PENDING)

**Duration:** Week 5-6
**Status:** ⏳ Pending

### Objectives
- Implement vector embeddings with OpenAI
- Create semantic search endpoint
- Display search results with relevance scores
- Add search filters

### Tasks

**Week 5: Embedding Pipeline**
- [ ] Implement embedding generation (OpenAI text-embedding-3-small)
- [ ] Chunk text (500 chars, 50 overlap)
- [ ] Store embeddings in pgvector column
- [ ] Create vector similarity search

**Week 6: Search Interface**
- [ ] Create POST /search/query endpoint
- [ ] Implement search result filtering
- [ ] Display relevance scores
- [ ] Highlight matching context
- [ ] Add search history

### Deliverables
- `backend/app/services/llm_service.py` (embeddings)
- `backend/app/services/rag_service.py` (search)
- `frontend/src/views/Search.vue`
- Semantic search working

### Success Criteria
- Search returns top 10 relevant chunks
- Relevance scores displayed (0-100%)
- Query response < 1 second
- Results show source document

---

## Phase 3: RAG Chat (PENDING)

**Duration:** Week 7-8
**Status:** ⏳ Pending

### Objectives
- Implement RAG chat endpoint
- Integrate LLM for response generation
- Display source citations
- Manage conversation context

### Tasks

**Week 7: Chat Implementation**
- [ ] Create POST /chat/message endpoint
- [ ] Build RAG prompt with retrieved context
- [ ] Call OpenAI chat API
- [ ] Format response with citations
- [ ] Implement conversation history

**Week 8: Chat Interface**
- [ ] Create Chat.vue view
- [ ] Display message bubbles
- [ ] Show source citations
- [ ] Add typing indicator
- [ ] Implement auto-scroll

### Deliverables
- `backend/app/api/v1/routes/chat.py`
- `backend/app/services/rag_service.py` (chat)
- `frontend/src/views/Chat.vue`
- Chat with RAG working

### Success Criteria
- Chat responses generated within 3 seconds
- Source citations displayed for each answer
- Conversation history maintained
- Context-aware responses

---

## Phase 4: Admin Dashboard (PENDING)

**Duration:** Week 9
**Status:** ⏳ Pending

### Objectives
- Create admin dashboard view
- Implement user management
- Add document statistics
- Role-based access control

### Tasks
- [ ] Create Admin.vue view
- [ ] Implement GET /admin/users endpoint
- [ ] Implement user CRUD operations
- [ ] Add document statistics
- [ ] Create activity feed
- [ ] Add role management UI

### Deliverables
- `backend/app/api/v1/routes/admin.py`
- `frontend/src/views/Admin.vue`
- Admin dashboard fully functional

### Success Criteria
- Admins can view all users
- Role management works
- Document stats displayed
- Activity feed shows recent activity

---

## Phase 5: Real-time Updates (PENDING)

**Duration:** Week 10
**Status:** ⏳ Pending

### Objectives
- Implement WebSocket for status updates
- Show processing progress
- Notify users of completion

### Tasks
- [ ] Create WebSocket connection endpoint
- [ ] Implement message broadcasting
- [ ] Update document status in real-time
- [ ] Display progress indicators
- [ ] Handle reconnection

### Deliverables
- `backend/app/api/v1/routes/websocket.py`
- `frontend/src/composables/use-web-socket.ts`
- Real-time status updates working

### Success Criteria
- Processing status updates in real-time
- Progress bar shows completion
- Success/error notifications displayed

---

## Phase 6: Testing & Documentation (PENDING)

**Duration:** Week 11
**Status:** ⏳ Pending

### Objectives
- Write comprehensive unit tests
- Write integration tests
- Create technical documentation
- Perform code review

### Tasks

**Backend Testing**
- [ ] Write unit tests for all services
- [ ] Write integration tests for API endpoints
- [ ] Test edge cases and error handling
- [ ] Achieve 60% code coverage

**Frontend Testing**
- [ ] Write unit tests for stores
- [ ] Write component tests
- [ ] Test async operations
- [ ] Test error handling

**Documentation**
- [ ] Create project overview (PDR)
- [ ] Create codebase summary
- [ ] Create code standards
- [ ] Create system architecture
- [ ] Create deployment guide
- [ ] Update README.md

**Code Review**
- [ ] Perform peer review
- [ ] Fix identified issues
- [ ] Refactor code if needed

### Deliverables
- Test suite with 60%+ coverage
- Complete documentation set
- Code review completed

### Success Criteria
- All tests passing
- Documentation complete and accurate
- Code quality improved
- No critical bugs

---

## Phase 7: MVP Release (PENDING)

**Duration:** Week 12
**Status:** ⏳ Pending

### Objectives
- Final testing and bug fixes
- Prepare for production deployment
- Create deployment guide
- Release MVP

### Tasks
- [ ] Final testing cycle
- [ ] Fix any remaining bugs
- [ ] Performance optimization
- [ ] Create production deployment guide
- [ ] Prepare Docker production images
- [ ] Final code review

### Deliverables
- Production-ready code
- Deployment guide
- Docker production images
- MVP release

### Success Criteria
- Zero critical bugs
- Performance within SLA
- Deployment guide complete
- Production-ready deployment

---

## Phase 8: Post-MVP Enhancements (Q2 2026)

**Duration:** Month 3-4
**Status:** ⏳ Future

### Objectives
- Add email verification
- Implement local embeddings
- Add OCR support
- Improve search and chat

### Tasks

**Email Verification**
- [ ] Implement email verification flow
- [ ] Send verification emails
- [ ] Add verification check to registration

**Local Embeddings**
- [ ] Integrate sentence-transformers
- [ ] Create embedding generation service
- [ ] Migrate from OpenAI to local embeddings

**OCR Support**
- [ ] Integrate PaddleOCR
- [ ] Add image scanning
- [ ] Extract text from scanned documents

**Search Improvements**
- [ ] Implement search filters (by date, user, status)
- [ ] Add search history
- [ ] Optimize vector index

**Chat Improvements**
- [ ] Implement chat context management
- [ ] Add chat export functionality
- [ ] Improve response formatting

### Deliverables
- Email verification working
- Local embeddings integrated
- OCR support added
- Enhanced search and chat features

---

## Milestones

### Milestone 1: Foundation (Week 2)
- ✅ Authentication system
- ✅ Database models
- ✅ Development environment

### Milestone 2: Document Upload (Week 4)
- ✅ Document upload working
- ✅ File storage (MinIO)
- ✅ Parsing implementation

### Milestone 3: Search & Chat (Week 8)
- ✅ Semantic search
- ✅ RAG chat
- ✅ Source citations

### Milestone 4: Admin Dashboard (Week 9)
- ✅ User management
- ✅ Document statistics
- ✅ Activity feed

### Milestone 5: MVP Release (Week 12)
- ✅ All core features working
- ✅ Testing completed
- ✅ Documentation complete
- ✅ Production-ready

### Milestone 6: Post-MVP (Month 4)
- ✅ Email verification
- ✅ Local embeddings
- ✅ OCR support

---

## Risk Management

### High Risk
**Risk:** OpenAI API cost increases significantly
- **Mitigation:** Use text-embedding-3-small (cheaper), implement caching
- **Contingency:** Switch to local embeddings

### Medium Risk
**Risk:** Document processing time exceeds SLA
- **Mitigation:** Optimize parsing, implement queue scaling
- **Contingency:** Increase chunk size to reduce processing time

### Low Risk
**Risk:** pgvector performance degrades with large datasets
- **Mitigation:** Use IVFFlat index, limit results to top 10 chunks
- **Contingency:** Migrate to dedicated vector DB (Qdrant)

---

## Metrics & KPIs

### Development Metrics
- **Velocity:** Average 2-3 tasks completed per week
- **Code Coverage:** Target 60% by Phase 6
- **Bug Count:** < 5 critical bugs by MVP

### Performance Metrics
- **Document Upload:** < 5 seconds (10MB file)
- **Search Query:** < 1 second
- **Chat Response:** < 3 seconds
- **Page Load:** < 2 seconds

### Feature Completeness
- **MVP Features:** 7 core features completed
- **Documentation:** 6 documents completed
- **Tests:** 60%+ coverage achieved

---

## Decision Log

### Week 1: Tech Stack Selection
- **Decision:** Use FastAPI + Vue 3 for better performance and DX
- **Rationale:** FastAPI's async support, Vue 3's Composition API

### Week 2: Database Choice
- **Decision:** PostgreSQL + pgvector instead of Qdrant
- **Rationale:** Simpler stack, PostgreSQL already needed for metadata

### Week 3: Embedding Model
- **Decision:** Use OpenAI text-embedding-3-small (MVP), migrate to local (Phase 2)
- **Rationale:** Fastest to implement, cheaper than GPT-4

### Week 4: Chunk Size
- **Decision:** 500 characters per chunk, 50 overlap
- **Rationale:** Balance between context and granularity

---

## Next Steps

### Immediate (Week 3)
- Focus on document upload implementation
- Set up Celery tasks for async processing
- Integrate MinIO for object storage

### Short-term (Week 4-5)
- Complete document parsing
- Implement embedding generation
- Start semantic search

### Long-term (Week 6-8)
- Complete RAG chat
- Build admin dashboard
- Implement WebSocket

### Production (Week 9-12)
- Testing and documentation
- Code review
- Deployment preparation

---

## Appendix: Resource Planning

### Team Size
- **Backend Developer:** 1 person (focused)
- **Frontend Developer:** 1 person (focused)
- **Tech Lead:** Part-time (review, decisions)
- **Total:** 2.5 FTE

### Time Allocation
- **Development:** 8 weeks (66%)
- **Testing:** 1 week (8%)
- **Documentation:** 1 week (8%)
- **Code Review:** 1 week (8%)
- **Planning:** 1 week (8%)

### Tools & Services
- **Development Tools:** Git, Docker, VS Code, Poetry, NPM
- **Infrastructure:** PostgreSQL, Redis, MinIO, OpenAI API
- **CI/CD:** GitHub Actions (planned for Phase 7)
- **Monitoring:** Prometheus + Grafana (planned for Phase 2)
