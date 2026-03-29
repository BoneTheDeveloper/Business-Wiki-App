# Phase 01 - Project Setup

**Priority:** P0 | **Duration:** 1 day | **Status:** Pending

## Overview

Initialize project structure, Docker environment, and development tooling for both frontend and backend.

## Key Insights

- Monorepo structure: `frontend/` and `backend/` directories
- Docker Compose for local development (all services)
- Environment-based configuration
- Hot-reload for both Vue and FastAPI

## Architecture

```
D:\Project\Bussiness_Wiki_App\
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── composables/
│   │   ├── stores/
│   │   ├── views/
│   │   ├── router/
│   │   ├── api/
│   │   ├── utils/
│   │   └── main.ts
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── auth/
│   │   ├── api/v1/routes/
│   │   ├── services/
│   │   ├── models/
│   │   └── utils/
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Requirements

### Functional
- Project scaffolding complete
- Docker services start correctly
- Health check endpoints work
- Dev servers hot-reload

### Non-Functional
- Startup time < 30 seconds
- Clear error messages
- Documented setup process

## Implementation Steps

### 1. Root Project Files

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_USER: ${DB_USER:-wiki}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-wiki_secret}
      POSTGRES_DB: ${DB_NAME:-wiki_db}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-wiki}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-minioadmin}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://${DB_USER:-wiki}:${DB_PASSWORD:-wiki_secret}@postgres:5432/${DB_NAME:-wiki_db}
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
    volumes:
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://${DB_USER:-wiki}:${DB_PASSWORD:-wiki_secret}@postgres:5432/${DB_NAME:-wiki_db}
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./backend:/app
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### 2. Backend Setup

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="RAG Business Wiki API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "backend"}
```

```python
# backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://wiki:wiki_secret@localhost:5432/wiki_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "documents"
    MINIO_SECURE: bool = False

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # OpenAI
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```

```
# backend/requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
asyncpg==0.29.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
aiofiles==23.2.1
redis==5.0.1
celery==5.3.6
minio==7.2.3
openai==1.10.0
langchain==0.1.0
langchain-openai==0.0.2
pypdf2==3.0.1
pdfplumber==0.10.3
python-docx==1.1.0
openpyxl==3.1.2
pgvector==0.2.4
```

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 3. Frontend Setup

```json
// frontend/package.json
{
  "name": "rag-wiki-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext .vue,.ts"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.5",
    "pinia": "^2.1.7",
    "primevue": "^3.49.0",
    "primeicons": "^6.0.1",
    "axios": "^1.6.5",
    "@vueuse/core": "^10.7.2"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.3",
    "typescript": "^5.3.3",
    "vite": "^5.0.11",
    "vue-tsc": "^1.8.27",
    "tailwindcss": "^3.4.1",
    "postcss": "^8.4.33",
    "autoprefixer": "^10.4.17"
  }
}
```

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

```javascript
// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        }
      }
    },
  },
  plugins: [],
}
```

```dockerfile
# frontend/Dockerfile.dev
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev", "--", "--host"]
```

### 4. Environment Files

```env
# .env.example
# Database
DB_USER=wiki
DB_PASSWORD=wiki_secret
DB_NAME=wiki_db

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

## Todo List

- [ ] Create root directory structure
- [ ] Create docker-compose.yml
- [ ] Create backend/Dockerfile
- [ ] Create backend/requirements.txt
- [ ] Create backend/app/main.py (minimal)
- [ ] Create backend/app/config.py
- [ ] Create frontend/Dockerfile.dev
- [ ] Create frontend/package.json
- [ ] Create frontend/vite.config.ts
- [ ] Create frontend/tailwind.config.js
- [ ] Create frontend/src/main.ts
- [ ] Create .env.example
- [ ] Create README.md with setup instructions
- [ ] Test: `docker-compose up` starts all services
- [ ] Test: Backend health check returns 200
- [ ] Test: Frontend loads at localhost:5173

## Success Criteria

1. `docker-compose up` starts all 6 services without errors
2. Backend health check at `http://localhost:8000/health` returns `{"status": "healthy"}`
3. Frontend loads at `http://localhost:5173` with Vue logo
4. Hot-reload works for both frontend and backend
5. PostgreSQL has pgvector extension available

## Next Steps

- Phase 02: Database schema, migrations, JWT authentication
