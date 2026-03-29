# RAG Business Document Wiki

A RAG-powered document wiki application with Vue.js frontend and FastAPI backend.

## Features

- Document upload (PDF, DOCX, XLSX)
- Semantic search across documents
- Chat with your documents using RAG
- User authentication with JWT
- Role-based access control
- Real-time processing status

## Tech Stack

- **Frontend:** Vue.js 3, TypeScript, PrimeVue, Tailwind CSS
- **Backend:** FastAPI, Poetry, SQLAlchemy
- **Database:** PostgreSQL + pgvector
- **Cache/Queue:** Redis, Celery
- **Storage:** MinIO
- **AI:** OpenAI (embeddings + chat)

## Prerequisites

- Docker & Docker Compose
- OpenAI API key

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd RAG_Business_Wiki_App
```

### 2. Create Environment File

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Access the Application

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/api/docs
- **MinIO Console:** http://localhost:9001

## Configuration

### Environment Variables

```env
# Database
DB_USER=wiki
DB_PASSWORD=wiki_secret
DB_NAME=wiki_db

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

## Development

### Backend (Docker)

```bash
# Start backend in development mode
docker-compose up -d backend

# View logs
docker-compose logs -f backend

# Stop backend
docker-compose stop backend
```

### Backend (Local)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
poetry install

# Run development server
poetry run uvicorn app.main:app --reload
```

### Frontend (Docker)

```bash
# Start frontend in development mode
docker-compose up -d frontend

# View logs
docker-compose logs -f frontend

# Stop frontend
docker-compose stop frontend
```

### Frontend (Local)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration

### Documents
- `GET /api/v1/documents` - List user documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete document
- `GET /api/v1/documents/{id}/status` - Check processing status

### Search
- `POST /api/v1/search/query` - Semantic search

### Chat
- `POST /api/v1/chat/message` - RAG chat

### Admin (admin only)
- `GET /api/v1/admin/users` - List all users
- `GET /api/v1/admin/stats` - Get stats

### WebSocket
- `WS /ws/documents` - Document status updates

## Project Structure

```
RAG_Business_Wiki_App/
├── frontend/          # Vue.js 3 frontend
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/
│   │   ├── api/
│   │   └── composables/
│   ├── package.json
│   └── Dockerfile.dev
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── models/
│   │   └── services/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── docs/              # Documentation
├── docker-compose.yml
└── .env.example
```

## Documentation

- [Project Overview & Requirements](docs/project-overview-pdr.md)
- [Codebase Summary](docs/codebase-summary.md)
- [Code Standards](docs/code-standards.md)
- [System Architecture](docs/system-architecture.md)
- [Project Roadmap](docs/project-roadmap.md)
- [Deployment Guide](docs/deployment-guide.md)

## Development Workflow

1. **Planning:** Create implementation plans in `./plans/`
2. **Research:** Conduct parallel research using researcher agents
3. **Implementation:** Follow plan in `./plans/`
4. **Testing:** Run tests after implementation
5. **Review:** Perform code review
6. **Integration:** Update documentation as needed
7. **Deployment:** Follow deployment guide

## License

MIT
