"""Admin API for documents and ingestion (Phase 3B). Every route here needs the system_admin role.

Reminder: an admin manages documents but is NOT a reader. No route returns document text,
chunks, previews or the original file."""
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core import rate_limit
from app.core.config import settings
from app.core.errors import AppError
from app.db.session import get_db
from app.ingest.errors import IngestError
from app.ingest.validation import read_limited, validate_file
from app.models import User
from app.models import document as dm
from app.schemas.documents import DocumentOut, DocumentPage, JobOut, VersionOut, VersionUploadOut
from app.services import document_service as svc

router = APIRouter(tags=["documents"], dependencies=[Depends(require_admin)])


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _upload_error(err: IngestError) -> AppError:
    return AppError(
        413 if err.code == "TOO_LARGE" else 422,
        "Upload rejected",
        err.message,
        extra={"error_code": err.code},
    )


@router.post("/documents/upload", status_code=status.HTTP_202_ACCEPTED, response_model=DocumentOut)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    department_id: int = Form(...),
    document_type: str = Form(...),
    sensitivity_level: int = Form(..., ge=0, le=4),
    title: str | None = Form(default=None, max_length=200),
    allowed_countries: str | None = Form(default=None, max_length=100),
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    allowed, retry = await rate_limit.hit(rate_limit.key_for("upload", str(actor.id)), settings.upload_limit_per_minute, 60)
    if not allowed:
        raise AppError(
            429, "Too many attempts", "Too many uploads. Try again shortly.",
            headers={"Retry-After": str(retry)}, extra={"retry_after_seconds": retry},
        )
    dtype = svc.check_type(document_type)
    countries = svc.parse_countries(allowed_countries)
    try:
        data = await read_limited(file)
        vfile = validate_file(file.filename, data)
    except IngestError as err:
        raise _upload_error(err) from None
    return await svc.create_upload(
        db, actor, vfile, title, department_id, dtype, sensitivity_level, countries, _rid(request)
    )


@router.get("/documents", response_model=DocumentPage)
async def list_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status"),
    department_id: int | None = Query(None),
    deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> DocumentPage:
    if status_filter is not None and status_filter not in dm.STATUSES:
        raise AppError(422, "Validation failed", f"Status must be one of: {', '.join(dm.STATUSES)}.")
    items, total = await svc.list_documents(db, limit, offset, status_filter, department_id, deleted)
    return DocumentPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> DocumentOut:
    return await svc.get_document(db, document_id)


# PATCH /documents/{id} (edit metadata) lives in app/api/v1/access.py: it needs MANAGE on the document.


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    await svc.delete_document(db, document_id, actor, _rid(request))


@router.get("/documents/{document_id}/versions", response_model=list[VersionOut])
async def list_versions(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[object]:
    return await svc.list_versions(db, document_id)  # type: ignore[return-value]


@router.post("/documents/{document_id}/versions", response_model=VersionUploadOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_version(
    document_id: uuid.UUID,
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> VersionUploadOut:
    """A new file for an existing document. Same content as the newest version answers 200 UNCHANGED and does nothing."""
    allowed, retry = await rate_limit.hit(rate_limit.key_for("upload", str(actor.id)), settings.upload_limit_per_minute, 60)
    if not allowed:
        raise AppError(
            429, "Too many attempts", "Too many uploads. Try again shortly.",
            headers={"Retry-After": str(retry)}, extra={"retry_after_seconds": retry},
        )
    try:
        data = await read_limited(file)
        vfile = validate_file(file.filename, data)
    except IngestError as err:
        raise _upload_error(err) from None
    out = await svc.upload_new_version(db, actor, document_id, vfile, _rid(request))
    if out.result == "UNCHANGED":
        response.status_code = status.HTTP_200_OK
    return out


@router.post("/documents/{document_id}/restore", response_model=DocumentOut)
async def restore_document(
    document_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    return await svc.restore_document(db, document_id, actor, _rid(request))


@router.post("/documents/{document_id}/reindex", status_code=status.HTTP_202_ACCEPTED, response_model=JobOut)
async def reindex_document(
    document_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    return await svc.reindex(db, document_id, actor, _rid(request))


@router.get("/ingestion/jobs")
async def list_jobs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status"),
    document_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    if status_filter is not None and status_filter not in dm.STATUSES:
        raise AppError(422, "Validation failed", f"Status must be one of: {', '.join(dm.STATUSES)}.")
    jobs, total = await svc.list_jobs(db, limit, offset, status_filter, document_id)
    return {"items": [JobOut.model_validate(j) for j in jobs], "total": total, "limit": limit, "offset": offset}


@router.get("/ingestion/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> object:
    return await svc.get_job(db, job_id)
