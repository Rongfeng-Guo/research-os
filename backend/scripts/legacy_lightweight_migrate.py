from __future__ import annotations

import argparse
import json
import sys
import warnings
import logging
from dataclasses import dataclass

from app.db import engine
from sqlmodel import SQLModel

from app.migration_bootstrap import add_column_if_missing, backfill_null

logger = logging.getLogger(__name__)


@dataclass
class LegacyMigrationSummary:
    created_schema: bool
    attempted_add_columns: int
    attempted_backfills: int
    dry_run: bool


def run_legacy_lightweight_migrations(*, dry_run: bool = False) -> LegacyMigrationSummary:
    logger.warning(
        "Running deprecated legacy lightweight migration script. Use only for temporary emergency recovery."
    )
    warnings.warn(
        "Legacy lightweight migration script is deprecated and kept only for emergency fallback. Prefer Alembic-managed recovery.",
        DeprecationWarning,
        stacklevel=2,
    )
    if not dry_run:
        SQLModel.metadata.create_all(engine)
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
        ("sourcepaper", "content_fingerprint", "content_fingerprint TEXT DEFAULT ''"),
        ("sourcepaper", "ingested_at", "ingested_at DATETIME"),
        ("sourcepaper", "source_updated_at", "source_updated_at DATETIME"),
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
        ("topicnoteversion", "version_kind", "version_kind TEXT DEFAULT 'snapshot'"),
        ("topicnoteversion", "source_suggestion_ids_json", "source_suggestion_ids_json TEXT DEFAULT '[]'"),
        ("noteupdatesuggestion", "diff_payload_json", "diff_payload_json TEXT DEFAULT '{}'"),
        ("noteupdatesuggestion", "applied_at", "applied_at DATETIME"),
        ("noteupdatesuggestion", "applied_by", "applied_by TEXT DEFAULT ''"),
    ]
    if not dry_run:
        for table_name, column_name, ddl in column_migrations:
            add_column_if_missing(engine=engine, table_name=table_name, column_name=column_name, ddl=ddl)

    additional_columns = [
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
    ]
    if not dry_run:
        for table_name, column_name, ddl in additional_columns:
            add_column_if_missing(engine=engine, table_name=table_name, column_name=column_name, ddl=ddl)

        backfill_null(engine=engine, table_name="evidencecard", column_name="extracted_at", replacement_sql="CURRENT_TIMESTAMP")
        backfill_null(engine=engine, table_name="sourcepaper", column_name="ingested_at", replacement_sql="CURRENT_TIMESTAMP")
        backfill_null(engine=engine, table_name="sourcepaper", column_name="source_updated_at", replacement_sql="CURRENT_TIMESTAMP")
        backfill_null(engine=engine, table_name="updaterun", column_name="started_at", replacement_sql="created_at")

    return LegacyMigrationSummary(
        created_schema=not dry_run,
        attempted_add_columns=len(column_migrations) + len(additional_columns),
        attempted_backfills=4,
        dry_run=dry_run,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the deprecated legacy lightweight migration path against the configured database."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required. Acknowledge that this deprecated path is only for emergency legacy recovery.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned legacy migration actions without modifying the database.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the execution summary as JSON.",
    )
    args = parser.parse_args()

    if not args.confirm:
        print(
            "Refusing to run legacy lightweight migrations without --confirm. "
            "Prefer Alembic-managed modes and only use this for emergency legacy recovery.",
            file=sys.stderr,
        )
        return 2

    summary = run_legacy_lightweight_migrations(dry_run=args.dry_run)
    if args.dry_run:
        if args.json:
            print(json.dumps(summary.__dict__, indent=2), file=sys.stdout)
        else:
            print(
                f"Dry run complete. Would attempt {summary.attempted_add_columns} column additions and "
                f"{summary.attempted_backfills} null backfills.",
                file=sys.stdout,
            )
        return 0

    if args.json:
        print(json.dumps(summary.__dict__, indent=2), file=sys.stdout)
    else:
        print(
            f"Legacy lightweight migration path completed. Attempted {summary.attempted_add_columns} column additions "
            f"and {summary.attempted_backfills} null backfills.",
            file=sys.stdout,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
