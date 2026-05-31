"""initial schema

Revision ID: 20260531_000001
Revises: 
Create Date: 2026-05-31 17:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260531_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=False)

    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("auto_refresh_enabled", sa.Boolean(), nullable=False),
        sa.Column("refresh_cadence", sa.String(), nullable=False),
        sa.Column("digest_enabled", sa.Boolean(), nullable=False),
        sa.Column("knowledge_status", sa.String(), nullable=False),
        sa.Column("last_refreshed_at", sa.DateTime(), nullable=True),
        sa.Column("next_refresh_due_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_owner_id"), "project", ["owner_id"], unique=False)

    op.create_table(
        "searchrun",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("query", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_searchrun_project_id"), "searchrun", ["project_id"], unique=False)

    op.create_table(
        "sourcepaper",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("abstract", sa.String(), nullable=False),
        sa.Column("authors", sa.String(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("content_text", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("ingestion_status", sa.String(), nullable=False),
        sa.Column("pdf_status", sa.String(), nullable=False),
        sa.Column("extraction_status", sa.String(), nullable=False),
        sa.Column("extraction_error", sa.String(), nullable=False),
        sa.Column("content_fingerprint", sa.String(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(), nullable=False),
        sa.Column("source_metadata", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sourcepaper_external_id"), "sourcepaper", ["external_id"], unique=False)

    op.create_table(
        "projectpaper",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("extraction_state", sa.String(), nullable=False),
        sa.Column("extracted_fingerprint", sa.String(), nullable=False),
        sa.Column("last_extracted_at", sa.DateTime(), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projectpaper_project_id"), "projectpaper", ["project_id"], unique=False)
    op.create_index(op.f("ix_projectpaper_paper_id"), "projectpaper", ["paper_id"], unique=False)

    op.create_table(
        "updaterun",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("run_type", sa.String(), nullable=False),
        sa.Column("trigger_type", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=False),
        sa.Column("current_step", sa.String(), nullable=False),
        sa.Column("progress_message", sa.String(), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False),
        sa.Column("completed_steps", sa.Integer(), nullable=False),
        sa.Column("papers_found", sa.Integer(), nullable=False),
        sa.Column("papers_added", sa.Integer(), nullable=False),
        sa.Column("evidence_created", sa.Integer(), nullable=False),
        sa.Column("affected_sections_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_updaterun_project_id"), "updaterun", ["project_id"], unique=False)

    op.create_table(
        "evidencecard",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("card_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("source_title", sa.String(), nullable=False),
        sa.Column("source_excerpt", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("source_chunk_id", sa.String(), nullable=False),
        sa.Column("source_section", sa.String(), nullable=False),
        sa.Column("snippet_start", sa.Integer(), nullable=True),
        sa.Column("snippet_end", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("provider_name", sa.String(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(), nullable=False),
        sa.Column("is_stale", sa.Boolean(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("pinned_at", sa.DateTime(), nullable=True),
        sa.Column("user_note", sa.String(), nullable=False),
        sa.Column("edited_at", sa.DateTime(), nullable=True),
        sa.Column("edited_by", sa.String(), nullable=False),
        sa.Column("edit_snapshot_json", sa.String(), nullable=False),
        sa.Column("extraction_run_id", sa.Integer(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evidencecard_project_id"), "evidencecard", ["project_id"], unique=False)
    op.create_index(op.f("ix_evidencecard_paper_id"), "evidencecard", ["paper_id"], unique=False)
    op.create_index(op.f("ix_evidencecard_extraction_run_id"), "evidencecard", ["extraction_run_id"], unique=False)

    op.create_table(
        "topicnote",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("markdown", sa.String(), nullable=False),
        sa.Column("sections_json", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )
    op.create_index(op.f("ix_topicnote_project_id"), "topicnote", ["project_id"], unique=True)

    op.create_table(
        "topicnoteversion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("markdown", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.String(), nullable=False),
        sa.Column("version_kind", sa.String(), nullable=False),
        sa.Column("source_suggestion_ids_json", sa.String(), nullable=False),
        sa.Column("update_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topicnoteversion_note_id"), "topicnoteversion", ["note_id"], unique=False)
    op.create_index(op.f("ix_topicnoteversion_project_id"), "topicnoteversion", ["project_id"], unique=False)
    op.create_index(op.f("ix_topicnoteversion_update_run_id"), "topicnoteversion", ["update_run_id"], unique=False)

    op.create_table(
        "noteupdatesuggestion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=True),
        sa.Column("update_run_id", sa.Integer(), nullable=False),
        sa.Column("target_section", sa.String(), nullable=False),
        sa.Column("suggestion_type", sa.String(), nullable=False),
        sa.Column("current_text", sa.String(), nullable=False),
        sa.Column("proposed_text", sa.String(), nullable=False),
        sa.Column("rationale", sa.String(), nullable=False),
        sa.Column("supporting_evidence_ids_json", sa.String(), nullable=False),
        sa.Column("supporting_sources_json", sa.String(), nullable=False),
        sa.Column("diff_payload_json", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("applied_by", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_noteupdatesuggestion_project_id"), "noteupdatesuggestion", ["project_id"], unique=False)
    op.create_index(op.f("ix_noteupdatesuggestion_note_id"), "noteupdatesuggestion", ["note_id"], unique=False)
    op.create_index(op.f("ix_noteupdatesuggestion_update_run_id"), "noteupdatesuggestion", ["update_run_id"], unique=False)

    op.create_table(
        "workspacedigest",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("included_project_ids_json", sa.String(), nullable=False),
        sa.Column("summary_json", sa.String(), nullable=False),
        sa.Column("markdown", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.String(), nullable=False),
        sa.Column("delivery_status", sa.String(), nullable=False),
        sa.Column("delivery_target", sa.String(), nullable=False),
        sa.Column("delivery_message", sa.String(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspacedigest_owner_id"), "workspacedigest", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workspacedigest_owner_id"), table_name="workspacedigest")
    op.drop_table("workspacedigest")
    op.drop_index(op.f("ix_noteupdatesuggestion_update_run_id"), table_name="noteupdatesuggestion")
    op.drop_index(op.f("ix_noteupdatesuggestion_note_id"), table_name="noteupdatesuggestion")
    op.drop_index(op.f("ix_noteupdatesuggestion_project_id"), table_name="noteupdatesuggestion")
    op.drop_table("noteupdatesuggestion")
    op.drop_index(op.f("ix_topicnoteversion_update_run_id"), table_name="topicnoteversion")
    op.drop_index(op.f("ix_topicnoteversion_project_id"), table_name="topicnoteversion")
    op.drop_index(op.f("ix_topicnoteversion_note_id"), table_name="topicnoteversion")
    op.drop_table("topicnoteversion")
    op.drop_index(op.f("ix_topicnote_project_id"), table_name="topicnote")
    op.drop_table("topicnote")
    op.drop_index(op.f("ix_evidencecard_extraction_run_id"), table_name="evidencecard")
    op.drop_index(op.f("ix_evidencecard_paper_id"), table_name="evidencecard")
    op.drop_index(op.f("ix_evidencecard_project_id"), table_name="evidencecard")
    op.drop_table("evidencecard")
    op.drop_index(op.f("ix_updaterun_project_id"), table_name="updaterun")
    op.drop_table("updaterun")
    op.drop_index(op.f("ix_projectpaper_paper_id"), table_name="projectpaper")
    op.drop_index(op.f("ix_projectpaper_project_id"), table_name="projectpaper")
    op.drop_table("projectpaper")
    op.drop_index(op.f("ix_sourcepaper_external_id"), table_name="sourcepaper")
    op.drop_table("sourcepaper")
    op.drop_index(op.f("ix_searchrun_project_id"), table_name="searchrun")
    op.drop_table("searchrun")
    op.drop_index(op.f("ix_project_owner_id"), table_name="project")
    op.drop_table("project")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
