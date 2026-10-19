from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_trusted_origin
from app.core import mailer
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.users import UserOut
from app.services import auth_service
from app.services.auth_service import SessionResult

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/api/v1/auth"  # the browser sends it only to auth endpoints


def _set_cookie(response: Response, result: SessionResult) -> None:
    response.set_cookie(
        COOKIE_NAME,
        result.refresh_token,
        max_age=result.cookie_max_age,  # None = ends when the browser closes
        httponly=True,  # JavaScript cannot read it
        secure=settings.app_env == "production",  # HTTPS only in production
        samesite="lax",
        path=COOKIE_PATH,
    )


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)


def _token_response(result: SessionResult) -> TokenResponse:
    return TokenResponse(
        access_token=result.access_token,
        expires_in=result.expires_in,
        user=UserOut.model_validate(result.user),
    )


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    result = await auth_service.login(
        db, body.email, body.password, body.remember_me, _ip(request), _request_id(request)
    )
    _set_cookie(response, result)
    return _token_response(result)


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(require_trusted_origin)])
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        result = await auth_service.refresh(db, refresh_token, _request_id(request))
    except Exception:
        _clear_cookie(response)  # bad/old cookie: remove it from the browser
        raise
    _set_cookie(response, result)
    return _token_response(result)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_trusted_origin)],
)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.logout(db, refresh_token)
    _clear_cookie(response)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.logout_all(db, user, _request_id(request))
    _clear_cookie(response)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED, response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    found = await auth_service.forgot_password(db, body.email, _ip(request), _request_id(request))
    if found is not None:
        user, raw = found
        background.add_task(mailer.send_reset_email, user.email, raw)  # runs after the response
    # Same answer whether or not the account exists.
    return MessageResponse(detail="If that account exists, a reset link has been sent.")


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    body: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> None:
    await auth_service.reset_password(db, body.token, body.new_password, _request_id(request))


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.change_password(
        db, user, body.current_password, body.new_password, _request_id(request)
    )
    _clear_cookie(response)  # all sessions ended; sign in again with the new password
