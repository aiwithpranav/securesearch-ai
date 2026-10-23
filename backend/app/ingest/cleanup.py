"""Removes the old passages of old document versions (Phase 9B, backlog 38).

Every new version of a document leaves the passages of the previous version in the database, switched off, so a bad new file
can be compared and nothing is lost at once. They would pile up forever. This keeps the passages of the newest KEEP_VERSIONS
versions (default 3) of every live document and removes the rest.

Safe by construction:
- only passages that are switched off (`is_active = false`) are ever removed: what searches can see is never touched;
- deleted documents are left alone (a restore re-indexes from the stored original file anyway);
- the original files and the version records are not touched, so any version can still be re-indexed."""
import logging

from sqlalchemy import text

from app.core.config import settings
from app.db.sync import SyncSession

logger = logging.getLogger(__name__)

_DELETE = text("""
    delete from document_chunks
    where not is_active
      and document_version_id in (
        select id from (
          select v.id, row_number() over (partition by v.document_id order by v.version_no desc) as rn
          from document_versions v join documents d on d.id = v.document_id
          where d.deleted_at is null
        ) ranked where rn > :keep
      )
""")


def run(keep: int | None = None) -> int:
    """Returns how many passages were removed."""
    n = settings.keep_versions if keep is None else keep
    if n < 1:
        raise ValueError("keep at least one version")
    with SyncSession.begin() as s:
        removed = s.execute(_DELETE, {"keep": n}).rowcount or 0  # type: ignore[attr-defined]
    if removed:
        logger.info("ingest.cleanup", extra={"fields": {"removed_passages": removed, "kept_versions": n}})
    return removed
