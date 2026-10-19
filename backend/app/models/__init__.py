"""Import every model here so Alembic can see all tables via Base.metadata."""
from app.models.auth_token import AuthToken
from app.models.user import Department, Role, User, user_roles

__all__ = ["AuthToken", "Department", "Role", "User", "user_roles"]
