"""Housekeeping you can run by hand (the same jobs also run every night in the worker).

    docker compose exec backend python -m app.scripts.maintenance audit-purge --dry-run   # how many audit rows are past retention
    docker compose exec backend python -m app.scripts.maintenance audit-purge             # remove them (needs AUDIT_RETENTION_DAYS)
    docker compose exec backend python -m app.scripts.maintenance cleanup                 # remove passages of old versions

Prints counts only. Refuses to run when APP_ENV is production unless --yes is given."""
import argparse
import sys

from app.audit import retention
from app.core.config import settings
from app.ingest import cleanup


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("job", choices=["audit-purge", "cleanup"])
    p.add_argument("--dry-run", action="store_true", help="only count (audit-purge)")
    p.add_argument("--yes", action="store_true", help="confirm a real run when APP_ENV is production")
    args = p.parse_args(argv)
    if settings.app_env == "production" and not args.dry_run and not args.yes:
        print("APP_ENV is production: add --yes to confirm.")
        return 3
    if args.job == "audit-purge":
        if settings.audit_retention_days == 0:
            print("AUDIT_RETENTION_DAYS is 0: everything is kept, nothing to purge.")
            return 0
        c = retention.run(dry_run=args.dry_run)
        print(f"{'Would remove' if args.dry_run else 'Removed'} (older than {settings.audit_retention_days} days): {c.queries} questions, {c.answers} answers, {c.events} security events.")
    else:
        print(f"Removed {cleanup.run()} old passage(s); the newest {settings.keep_versions} version(s) of every document are kept.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
