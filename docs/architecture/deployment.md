# Deployment Architecture

> Source: [deployment-guide.md](../deployment-guide.md), [system-architecture.md](../system-architecture.md)

## Development Environment

```mermaid
graph TB
    subgraph DOCKER["Docker Compose (Development)"]
        subgraph SERVICES
            PG_DEV["postgres<br/>pgvector/pgvector:pg15<br/>:5432"]
            REDIS_DEV["redis<br/>redis:7.2-alpine<br/>:6379"]
            MINIO_DEV["minio<br/>minio/minio:latest<br/>:9000 / :9001"]
            BE_DEV["backend<br/>FastAPI (uvicorn)<br/>:8000"]
            FE_DEV["frontend<br/>Vite dev server<br/>:5173"]
            CW_DEV["celery_worker<br/>Celery worker"]
            CL_DEV["chainlit<br/>RAG Playground<br/>:8001<br/>docker profile: playground"]
        end
    end

    subgraph VOLUMES
        VOL_PG["postgres_data"]
        VOL_REDIS["redis_data"]
        VOL_MINIO["minio_data"]
    end

    BE_DEV --> PG_DEV
    BE_DEV --> REDIS_DEV
    BE_DEV --> MINIO_DEV
    CW_DEV --> PG_DEV
    CW_DEV --> REDIS_DEV
    CW_DEV --> MINIO_DEV
    FE_DEV --> BE_DEV
    CL_DEV --> BE_DEV

    PG_DEV -.-> VOL_PG
    REDIS_DEV -.-> VOL_REDIS
    MINIO_DEV -.-> VOL_MINIO
```

## Production Environment

```mermaid
graph TB
    subgraph PROD["Production Deployment"]
        LB["Nginx Load Balancer<br/>:80 / :443"]

        subgraph APPS["Application Tier"]
            BE1["Backend 1<br/>FastAPI"]
            BE2["Backend 2<br/>FastAPI"]
            BE3["Backend 3<br/>FastAPI"]
        end

        subgraph WORKERS["Worker Tier"]
            CW1["Celery Worker 1"]
            CW2["Celery Worker 2"]
        end

        subgraph STATIC["Static Assets"]
            FE_PROD["Frontend<br/>Built Vue.js<br/>(served by Nginx)"]
        end

        subgraph DATA["Data Tier"]
            PG_PRIMARY["PostgreSQL Primary<br/>+ pgvector"]
            PG_REPLICA["PostgreSQL Replica<br/>(read-only)"]
            REDIS_CLUSTER["Redis Cluster"]
            MINIO_PROD["MinIO<br/>Object Storage"]
        end
    end

    CLIENT["Client Browser"] --> LB
    LB --> BE1
    LB --> BE2
    LB --> BE3
    LB --> FE_PROD

    BE1 --> PG_PRIMARY
    BE2 --> PG_PRIMARY
    BE3 --> PG_PRIMARY
    BE1 --> PG_REPLICA
    BE2 --> PG_REPLICA
    BE3 --> PG_REPLICA

    BE1 --> REDIS_CLUSTER
    BE2 --> REDIS_CLUSTER
    BE3 --> REDIS_CLUSTER

    CW1 --> PG_PRIMARY
    CW2 --> PG_PRIMARY
    CW1 --> REDIS_CLUSTER
    CW2 --> REDIS_CLUSTER
    CW1 --> MINIO_PROD
    CW2 --> MINIO_PROD

    PG_PRIMARY -.->|replication| PG_REPLICA
```

## Nginx Routing

```mermaid
flowchart LR
    REQ["Incoming Request"]

    REQ --> ROUTER{Nginx Router}

    ROUTER -->|"/"| FE_R["Frontend<br/>(static build)"]
    ROUTER -->|"/api/"| API_R["Backend<br/>(FastAPI :8000)"]
    ROUTER -->|"/ws/"| WS_R["WebSocket<br/>(upgrade to :8000)"]
    ROUTER -->|"/health"| HEALTH_R["Health Check<br/>(:8000/health)"]

    FE_R --> STATIC["dist/index.html"]
    API_R --> UPSTREAM["upstream backend"]
    WS_R --> UPSTREAM
```

## Resource Requirements

| Environment | RAM | CPU | Storage |
|-------------|-----|-----|---------|
| Development | 2 GB | 1 core | 10 GB |
| Staging | 4 GB | 2 cores | 50 GB |
| Production | 8 GB+ | 4 cores+ | 200 GB+ |
