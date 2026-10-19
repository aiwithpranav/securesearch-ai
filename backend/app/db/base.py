from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """All database models inherit from this. Alembic reads Base.metadata."""
