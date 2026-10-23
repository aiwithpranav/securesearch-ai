"""Audit retention (Phase 9B, FR-36): old audit rows are removed after a configurable number of days (default 365).

How it stays safe:
- The audit tables are append-only. The only way a row can leave is the database function `audit_purge`, and its trigger also
  refuses to delete anything younger than 30 days, whatever the setting says (a floor).
- The purge removes the answer rows first, then the question rows, then the security events, and writes ONE `audit.purge`
  event with counts only (no text, no names).
- `AUDIT_RETENTION_DAYS=0` keeps everything forever; any other value below 30 is refused when the settings load.
- Nothing here reads or returns audit content: it only counts and deletes."""
import logging
from dataclasses import dataclass

from sqlalchemy import text

from app.core.config import settings
from app.db.sync import SyncSession

logger = logging.getLogger(__name__)
MIN_RETENTION_DAYS = 30


@dataclass(frozen=True)
class PurgeCounts:
    queries: int
    answers: int
    events: int

    @property
    def total(self) -> int:
        return self.queries + self.answers + self.events


def retention_days() -> int:
    return settings.audit_retention_days


def run(days: int | None = None, *, dry_run: bool = False) -> PurgeCounts:
    """Removes (or, with dry_run, only counts) the audit rows older than `days`. 0 or None-with-0-setting means keep everything."""
    d = settings.audit_retention_days if days is None else days
    if d == 0:
        return PurgeCounts(0, 0, 0)
    with SyncSession.begin() as s:
        row = s.execute(text("select * from audit_purge(:d, :dry)"), {"d": d, "dry": dry_run}).one()
    counts = PurgeCounts(int(row.queries), int(row.answers), int(row.events))
    if not dry_run and counts.total:
        logger.info("audit.purged", extra={"fields": {"queries": counts.queries, "answers": counts.answers, "events": counts.events, "older_than_days": d}})
    return counts
