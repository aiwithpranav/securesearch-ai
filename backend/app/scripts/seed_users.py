"""Creates the demo departments, roles and the 8 persona users (+1 deactivated user).

Run inside the backend container:
    docker compose exec backend python -m app.scripts.seed_users

All demo users share one password, read from SEED_USER_PASSWORD in .env
(never stored in Git, never printed). Existing users are left untouched, so it is safe to re-run.
Synthetic data only."""
import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import async_session, engine
from app.models import Department, Role, User

DEPARTMENTS = [
    "HR", "Finance", "Engineering", "Sales", "Legal", "Security", "Customer Support", "Company-wide",
]

ROLES = {
    "employee": "Every person with an account",
    "engineer": "Engineering staff",
    "finance_analyst": "Finance analyst",
    "hr_manager": "HR manager",
    "sales_executive": "Sales executive",
    "security_admin": "Security administrator",
    "executive": "Company executive",
    "system_admin": "Manages users and settings. Does NOT automatically read documents.",
    "auditor": "Compliance auditor. Sees metadata, not document content.",
}

# email, name, department, clearance, country, employment, roles, active
# Blueprint persona departments Executive / IT / Compliance are not in the 8-department list,
# so they map to Company-wide / Engineering / Legal (see phase-02 WALKTHROUGH).
USERS = [
    ("swara@demo", "Swaranjali Jadhav", "Engineering", 1, "IN", "full_time", ["employee", "engineer"], True),
    ("pranav@demo", "Pranav Mane", "Finance", 2, "IN", "full_time", ["employee", "finance_analyst"], True),
    ("dhanashree@demo", "Dhanashree Patil", "HR", 3, "IN", "full_time", ["employee", "hr_manager"], True),
    ("akshay@demo", "Akshay Khade", "Sales", 1, "US", "full_time", ["employee", "sales_executive"], True),
    ("sanjana@demo", "Sanjana Aid", "Security", 3, "IN", "full_time", ["employee", "security_admin"], True),
    ("shivam@demo", "Shivam Suryawanshi", "Company-wide", 4, "IN", "full_time", ["employee", "executive"], True),
    ("prashant@demo", "Prashant Ghewari", "Engineering", 2, "IN", "full_time", ["employee", "system_admin"], True),
    ("karunesh@demo", "Karunesh Potdar", "Legal", 2, "IN", "full_time", ["employee", "auditor"], True),
    ("former@demo", "Former Employee", "Sales", 0, "IN", "contractor", ["employee"], False),
]


async def main() -> int:
    password = settings.seed_user_password
    if settings.app_env == "production":
        print("Refusing to seed demo users when APP_ENV is production.")
        return 1
    if len(password) < settings.min_password_length or password == "CHANGE_ME":
        print(
            f"SEED_USER_PASSWORD is missing or too short (need {settings.min_password_length}+ "
            "characters). Add it to .env, restart the backend, then run this again."
        )
        return 1

    password_hash = hash_password(password)
    created = 0
    async with async_session() as db:
        depts: dict[str, Department] = {}
        for name in DEPARTMENTS:
            dept = await db.scalar(select(Department).where(Department.name == name))
            if dept is None:
                dept = Department(name=name)
                db.add(dept)
            depts[name] = dept
        roles: dict[str, Role] = {}
        for name, desc in ROLES.items():
            role = await db.scalar(select(Role).where(Role.name == name))
            if role is None:
                role = Role(name=name, description=desc)
                db.add(role)
            roles[name] = role
        await db.flush()

        for email, full_name, dept, clearance, country, employment, role_names, active in USERS:
            if await db.scalar(select(User).where(User.email == email)):
                continue
            user = User(
                email=email,
                full_name=full_name,
                password_hash=password_hash,
                department_id=depts[dept].id,
                clearance_level=clearance,
                country=country,
                employment_type=employment,
                is_active=active,
            )
            user.roles = [roles[r] for r in role_names]
            db.add(user)
            created += 1
        await db.commit()

    await engine.dispose()
    print(f"Seed done: {created} new user(s) created, {len(USERS) - created} already existed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
