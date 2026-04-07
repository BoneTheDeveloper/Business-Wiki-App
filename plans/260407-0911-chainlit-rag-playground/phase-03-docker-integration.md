# Phase 3: Docker Config + Integration Testing

**PRIORITY:** High
**STATUS:** ⏳ Pending
**EFFORT:** 0.5 day

## Context Links

- Docker Compose: `docker/docker-compose.yml`
- Backend Dockerfile: `backend/Dockerfile` (reference for patterns)
- System architecture: `docs/architecture/system-architecture.md`
- Deployment: `docs/architecture/deployment.md`

## Overview

Containerize the Chainlit app and integrate into the existing Docker Compose stack. Verify end-to-end RAG playground flow.

## Requirements

### Functional
- Chainlit runs in its own Docker container
- Connects to backend via Docker service name (`backend:8000`)
- Accessible at `localhost:8001`
- Hot-reload for development (volume mount)

### Non-Functional
- Same Docker network as existing services
- Minimal image size (Python 3.11 slim)
- Fast rebuild on code changes

## Architecture

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .
COPY . .
EXPOSE 8000
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Addition
```yaml
chainlit:
  build:
    context: ../chainlit
    dockerfile: Dockerfile
  ports:
    - "${CHAINLIT_PORT:-8001}:8000"
  environment:
    BACKEND_URL: http://backend:8000
  volumes:
    - ../chainlit:/app
  depends_on:
    - backend
```

## Related Code Files

### Files to Create
- `chainlit/Dockerfile`
- `chainlit/.dockerignore`

### Files to Modify
- `docker/docker-compose.yml` — Add chainlit service

## Implementation Steps

1. Create `chainlit/Dockerfile` based on Python 3.11-slim
2. Create `chainlit/.dockerignore` (exclude .venv, __pycache__, .env)
3. Add chainlit service to `docker/docker-compose.yml`
4. Add `CHAINLIT_PORT` to `.env.example` files
5. Test: `docker-compose up -d chainlit`
6. Verify `localhost:8001` loads Chainlit UI
7. Send test query → verify RAG steps render
8. Verify chunks display with scores
9. Verify latency metrics appear

## Success Criteria
- `docker-compose up chainlit` starts without errors
- `localhost:8001` shows Chainlit chat UI
- Query reaches backend playground endpoint
- Full RAG pipeline renders end-to-end through Chainlit
- Latency metrics visible per step

## Risk Assessment
| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Chainlit WebSocket issues in Docker | Low | Expose correct port, use host 0.0.0.0 |
| Backend not reachable | Medium | Use Docker service name, same network |
| Volume mount permissions (Windows) | Medium | Use named volume for venv |

## Next Steps
- Full integration test: upload doc → wait for processing → query in playground
