"""Loads the 36 extra evaluation documents (with the 12 from Phase 3 that makes 48) through the real upload and
ingestion, and gives them their access rules.

Run inside the backend container (the worker must be running; the demo people and groups must exist):
    docker compose exec backend python -m app.scripts.load_eval_corpus

Safe to run twice: documents with identical content are skipped. Synthetic data only; refuses to run when APP_ENV is
production. Wait until the worker has processed the documents (Admin, Documents shows READY) before an evaluation."""
import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.errors import AppError
from app.db.session import async_session, engine
from app.db.sync import SyncSession
from app.eval.corpus import EXTRA_RULES, EXTRA_SAMPLES
from app.eval.loader import apply_rules
from app.ingest.validation import validate_file
from app.models import Department, Role, User
from app.models.user import user_roles
from app.scripts.synthetic_docs import build
from app.services import document_service as svc


async def main() -> int:
    if settings.app_env == "production":
        print("Refusing to load evaluation documents when APP_ENV is production.")
        return 1
    async with async_session() as db:
        admin = await db.scalar(
            select(User).join(user_roles, user_roles.c.user_id == User.id).join(Role, Role.id == user_roles.c.role_id)
            .where(Role.name == "system_admin", User.is_active.is_(True)).order_by(User.email).limit(1)
        )
        if admin is None:
            print("No active system_admin user found. Run the seed scripts first.")
            return 1
        created = skipped = 0
        for s in EXTRA_SAMPLES:
            dept = await db.scalar(select(Department).where(Department.name == s.department))
            if dept is None:
                print(f"Department '{s.department}' is missing. Run the seed script first.")
                return 1
            try:
                await svc.create_upload(db, admin, validate_file(s.filename, build(s)), s.title, dept.id, s.document_type, s.sensitivity, None, None)
                created += 1
            except AppError as exc:
                if exc.status != 409:
                    raise
                skipped += 1
    await engine.dispose()
    with SyncSession.begin() as session:
        try:
            added = apply_rules(session, EXTRA_RULES)
        except LookupError as exc:
            print(f"Missing data: {exc}. Run seed_access first.")
            return 1
    print(f"Queued {created} evaluation document(s), skipped {skipped} duplicate(s), added {added} access rule(s).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
