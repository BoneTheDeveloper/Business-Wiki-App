# Routes package
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.search import router as search_router
from app.api.v1.routes.organizations import router as organizations_router
from app.api.v1.routes.invitations import router as invitations_router
from app.api.v1.routes.groups import router as groups_router

__all__ = [
    "documents_router",
    "search_router",
    "organizations_router",
    "invitations_router",
    "groups_router"
]
