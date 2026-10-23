import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import access, audit, auth, chat, dashboards, documents, evaluation, health, notifications, search, sync, users
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
from app.core.metrics import MetricsMiddleware
from app.core.middleware import RequestIDMiddleware
from app.core.redis import close_redis
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Run env doctor at startup
    check_env()
    if settings.search_warmup:
        app.state.warmup = asyncio.create_task(asyncio.to_thread(search.warm_up))  # loads the models in the background
    yield
    # Close connections cleanly on shutdown
    await close_redis()
    await engine.dispose()


setup_logging()

app = FastAPI(lifespan=lifespan, title="SecureSearch AI API", docs_url="/api/docs", openapi_url="/api/openapi.json")

# Middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)
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
app.include_router(access.groups_router, prefix="/api/v1")
app.include_router(access.manage_router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(evaluation.router, prefix="/api/v1")
app.include_router(dashboards.router, prefix="/api/v1")
app.include_router(sync.router, prefix="/api/v1")
