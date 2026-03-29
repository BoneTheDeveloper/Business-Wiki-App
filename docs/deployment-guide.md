# Deployment Guide - RAG Business Document Wiki

**Last Updated:** 2026-03-27
**Environment:** Development, Staging, Production

## Prerequisites

### System Requirements

**Development**
- Docker & Docker Compose (latest version)
- Poetry (Python 3.11+)
- Node.js 18+ and npm
- Git

**Staging/Production**
- Docker & Docker Compose
- PostgreSQL 15+ with pgvector extension
- Redis 7+
- MinIO (S3-compatible storage)
- Nginx (optional, recommended for production)
- 2GB RAM minimum (4GB recommended)

### Required Accounts
- OpenAI API account with credits
- (Optional) SendGrid account for email verification

---

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd RAG_Business_Wiki_App
```

### 2. Create Environment File

```bash
cp .env.example .env
```

### 3. Configure Environment Variables

Edit `.env` file:

```env
# Database
DB_USER=wiki
DB_PASSWORD=strong-password-here
DB_NAME=wiki_db

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=strong-password-here

# JWT
JWT_SECRET_KEY=generate-random-32-char-string
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Frontend (optional, for production)
VITE_API_URL=https://your-api-domain.com/api/v1
```

### 4. Generate Secure Secrets

```bash
# Generate JWT secret (32 characters)
openssl rand -hex 32

# Generate MinIO secrets
openssl rand -hex 32
```

---

## Development Deployment

### Using Docker Compose

#### Start All Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL (pgvector)
- Redis
- MinIO
- Backend API (FastAPI)
- Frontend (Vite dev server)
- Celery Worker

#### Check Service Status

```bash
docker-compose ps
```

Expected output:
```
NAME                STATUS
backend             Up
celery_worker       Up
frontend            Up
minio               Up
postgres            Up (healthy)
redis               Up
```

#### View Logs

```bash
# Backend logs
docker-compose logs -f backend

# Frontend logs
docker-compose logs -f frontend

# Celery worker logs
docker-compose logs -f celery_worker
```

#### Stop Services

```bash
docker-compose down
```

#### Stop and Remove Volumes

```bash
docker-compose down -v
```

### Local Development (Without Docker)

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
poetry install

# Run development server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

---

## Production Deployment

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Production Deployment                      │
├─────────────────────────────────────────────────────────────┤
│  Load Balancer (Nginx)                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Backend 1  │  │  Backend 2  │  │  Backend 3  │       │
│  │ (FastAPI)    │  │ (FastAPI)    │  │ (FastAPI)    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│           │           │           │                          │
│  ┌────────▼───────────▼───────────▼──────────┐               │
│  │  PostgreSQL (primary + replicas)           │               │
│  └─────────────────────────────────────────────┘               │
│  ┌─────────────────────────────────────────────┐               │
│  │  Redis (cluster)                            │               │
│  └─────────────────────────────────────────────┘               │
│  ┌─────────────────────────────────────────────┐               │
│  │  MinIO (object storage)                     │               │
│  └─────────────────────────────────────────────┘               │
│  ┌─────────────────────────────────────────────┐               │
│  │  Celery Workers (multiple instances)        │               │
│  └─────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Docker Compose Production Setup

Create `docker-compose.prod.yml`:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
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
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
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
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    volumes:
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    depends_on:
      - backend
    restart: unless-stopped

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: poetry run celery -A app.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    volumes:
      - ./backend:/app
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 2  # Run 2 worker instances
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### Start Production Services

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Build Frontend for Production

```bash
cd frontend
npm run build
```

The built assets will be in `frontend/dist/`.

### Update Docker Images

```bash
# Rebuild backend
docker-compose -f docker-compose.prod.yml build backend

# Rebuild frontend
docker-compose -f docker-compose.prod.yml build frontend

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

---

## Nginx Configuration (Recommended)

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:80;
    }

    server {
        listen 80;
        server_name your-domain.com;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }

        # Backend API
        location /api/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $host;
            proxy_set_header Connection '';
            proxy_read_timeout 300s;
        }

        # WebSocket
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400s;
        }

        # Health check
        location /health {
            proxy_pass http://backend;
            access_log off;
        }
    }
}
```

---

## Monitoring & Logging

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy","service":"backend"}
```

### Database Health Check

```bash
docker exec -it rag-wiki-app-postgres-1 psql -U wiki -d wiki_db -c "SELECT 1"
```

---

## Backup & Recovery

### Database Backups

Create backup script `scripts/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/wiki_db_$DATE.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker exec rag-wiki-app-postgres-1 pg_dump -U wiki wiki_db > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Keep only last 7 days
find $BACKUP_DIR -name "wiki_db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

Run backup daily:
```bash
0 2 * * * /path/to/scripts/backup.sh
```

### Restore Database

```bash
# Restore from backup
gunzip < /backups/wiki_db_20260327_020000.sql.gz | docker exec -i rag-wiki-app-postgres-1 psql -U wiki wiki_db
```

### MinIO Backups

```bash
# Backup MinIO data
docker exec rag-wiki-app-minio-1 mc mirror /data /backups/minio
```

---

## Security Best Practices

### Environment Variables

1. **Never commit `.env` file** to version control
2. **Use strong secrets** (at least 32 characters)
3. **Rotate secrets** periodically
4. **Use different secrets** for development and production

### Database Security

1. Use strong passwords
2. Enable SSL connections
3. Restrict network access (bind to localhost only)
4. Regular backups
5. Monitor database queries

### API Security

1. Enable HTTPS (nginx)
2. Implement rate limiting (Phase 2)
3. Use secure cookies
4. Implement CORS properly
5. Validate all inputs

### File Upload Security

1. Validate file types
2. Restrict file sizes
3. Sanitize filenames
4. Store files outside web root
5. Implement virus scanning (Phase 2)

---

## Troubleshooting

### Backend Won't Start

**Problem:** Backend container fails to start
**Solution:**
```bash
# Check logs
docker-compose logs backend

# Verify database connection
docker-compose exec backend python -c "from app.config import settings; print(settings.database_url)"

# Restart services
docker-compose restart backend
```

### Frontend Won't Start

**Problem:** Frontend shows connection errors
**Solution:**
```bash
# Check frontend logs
docker-compose logs frontend

# Verify backend is running
docker-compose ps backend

# Check API URL in .env
echo $VITE_API_URL
```

### Document Processing Fails

**Problem:** Celery worker shows errors
**Solution:**
```bash
# Check celery logs
docker-compose logs celery_worker

# Verify OpenAI API key
echo $OPENAI_API_KEY

# Check file permissions
docker-compose exec backend ls -la /app/uploads
```

### High Memory Usage

**Problem:** Services using too much memory
**Solution:**
```bash
# Check resource usage
docker stats

# Adjust resource limits in docker-compose.prod.yml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

---

## Performance Optimization

### Database Optimization

```sql
-- Reindex vector index
REINDEX INDEX idx_chunks_embedding;

-- Analyze table for query optimization
ANALYZE document_chunks;

-- Vacuum to reclaim space
VACUUM document_chunks;
```

### Redis Optimization

```bash
# Clear old keys
redis-cli --scan --pattern "temp:*" | xargs redis-cli DEL

# Check memory usage
redis-cli INFO memory
```

### Celery Worker Optimization

```bash
# Adjust worker concurrency
celery -A app.celery_app worker --loglevel=info --concurrency=4
```

---

## Update & Upgrade

### Backend Update

```bash
# Pull latest code
git pull origin main

# Rebuild backend
docker-compose build backend
docker-compose up -d backend

# Restart celery workers
docker-compose up -d celery_worker
```

### Frontend Update

```bash
cd frontend
git pull origin main
npm install
npm run build
docker-compose build frontend
docker-compose up -d frontend
```

---

## Support & Resources

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vue.js Documentation](https://vuejs.org/)
- [Docker Documentation](https://docs.docker.com/)

### Health Checks
- **Backend Health:** `http://your-domain.com/health`
- **API Docs:** `http://your-domain.com/api/docs`
- **MinIO Console:** `http://your-domain.com:9001`
- **Frontend:** `http://your-domain.com`

### Common Issues

**Issue:** Connection refused
- Check if services are running: `docker-compose ps`
- Check service logs: `docker-compose logs <service>`

**Issue:** Documents not processing
- Check Celery worker status: `docker-compose ps celery_worker`
- Check worker logs: `docker-compose logs celery_worker`

**Issue:** Search not working
- Verify embeddings are generated: Check document status
- Verify pgvector extension is installed
- Check vector index: `SELECT * FROM pg_indexes WHERE indexname = 'idx_chunks_embedding'`
