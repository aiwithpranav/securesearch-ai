"""Uploads the synthetic documents as the first system_admin, through the same service code the API uses.
Handy to fill the system with demo data without a user interface.

Run inside the backend container (the worker must be running):
    docker compose exec backend python -m app.scripts.load_synthetic_docs
Safe to run twice: documents with identical content are skipped (409)."""
import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.errors import AppError
from app.db.session import async_session, engine
from app.ingest.validation import validate_file
from app.models import Department, Role, User
from app.models.user import user_roles
from app.scripts.synthetic_docs import SAMPLES, build
from app.services import document_service as svc


async def main() -> int:
    if settings.app_env == "production":
        print("Refusing to load demo documents when APP_ENV is production.")
        return 1
    async with async_session() as db:
        admin = await db.scalar(
            select(User).join(user_roles, user_roles.c.user_id == User.id).join(Role, Role.id == user_roles.c.role_id)
            .where(Role.name == "system_admin", User.is_active.is_(True)).order_by(User.email).limit(1)
        )
        if admin is None:
            print("No active system_admin user found. Run the seed script first.")
            return 1
        created = skipped = 0
        for s in SAMPLES:
            dept = await db.scalar(select(Department).where(Department.name == s.department))
            if dept is None:
                print(f"Department '{s.department}' is missing. Run the seed script first.")
                return 1
            vfile = validate_file(s.filename, build(s))
            try:
                await svc.create_upload(db, admin, vfile, s.title, dept.id, s.document_type, s.sensitivity, None, None)
                created += 1
            except AppError as exc:
                if exc.status == 409:
                    skipped += 1
                else:
                    raise
    await engine.dispose()
    print(f"Queued {created} document(s) for processing, skipped {skipped} duplicate(s).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
