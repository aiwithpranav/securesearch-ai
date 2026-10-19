import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import Email, EmploymentType


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    department: DepartmentOut
    clearance_level: int
    country: str
    employment_type: str
    roles: list[str] = Field(validation_alias="role_names")
    is_active: bool
    last_login_at: datetime | None = None


def _check_country(v: str | None) -> str | None:
    if v is None:
        return v
    v = v.strip().upper()
    if len(v) != 2 or not v.isalpha():
        raise ValueError("Country must be a 2-letter code such as IN or US.")
    return v


class UserCreate(BaseModel):
    email: Email
    full_name: str = Field(min_length=1, max_length=120)
    department_id: int
    clearance_level: int = Field(default=0, ge=0, le=4)
    country: str
    employment_type: EmploymentType = "full_time"
    role_ids: list[int] = Field(default_factory=list, max_length=20)

    _country = field_validator("country")(_check_country)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    department_id: int | None = None
    clearance_level: int | None = Field(default=None, ge=0, le=4)
    country: str | None = None
    employment_type: EmploymentType | None = None
    is_active: bool | None = None

    _country = field_validator("country")(_check_country)


class RoleAssign(BaseModel):
    """The complete list of roles the user should have (replaces the old list)."""

    role_ids: list[int] = Field(max_length=20)


class RoleCreate(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,39}$")
    description: str | None = Field(default=None, max_length=200)
