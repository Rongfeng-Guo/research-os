from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from .time_utils import utc_now


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=utc_now)


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(index=True)
    title: str
    topic: str
    description: str = ""
    auto_refresh_enabled: bool = False
    refresh_cadence: str = "manual_only"
    digest_enabled: bool = True
    knowledge_status: str = "idle"
    last_refreshed_at: Optional[datetime] = None
    next_refresh_due_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SearchRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    query: str
    provider: str = "mock"
    status: str = "completed"
    error_message: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class SourcePaper(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True)
    title: str
    abstract: str
    authors: str = ""
    year: int = 2025
    source: str = "mock"
    url: str = ""
    content_text: str = ""
    content_type: str = "abstract"
    source_type: str = "paper"
    origin: str = "search"
    ingestion_status: str = "completed"
    pdf_status: str = "pending"
    extraction_status: str = "pending"
    extraction_error: str = ""
    content_fingerprint: str = ""
    ingested_at: datetime = Field(default_factory=utc_now)
    source_updated_at: datetime = Field(default_factory=utc_now)
    source_metadata: str = "{}"
    created_at: datetime = Field(default_factory=utc_now)


class ProjectPaper(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    paper_id: int = Field(index=True)
    extraction_state: str = "not_started"
    extracted_fingerprint: str = ""
    last_extracted_at: Optional[datetime] = None
    added_at: datetime = Field(default_factory=utc_now)


class EvidenceCard(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    paper_id: int = Field(index=True)
    card_type: str
    title: str
    content: str
    source_title: str = ""
    source_excerpt: str = ""
    source_url: str = ""
    source_chunk_id: str = ""
    source_section: str = ""
    snippet_start: Optional[int] = None
    snippet_end: Optional[int] = None
    confidence_score: float = 0.0
    provider_name: str = "mock"
    review_status: str = "suggested"
    evidence_fingerprint: str = ""
    is_stale: bool = False
    is_pinned: bool = False
    pinned_at: Optional[datetime] = None
    user_note: str = ""
    edited_at: Optional[datetime] = None
    edited_by: str = ""
    edit_snapshot_json: str = "{}"
    extraction_run_id: Optional[int] = Field(default=None, index=True)
    extracted_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)


class TopicNote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, unique=True)
    title: str
    markdown: str
    sections_json: str = "[]"
    metadata_json: str = "{}"
    updated_at: datetime = Field(default_factory=utc_now)

    def section_list(self) -> list[dict]:
        try:
            return json.loads(self.sections_json or "[]")
        except json.JSONDecodeError:
            return []


class TopicNoteVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    note_id: int = Field(index=True)
    project_id: int = Field(index=True)
    version_number: int
    markdown: str
    metadata_json: str = "{}"
    version_kind: str = "snapshot"
    source_suggestion_ids_json: str = "[]"
    update_run_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class UpdateRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    status: str = "pending"
    run_type: str = "generic"
    trigger_type: str = "manual"
    provider: str = ""
    summary: str = ""
    error_message: str = ""
    current_step: str = ""
    progress_message: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    papers_found: int = 0
    papers_added: int = 0
    evidence_created: int = 0
    affected_sections_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: Optional[datetime] = None


class NoteUpdateSuggestion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    note_id: Optional[int] = Field(default=None, index=True)
    update_run_id: int = Field(index=True)
    target_section: str
    suggestion_type: str = "revise"
    current_text: str = ""
    proposed_text: str
    rationale: str = ""
    supporting_evidence_ids_json: str = "[]"
    supporting_sources_json: str = "[]"
    diff_payload_json: str = "{}"
    status: str = "suggested"
    created_at: datetime = Field(default_factory=utc_now)
    reviewed_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    applied_by: str = ""


class WorkspaceDigest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, index=True)
    period_start: datetime
    period_end: datetime
    included_project_ids_json: str = "[]"
    summary_json: str = "{}"
    markdown: str
    metadata_json: str = "{}"
    delivery_status: str = "pending"
    delivery_target: str = ""
    delivery_message: str = ""
    delivered_at: Optional[datetime] = None
    generated_at: datetime = Field(default_factory=utc_now)
