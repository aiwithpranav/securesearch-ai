"""Response shapes for documents, jobs and notifications.

IMPORTANT (admin is not reader): nothing here contains document TEXT. A document is described by
metadata and counts only. There is no field for chunk text, a preview, or a download link."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.users import DepartmentOut


class UserRef(BaseModel):
    id: uuid.UUID
    full_name: str


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    attempt: int
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    version_no: int
    content_hash: str
    size_bytes: int
    content_type: str
    created_at: datetime


class DocumentOut(BaseModel):
    id: uuid.UUID
    title: str
    original_filename: str
    document_type: str
    department: DepartmentOut
    sensitivity_level: int
    sensitivity_name: str
    status: str
    allowed_countries: list[str] | None = None
    current_version_no: int | None = None
    version_count: int
    chunk_count: int  # a NUMBER of active chunks, never their text
    latest_job: JobOut | None = None
    uploaded_by: UserRef
    created_at: datetime
    updated_at: datetime


class DocumentPage(BaseModel):
    items: list[DocumentOut]
    total: int
    limit: int
    offset: int


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    department_id: int | None = None
    document_type: str | None = None
    sensitivity_level: int | None = Field(default=None, ge=0, le=4)
    allowed_countries: list[str] | None = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    payload: dict[str, Any]
    read_at: datetime | None = None
    created_at: datetime
