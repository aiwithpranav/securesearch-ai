"""Import every model here so Alembic can see all tables via Base.metadata."""
from app.models.access import DocumentAcl, Group, PermissionChangeEvent, user_groups
from app.models.audit import AccessEvent, AnswerAuditLog, QueryAuditLog
from app.models.auth_token import AuthToken
from app.models.chat import ChatFeedback, SearchHistory
from app.models.document import Document, DocumentChunk, DocumentVersion, IngestionJob, Notification
from app.models.user import Department, Role, User, user_roles

__all__ = [
    "AccessEvent",
    "AnswerAuditLog",
    "AuthToken",
    "ChatFeedback",
    "Department",
    "Document",
    "DocumentAcl",
    "DocumentChunk",
    "DocumentVersion",
    "Group",
    "IngestionJob",
    "Notification",
    "PermissionChangeEvent",
    "QueryAuditLog",
    "Role",
    "SearchHistory",
    "User",
    "user_groups",
    "user_roles",
]
