"""finalize legacy runtime columns

Revision ID: 20260531_000002
Revises: 20260531_000001
Create Date: 2026-05-31 18:05:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260531_000002"
down_revision = "20260531_000001"
branch_labels = None
depends_on = None


def _add_column_if_missing(table_name: str, column_name: str, ddl: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name not in columns:
        bind.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def _backfill_null(table_name: str, column_name: str, replacement_sql: str) -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        f"UPDATE {table_name} SET {column_name} = {replacement_sql} WHERE {column_name} IS NULL"
    )


def upgrade() -> None:
    column_migrations = [
        ("searchrun", "provider", "provider TEXT DEFAULT 'mock'"),
        ("searchrun", "status", "status TEXT DEFAULT 'completed'"),
        ("searchrun", "error_message", "error_message TEXT DEFAULT ''"),
        ("sourcepaper", "content_text", "content_text TEXT DEFAULT ''"),
        ("sourcepaper", "content_type", "content_type TEXT DEFAULT 'abstract'"),
        ("sourcepaper", "source_type", "source_type TEXT DEFAULT 'paper'"),
        ("sourcepaper", "origin", "origin TEXT DEFAULT 'search'"),
        ("sourcepaper", "ingestion_status", "ingestion_status TEXT DEFAULT 'completed'"),
        ("sourcepaper", "pdf_status", "pdf_status TEXT DEFAULT 'pending'"),
        ("sourcepaper", "extraction_status", "extraction_status TEXT DEFAULT 'pending'"),
        ("sourcepaper", "extraction_error", "extraction_error TEXT DEFAULT ''"),
        ("sourcepaper", "source_metadata", "source_metadata TEXT DEFAULT '{}'"),
        ("sourcepaper", "content_fingerprint", "content_fingerprint TEXT DEFAULT ''"),
        ("sourcepaper", "ingested_at", "ingested_at DATETIME"),
        ("sourcepaper", "source_updated_at", "source_updated_at DATETIME"),
        ("project", "auto_refresh_enabled", "auto_refresh_enabled BOOLEAN DEFAULT 0"),
        ("project", "refresh_cadence", "refresh_cadence TEXT DEFAULT 'manual_only'"),
        ("project", "digest_enabled", "digest_enabled BOOLEAN DEFAULT 1"),
        ("project", "knowledge_status", "knowledge_status TEXT DEFAULT 'idle'"),
        ("project", "last_refreshed_at", "last_refreshed_at DATETIME"),
        ("project", "next_refresh_due_at", "next_refresh_due_at DATETIME"),
        ("workspacedigest", "owner_id", "owner_id INTEGER"),
        ("workspacedigest", "delivery_status", "delivery_status TEXT DEFAULT 'pending'"),
        ("workspacedigest", "delivery_target", "delivery_target TEXT DEFAULT ''"),
        ("workspacedigest", "delivery_message", "delivery_message TEXT DEFAULT ''"),
        ("workspacedigest", "delivered_at", "delivered_at DATETIME"),
        ("evidencecard", "source_title", "source_title TEXT DEFAULT ''"),
        ("evidencecard", "source_excerpt", "source_excerpt TEXT DEFAULT ''"),
        ("evidencecard", "source_url", "source_url TEXT DEFAULT ''"),
        ("evidencecard", "source_chunk_id", "source_chunk_id TEXT DEFAULT ''"),
        ("evidencecard", "source_section", "source_section TEXT DEFAULT ''"),
        ("evidencecard", "snippet_start", "snippet_start INTEGER"),
        ("evidencecard", "snippet_end", "snippet_end INTEGER"),
        ("evidencecard", "confidence_score", "confidence_score REAL DEFAULT 0"),
        ("evidencecard", "provider_name", "provider_name TEXT DEFAULT 'mock'"),
        ("evidencecard", "review_status", "review_status TEXT DEFAULT 'suggested'"),
        ("evidencecard", "evidence_fingerprint", "evidence_fingerprint TEXT DEFAULT ''"),
        ("evidencecard", "is_stale", "is_stale BOOLEAN DEFAULT 0"),
        ("evidencecard", "is_pinned", "is_pinned BOOLEAN DEFAULT 0"),
        ("evidencecard", "pinned_at", "pinned_at DATETIME"),
        ("evidencecard", "user_note", "user_note TEXT DEFAULT ''"),
        ("evidencecard", "edited_at", "edited_at DATETIME"),
        ("evidencecard", "edited_by", "edited_by TEXT DEFAULT ''"),
        ("evidencecard", "edit_snapshot_json", "edit_snapshot_json TEXT DEFAULT '{}'"),
        ("evidencecard", "extraction_run_id", "extraction_run_id INTEGER"),
        ("evidencecard", "extracted_at", "extracted_at DATETIME"),
        ("topicnote", "sections_json", "sections_json TEXT DEFAULT '[]'"),
        ("topicnote", "metadata_json", "metadata_json TEXT DEFAULT '{}'"),
        ("projectpaper", "extraction_state", "extraction_state TEXT DEFAULT 'not_started'"),
        ("projectpaper", "extracted_fingerprint", "extracted_fingerprint TEXT DEFAULT ''"),
        ("projectpaper", "last_extracted_at", "last_extracted_at DATETIME"),
        ("updaterun", "run_type", "run_type TEXT DEFAULT 'generic'"),
        ("updaterun", "provider", "provider TEXT DEFAULT ''"),
        ("updaterun", "error_message", "error_message TEXT DEFAULT ''"),
        ("updaterun", "current_step", "current_step TEXT DEFAULT ''"),
        ("updaterun", "progress_message", "progress_message TEXT DEFAULT ''"),
        ("updaterun", "total_steps", "total_steps INTEGER DEFAULT 0"),
        ("updaterun", "completed_steps", "completed_steps INTEGER DEFAULT 0"),
        ("updaterun", "papers_found", "papers_found INTEGER DEFAULT 0"),
        ("updaterun", "papers_added", "papers_added INTEGER DEFAULT 0"),
        ("updaterun", "evidence_created", "evidence_created INTEGER DEFAULT 0"),
        ("updaterun", "affected_sections_count", "affected_sections_count INTEGER DEFAULT 0"),
        ("updaterun", "started_at", "started_at DATETIME"),
        ("updaterun", "finished_at", "finished_at DATETIME"),
        ("topicnoteversion", "version_kind", "version_kind TEXT DEFAULT 'snapshot'"),
        ("topicnoteversion", "source_suggestion_ids_json", "source_suggestion_ids_json TEXT DEFAULT '[]'"),
        ("noteupdatesuggestion", "diff_payload_json", "diff_payload_json TEXT DEFAULT '{}'"),
        ("noteupdatesuggestion", "applied_at", "applied_at DATETIME"),
        ("noteupdatesuggestion", "applied_by", "applied_by TEXT DEFAULT ''"),
    ]
    for table_name, column_name, ddl in column_migrations:
        _add_column_if_missing(table_name, column_name, ddl)

    _backfill_null("evidencecard", "extracted_at", "CURRENT_TIMESTAMP")
    _backfill_null("sourcepaper", "ingested_at", "CURRENT_TIMESTAMP")
    _backfill_null("sourcepaper", "source_updated_at", "CURRENT_TIMESTAMP")
    _backfill_null("updaterun", "started_at", "created_at")


def downgrade() -> None:
    pass
