"""Import every model here so Alembic can see all tables via Base.metadata."""
from app.models.auth_token import AuthToken
from app.models.document import Document, DocumentChunk, DocumentVersion, IngestionJob, Notification
from app.models.user import Department, Role, User, user_roles

__all__ = [
    "AuthToken",
    "Department",
    "Document",
    "DocumentChunk",
    "DocumentVersion",
    "IngestionJob",
    "Notification",
    "Role",
    "User",
    "user_roles",
]
