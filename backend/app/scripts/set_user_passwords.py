"""Sets the password of existing users from lines like:  email: password

Input comes from standard input, so passwords never appear in shell history or process lists.
Lines starting with # and empty lines are ignored. Only users that already exist are changed.
Each changed user is signed out everywhere and any login lockout is cleared.

Run from the repository root (PowerShell), with a local credentials file that is NOT in Git:
    Get-Content demo-credentials.local.txt | docker compose exec -T backend python -m app.scripts.set_user_passwords

Meant for synthetic demo accounts on a developer machine. It refuses to run when APP_ENV is production."""
import asyncio
import sys

from sqlalchemy import select

from app.core import rate_limit
from app.core.config import settings
from app.core.redis import close_redis
from app.core.security import hash_password
from app.db.session import async_session, engine
from app.models import User
from app.services.auth_service import revoke_all_sessions


def parse_lines(text: str) -> dict[str, str]:
    """Turns 'email: password' lines into {email: password}. Raises ValueError on a bad line."""
    result: dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        email, sep, password = line.partition(":")
        email = email.strip().lower()
        password = password.strip()
        if not sep or not email or not password:
            raise ValueError(f"Line {number} must look like 'email: password'.")
        if len(password) < settings.min_password_length or len(password) > 128:
            raise ValueError(
                f"Line {number}: the password must be {settings.min_password_length} to 128 characters."
            )
        if email in result:
            raise ValueError(f"Line {number}: {email} appears twice.")
        result[email] = password
    return result


async def main() -> int:
    if settings.app_env == "production":
        print("Refusing to set demo passwords when APP_ENV is production.")
        return 1
    try:
        wanted = parse_lines(sys.stdin.read())
    except ValueError as exc:
        print(str(exc))
        return 1
    if not wanted:
        print("No 'email: password' lines were found on standard input.")
        return 1

    changed: list[str] = []
    missing: list[str] = []
    async with async_session() as db:
        for email, password in wanted.items():
            user = await db.scalar(select(User).where(User.email == email))
            if user is None:
                missing.append(email)
                continue
            user.password_hash = hash_password(password)
            await revoke_all_sessions(db, user)
            changed.append(email)
        await db.commit()
    for email in changed:
        await rate_limit.clear(rate_limit.key_for("login-fail", email))

    await close_redis()
    await engine.dispose()
    print(f"Passwords set for {len(changed)} user(s).")
    if missing:
        print("No such user (skipped): " + ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
