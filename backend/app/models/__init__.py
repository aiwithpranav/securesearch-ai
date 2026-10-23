"""Import every model here so Alembic can see all tables via Base.metadata."""
from app.models.access import DocumentAcl, Group, PermissionChangeEvent, user_groups
from app.models.audit import AccessEvent, AnswerAuditLog, QueryAuditLog
from app.models.auth_token import AuthToken
from app.models.chat import ChatFeedback, SearchHistory
from app.models.document import Document, DocumentChunk, DocumentVersion, IngestionJob, Notification
from app.models.evaluation import EvalCase, EvalResult, EvalRun
from app.models.sync import SyncRun, SyncSource
from app.models.user import Department, Role, User, user_roles

__all__ = [
    "AccessEvent",
    "AnswerAuditLog",
    "AuthToken",
    "ChatFeedback",
    "Department",
    "EvalCase",
    "EvalResult",
    "EvalRun",
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
    "SyncRun",
    "SyncSource",
    "User",
    "user_groups",
    "user_roles",
]
