from __future__ import annotations

import warnings
from pathlib import Path

from sqlalchemy import inspect, text
from sqlmodel import SQLModel

from .settings import settings


def run_alembic_migrations(*, database_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[1]
    alembic_ini = backend_dir / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def stamp_alembic_revision(*, database_url: str, revision: str) -> None:
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[1]
    alembic_ini = backend_dir / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.stamp(config, revision)


def has_user_tables(*, engine) -> bool:
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
    return bool(table_names - {"alembic_version"})


def has_alembic_version_table(*, engine) -> bool:
    with engine.begin() as connection:
        inspector = inspect(connection)
        return "alembic_version" in set(inspector.get_table_names())


def get_alembic_revision(*, engine) -> str | None:
    if not has_alembic_version_table(engine=engine):
        return None
    with engine.begin() as connection:
        row = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
    return str(row[0]) if row else None


def bootstrap_legacy_database_for_alembic(*, engine, database_url: str) -> None:
    if not has_user_tables(engine=engine) or has_alembic_version_table(engine=engine):
        return
    stamp_alembic_revision(database_url=database_url, revision="20260531_000001")


def add_column_if_missing(*, engine, table_name: str, column_name: str, ddl: str) -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if column_name not in columns:
            connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def backfill_null(*, engine, table_name: str, column_name: str, replacement_sql: str) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            f"UPDATE {table_name} SET {column_name} = {replacement_sql} WHERE {column_name} IS NULL"
        )


def run_lightweight_migrations(*, engine) -> None:
    warnings.warn(
        "DATABASE_MIGRATION_MODE=lightweight is deprecated and kept only for emergency legacy fallback. Prefer hybrid or alembic.",
        DeprecationWarning,
        stacklevel=2,
    )
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
    for table_name, column_name, ddl in column_migrations:
        add_column_if_missing(engine=engine, table_name=table_name, column_name=column_name, ddl=ddl)

    backfill_null(engine=engine, table_name="evidencecard", column_name="extracted_at", replacement_sql="CURRENT_TIMESTAMP")
    backfill_null(engine=engine, table_name="sourcepaper", column_name="ingested_at", replacement_sql="CURRENT_TIMESTAMP")
    backfill_null(engine=engine, table_name="sourcepaper", column_name="source_updated_at", replacement_sql="CURRENT_TIMESTAMP")
    add_column_if_missing(engine=engine, table_name="topicnote", column_name="sections_json", ddl="sections_json TEXT DEFAULT '[]'")
    add_column_if_missing(engine=engine, table_name="topicnote", column_name="metadata_json", ddl="metadata_json TEXT DEFAULT '{}'")
    add_column_if_missing(engine=engine, table_name="projectpaper", column_name="extraction_state", ddl="extraction_state TEXT DEFAULT 'not_started'")
    add_column_if_missing(engine=engine, table_name="projectpaper", column_name="extracted_fingerprint", ddl="extracted_fingerprint TEXT DEFAULT ''")
    add_column_if_missing(engine=engine, table_name="projectpaper", column_name="last_extracted_at", ddl="last_extracted_at DATETIME")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="run_type", ddl="run_type TEXT DEFAULT 'generic'")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="provider", ddl="provider TEXT DEFAULT ''")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="error_message", ddl="error_message TEXT DEFAULT ''")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="current_step", ddl="current_step TEXT DEFAULT ''")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="progress_message", ddl="progress_message TEXT DEFAULT ''")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="total_steps", ddl="total_steps INTEGER DEFAULT 0")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="completed_steps", ddl="completed_steps INTEGER DEFAULT 0")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="papers_found", ddl="papers_found INTEGER DEFAULT 0")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="papers_added", ddl="papers_added INTEGER DEFAULT 0")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="evidence_created", ddl="evidence_created INTEGER DEFAULT 0")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="affected_sections_count", ddl="affected_sections_count INTEGER DEFAULT 0")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="started_at", ddl="started_at DATETIME")
    add_column_if_missing(engine=engine, table_name="updaterun", column_name="finished_at", ddl="finished_at DATETIME")
    backfill_null(engine=engine, table_name="updaterun", column_name="started_at", replacement_sql="created_at")
