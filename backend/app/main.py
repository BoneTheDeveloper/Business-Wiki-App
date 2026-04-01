"""FastAPI main application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import init_db
from app.auth import auth_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.search import router as search_router
from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.admin import router as admin_router
from app.api.v1.routes.websocket import router as ws_router
from app.api.v1.routes.organizations import router as organizations_router
from app.api.v1.routes.invitations import router as invitations_router
from app.api.v1.routes.groups import router as groups_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: Cleanup if needed


app = FastAPI(
    title="RAG Business Wiki API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS middleware (Supabase Auth handles sessions -- no server-side session needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(ws_router)  # WebSocket at /ws/documents
app.include_router(organizations_router, prefix="/api/v1")
app.include_router(invitations_router, prefix="/api/v1")
app.include_router(groups_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "backend"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "RAG Business Wiki API",
        "version": "0.1.0",
        "docs": "/api/docs"
    }
