from pydantic import BaseModel

from app.schemas.common import AnyPassword, Email, NewPassword
from app.schemas.users import UserOut


class LoginRequest(BaseModel):
    email: Email
    password: AnyPassword
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserOut


class ForgotPasswordRequest(BaseModel):
    email: Email


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: NewPassword


class ChangePasswordRequest(BaseModel):
    current_password: AnyPassword
    new_password: NewPassword


class MessageResponse(BaseModel):
    detail: str
