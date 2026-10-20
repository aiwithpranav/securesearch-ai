"""Response and request shapes for groups, access rules, rule history and the access preview.
Nothing here contains document text."""
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.users import DepartmentOut

PrincipalType = Literal["USER", "ROLE", "GROUP", "DEPARTMENT", "COMPANY"]
Effect = Literal["ALLOW", "DENY"]
Permission = Literal["READ", "DOWNLOAD", "MANAGE"]


class MemberOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str


class GroupOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    member_count: int


class GroupDetail(GroupOut):
    members: list[MemberOut]


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    description: str | None = Field(default=None, max_length=200)


class MemberAdd(BaseModel):
    user_id: uuid.UUID


class AclCreate(BaseModel):
    principal_type: PrincipalType
    principal_id: str | None = Field(default=None, max_length=64)  # a user id, or a role/group/department id; none for COMPANY
    effect: Effect
    permission: Permission
    expires_at: datetime | None = None


class AclPatch(BaseModel):
    """Only these can change. The principal is fixed: to change WHO, delete the rule and add a new one."""

    effect: Effect | None = None
    permission: Permission | None = None
    expires_at: datetime | None = None  # send null to remove the expiry


class AclOut(BaseModel):
    id: uuid.UUID
    principal_type: PrincipalType
    principal_id: str | None
    principal_name: str
    effect: Effect
    permission: Permission
    expires_at: datetime | None
    expired: bool
    granted_by: uuid.UUID | None
    created_at: datetime


class HistoryOut(BaseModel):
    id: uuid.UUID
    changed_at: datetime
    changed_by: MemberOut | None
    prev_acl: list[dict[str, Any]]
    new_acl: list[dict[str, Any]]


class DecisionOut(BaseModel):
    allowed: bool
    code: str


class PreviewUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    department: DepartmentOut
    clearance_level: int
    country: str
    is_active: bool
    roles: list[str]


class PreviewOut(BaseModel):
    user: PreviewUser
    document_status: str
    sensitivity_level: int
    allowed_countries: list[str] | None
    read: DecisionOut
    download: DecisionOut
    manage: DecisionOut
    matching_rules: list[AclOut]  # the live rules that match this user (they explain the answers)
