from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.env_doctor import check_env
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.core.errors import problem_details_handler
from app.api.v1 import health
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run env doctor at startup
    check_env()
    yield

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

# Exception handlers
app.add_exception_handler(Exception, problem_details_handler)

# Routers
app.include_router(health.router, prefix="/api/v1")
