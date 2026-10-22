"""Evaluation API (Phase 7B): start a run, list runs, see one run and its failures. System administrators only.

Why a separate process: the evaluation signs in as each demo person by replacing the login check of ITS OWN copy of
the application. Doing that inside the running server would hijack real requests, so a run is a child process
(`python -m app.scripts.run_eval`) that writes its results into the database.

Safety: results hold ids, code words, numbers and the synthetic question; never an answer or a document text. A live
run (real model, real cost) needs `confirm_cost: true`, an API key, and only one run may be active at a time."""
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.config import settings
from app.core.errors import AppError
from app.db.session import get_db
from app.eval.runner import estimate_live_cost
from app.llm import LlmNotConfigured, get_llm
from app.models import EvalCase, EvalResult, EvalRun, User
from app.schemas.evaluation import ResultOut, RunDetail, RunOut

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
STALE_AFTER = timedelta(minutes=30)  # a run that never finished stops blocking new runs after this long


class StartRun(BaseModel):
    live: bool = False
    confirm_cost: bool = False
    label: str = Field(default="manual run", max_length=80)


@router.post("/runs", response_model=RunOut, status_code=202)
async def start_run(body: StartRun, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> RunOut:
    if settings.app_env == "production":
        raise AppError(403, "Forbidden", "The evaluation does not run in production.")
    if body.live:
        est = estimate_live_cost()
        if not body.confirm_cost:
            raise AppError(
                422, "Confirm the cost", f"A live run asks about {est['questions']:.0f} questions and costs about ${est['estimated_usd']}. Send confirm_cost: true to run it.",
                extra={"estimated_usd": est["estimated_usd"], "questions": est["questions"]},
            )
        try:
            get_llm()
        except LlmNotConfigured:
            raise AppError(503, "Not available", "A live run needs an API key, and none is set.") from None
    cutoff = datetime.now(timezone.utc) - STALE_AFTER
    active = await db.scalar(select(EvalRun.id).where(EvalRun.status == "RUNNING", EvalRun.started_at > cutoff).limit(1))
    if active is not None:
        raise AppError(409, "Already running", "An evaluation is already running. Wait for it to finish.")
    run = EvalRun(label=body.label, model_mode="LIVE_MODEL" if body.live else "FAKE_MODEL", status="RUNNING", started_by=admin.id)
    db.add(run)
    await db.commit()
    command = [sys.executable, "-m", "app.scripts.run_eval", "--run-id", str(run.id), "--label", body.label]
    try:
        subprocess.Popen(command + (["--live", "--yes"] if body.live else []), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)  # noqa: S603
    except OSError:
        run.status, run.finished_at, run.summary = "FAILED", datetime.now(timezone.utc), {"error": "COULD_NOT_START"}
        await db.commit()
        raise AppError(503, "Not available", "The evaluation could not be started.") from None
    return RunOut.model_validate(run)


@router.get("/runs", response_model=list[RunOut])
async def list_runs(limit: int = Query(20, ge=1, le=100), _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> list[RunOut]:
    rows = (await db.scalars(select(EvalRun).order_by(EvalRun.started_at.desc()).limit(limit))).all()
    return [RunOut.model_validate(r) for r in rows]


async def _results(db: AsyncSession, run_id: uuid.UUID, failed_only: bool) -> list[ResultOut]:
    stmt = select(EvalResult, EvalCase).outerjoin(EvalCase, EvalCase.id == EvalResult.case_id).where(EvalResult.run_id == run_id).order_by(EvalResult.case_id)
    if failed_only:
        stmt = stmt.where(EvalResult.passed.is_(False))
    return [
        ResultOut(case_id=r.case_id, category=r.category, persona=c.persona if c else None, question=c.question if c else None,
                  passed=r.passed, leaked=r.leaked, latency_ms=r.latency_ms, detail=r.detail)
        for r, c in (await db.execute(stmt)).all()
    ]


async def _run_or_404(db: AsyncSession, run_id: uuid.UUID) -> EvalRun:
    run = await db.get(EvalRun, run_id)
    if run is None:
        raise AppError(404, "Not found", "Evaluation run not found.")
    return run


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(run_id: uuid.UUID, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> RunDetail:
    run = await _run_or_404(db, run_id)
    return RunDetail(**RunOut.model_validate(run).model_dump(), results=await _results(db, run_id, False))


@router.get("/runs/{run_id}/failures", response_model=list[ResultOut])
async def get_failures(run_id: uuid.UUID, _: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> list[ResultOut]:
    await _run_or_404(db, run_id)
    return await _results(db, run_id, True)
