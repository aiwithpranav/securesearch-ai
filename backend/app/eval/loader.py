"""Puts the evaluation corpus into a database.

- `apply_rules` gives documents their access rules (used by the dev loader and by the tests).
- `chunks_for` cuts a sample into the passages the tests store directly (the dev loader uses the real upload and
  ingestion instead, so real files are parsed, cut and embedded by the worker)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.eval.corpus import Rule
from app.models import Document, DocumentAcl, PermissionChangeEvent
from app.scripts.seed_access import _principal_id, _snapshot
from app.scripts.synthetic_docs import Sample, _all_text


def chunks_for(sample: Sample) -> list[tuple[str, str]]:
    """One passage per section: (section heading, text). The canary marker is part of the text."""
    return [(heading, (heading + "\n\n" if heading else "") + "\n\n".join(paragraphs)) for heading, paragraphs in _all_text(sample)]


def apply_rules(s: Session, rules: dict[str, list[Rule]]) -> int:
    """Adds the missing rules to each document (found by its file name). Returns how many rules were added.
    Safe to repeat: rules that exist are skipped. Every changed document gets a history row."""
    added_total = 0
    for filename, wanted in rules.items():
        doc = s.scalar(select(Document).where(Document.original_filename == filename, Document.deleted_at.is_(None)))
        if doc is None:
            continue
        before = _snapshot(s, doc.id)
        added = 0
        for (ptype, who), effect, permission in wanted:
            pid = _principal_id(s, ptype, who)
            existing = s.scalar(select(DocumentAcl).where(
                DocumentAcl.document_id == doc.id, DocumentAcl.principal_type == ptype,
                DocumentAcl.principal_id.is_(None) if pid is None else DocumentAcl.principal_id == pid,
                DocumentAcl.effect == effect, DocumentAcl.permission == permission,
            ))
            if existing is None:
                s.add(DocumentAcl(document_id=doc.id, principal_type=ptype, principal_id=pid, effect=effect, permission=permission))
                added += 1
        if added:
            s.flush()
            s.add(PermissionChangeEvent(document_id=doc.id, prev_acl=before, new_acl=_snapshot(s, doc.id), changed_by=None))
            added_total += added
    return added_total
