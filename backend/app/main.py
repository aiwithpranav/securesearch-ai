from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import auth, documents, health, notifications, users
from app.core.config import settings
from app.core.env_doctor import check_env
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    problem_details_handler,
    validation_error_handler,
)
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.core.redis import close_redis
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Run env doctor at startup
    check_env()
    yield
    # Close connections cleanly on shutdown
    await close_redis()
    await engine.dispose()


setup_logging()

app = FastAPI(lifespan=lifespan, title="SecureSearch AI API", docs_url="/api/docs", openapi_url="/api/openapi.json")

# Middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers (all errors use Problem Details)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, problem_details_handler)

# Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
