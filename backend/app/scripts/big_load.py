"""Loads the scale demo: synthetic people and thousands of real public documents (Phase 10).

Run inside the backend container of the SEPARATE big stack (see docs/phases/phase-10-scale-demo/WALKTHROUGH.md):
    docker compose -p securesearch-big -f docker-compose.yml -f docker-compose.big.yml exec backend \\
        python -m app.scripts.big_load --users 1000

It needs the demo departments and roles (seed_users) and a running worker. Documents go through the real upload and
ingestion; the worker then parses, cuts and embeds them (this takes hours for 100,000 passages: let it run).
Safe to run twice: documents with identical content are skipped and existing people are left untouched.
Synthetic people only; refuses to run when APP_ENV is production."""
import argparse
import asyncio
import sys
import time
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import hash_password
from app.db.session import async_session, engine
from app.db.sync import SyncSession
from app.eval.loader import apply_rules
from app.ingest.errors import IngestError
from app.ingest.validation import validate_file
from app.models import Department, Role, User
from app.models.user import user_roles
from app.scale.corpus import (
    MIN_BODY_CHARS,
    canary_for,
    classify,
    clean_markdown,
    fallback_title,
    rules_for,
    unique_filename,
    wants_canary,
    with_canary,
)
from app.scale.people import make_people
from app.services import document_service as svc

DEFAULT_DIR = "/data/big"


async def _create_people(count: int) -> tuple[int, int]:
    """Creates the synthetic people (one password hash shared by all, so 1,000 people take seconds, not minutes)."""
    password_hash = hash_password(settings.seed_user_password)
    created = 0
    async with async_session() as db:
        depts = {d.name: d for d in (await db.scalars(select(Department))).all()}
        roles = {r.name: r for r in (await db.scalars(select(Role))).all()}
        existing = set((await db.scalars(select(User.email).where(User.email.like("big%@demo")))).all())
        for p in make_people(count):
            if p.email in existing:
                continue
            user = User(
                email=p.email, full_name=p.full_name, password_hash=password_hash, department_id=depts[p.department].id,
                clearance_level=p.clearance, country=p.country, employment_type="full_time", is_active=True,
            )
            user.roles = [roles[r] for r in p.roles]
            db.add(user)
            created += 1
        await db.commit()
    return created, count - created


def _walk(root: Path, limit: int | None) -> list[Path]:
    files = sorted(p for p in root.rglob("*.md") if p.is_file())
    return files[:limit] if limit else files


async def _upload(root: Path, limit: int | None) -> tuple[dict[str, list], dict[str, int]]:
    """Uploads every usable file. Returns the access rules by file name and the counts."""
    counts = {"files": 0, "uploaded": 0, "duplicate": 0, "too_short": 0, "rejected": 0, "canaries": 0}
    rules: dict[str, list] = {}
    async with async_session() as db:
        admin = await db.scalar(
            select(User).join(user_roles, user_roles.c.user_id == User.id).join(Role, Role.id == user_roles.c.role_id)
            .where(Role.name == "system_admin", User.is_active.is_(True)).order_by(User.email).limit(1)
        )
        if admin is None:
            raise SystemExit("No active system_admin user found. Run seed_users first.")
        depts = {d.name: d.id for d in (await db.scalars(select(Department))).all()}
        started = time.time()
        for path in _walk(root, limit):
            counts["files"] += 1
            rel = path.relative_to(root).as_posix()
            title, body = clean_markdown(path.read_text(encoding="utf-8", errors="replace"), fallback_title(rel))
            if len(body) < MIN_BODY_CHARS:
                counts["too_short"] += 1
                continue
            place = classify(rel)
            if wants_canary(rel, place.sensitivity):
                body = with_canary(body, canary_for(rel))
                counts["canaries"] += 1
            filename = unique_filename(rel)
            try:
                vfile = validate_file(filename, body.encode("utf-8"))
                await svc.create_upload(
                    db, admin, vfile, title, depts[place.department], place.document_type, place.sensitivity, None, None
                )
            except AppError as exc:
                if exc.status != 409:
                    raise
                counts["duplicate"] += 1
                continue
            except IngestError:
                counts["rejected"] += 1
                continue
            counts["uploaded"] += 1
            rules[filename] = rules_for(place)
            if counts["files"] % 500 == 0:
                print(f"  {counts['files']} files read, {counts['uploaded']} uploaded ({int(time.time() - started)} s)", flush=True)
    return rules, counts


async def main(args: argparse.Namespace) -> int:
    if settings.app_env == "production":
        print("Refusing to load the scale demo when APP_ENV is production.")
        return 1
    root = Path(args.dir)
    if not root.is_dir():
        print(f"Folder {root} not found. Mount the downloaded documents there (see the walkthrough).")
        return 1
    created, existed = await _create_people(args.users)
    print(f"People: {created} created, {existed} already existed.")
    rules, counts = await _upload(root, args.limit)
    await engine.dispose()
    with SyncSession.begin() as session:
        added = apply_rules(session, rules)
    print(
        f"Documents: {counts['files']} files read, {counts['uploaded']} uploaded, {counts['duplicate']} duplicate, "
        f"{counts['too_short']} too short, {counts['rejected']} rejected; {counts['canaries']} carry a canary marker."
    )
    print(f"Access rules added: {added}. The worker now indexes the documents; follow it with: python -m app.scripts.big_check --status")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dir", default=DEFAULT_DIR, help="folder with the downloaded documents")
    parser.add_argument("--users", type=int, default=1000, help="how many synthetic people")
    parser.add_argument("--limit", type=int, default=None, help="only the first N files (a small trial)")
    sys.exit(asyncio.run(main(parser.parse_args())))
