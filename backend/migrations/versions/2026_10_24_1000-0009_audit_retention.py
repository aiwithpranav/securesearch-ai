"""audit retention: a guarded purge of old audit rows (FR-36)

The audit tables stay append-only. A row can be deleted only inside `audit_purge()`, which switches a flag on for its own
transaction, and the trigger accepts a delete only when that flag is on AND the row is older than 30 days (a floor that no
retention setting can lower). The purge writes one `audit.purge` event with counts only.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-24
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

TABLES = ("query_audit_logs", "answer_audit_logs", "access_events")


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE'
               AND coalesce(current_setting('app.audit_purge', true), '') = 'on'
               AND OLD.created_at < now() - interval '30 days' THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION 'audit rows are append-only (% on %)', TG_OP, TG_TABLE_NAME;
        END $$
    """)
    op.execute("""
        CREATE FUNCTION audit_purge(retention_days integer, dry_run boolean DEFAULT false)
        RETURNS TABLE (queries bigint, answers bigint, events bigint) LANGUAGE plpgsql AS $$
        DECLARE
            cutoff timestamptz;
            n_answers bigint;
            n_queries bigint;
            n_events bigint;
        BEGIN
            IF retention_days < 30 THEN
                RAISE EXCEPTION 'audit retention must be at least 30 days';
            END IF;
            cutoff := now() - make_interval(days => retention_days);
            IF dry_run THEN
                SELECT count(*) INTO n_answers FROM answer_audit_logs WHERE created_at < cutoff;
                SELECT count(*) INTO n_queries FROM query_audit_logs WHERE created_at < cutoff;
                SELECT count(*) INTO n_events FROM access_events WHERE created_at < cutoff;
                RETURN QUERY SELECT n_queries, n_answers, n_events;
                RETURN;
            END IF;
            PERFORM set_config('app.audit_purge', 'on', true);
            DELETE FROM answer_audit_logs WHERE created_at < cutoff OR query_audit_id IN (SELECT id FROM query_audit_logs WHERE created_at < cutoff);
            GET DIAGNOSTICS n_answers = ROW_COUNT;
            DELETE FROM query_audit_logs WHERE created_at < cutoff;
            GET DIAGNOSTICS n_queries = ROW_COUNT;
            DELETE FROM access_events WHERE created_at < cutoff;
            GET DIAGNOSTICS n_events = ROW_COUNT;
            PERFORM set_config('app.audit_purge', 'off', true);
            IF n_answers + n_queries + n_events > 0 THEN
                INSERT INTO access_events (event, detail)
                VALUES ('audit.purge', jsonb_build_object('queries', n_queries, 'answers', n_answers, 'events', n_events, 'older_than_days', retention_days));
            END IF;
            RETURN QUERY SELECT n_queries, n_answers, n_events;
        END $$
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION audit_purge(integer, boolean)")
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'audit rows are append-only (% on %)', TG_OP, TG_TABLE_NAME; END $$
    """)
