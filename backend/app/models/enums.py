"""Enumerations used across models."""
import enum


class UserRole(str, enum.Enum):
    """User role enumeration."""
    USER = "user"
    EDITOR = "editor"
    ADMIN = "admin"


class DocumentStatus(str, enum.Enum):
    """Document processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OrgRole(str, enum.Enum):
    """Organization member role enumeration."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class DocumentVisibility(str, enum.Enum):
    """Document visibility enumeration."""
    PUBLIC = "public"           # All org members can view
    RESTRICTED = "restricted"   # Group/user-based access
    PRIVATE = "private"         # Owner + admins only


class AccessLevel(str, enum.Enum):
    """Document access level enumeration."""
    VIEW = "view"
    EDIT = "edit"
