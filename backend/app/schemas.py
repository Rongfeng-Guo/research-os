from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(ReadModel):
    access_token: str
    token_type: str = "bearer"
    user_email: str


class LoginRequest(ReadModel):
    email: str
    password: str


class RegisterRequest(ReadModel):
    email: str
    password: str


class ProjectCreate(ReadModel):
    title: str
    topic: str
    description: str = ""


class ProjectRead(ReadModel):
    id: int
    title: str
    topic: str
    description: str
    auto_refresh_enabled: bool = False
    refresh_cadence: str = "manual_only"
    digest_enabled: bool = True
    last_refreshed_at: Optional[datetime] = None
    next_refresh_due_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ProjectPreferencesUpdate(ReadModel):
    auto_refresh_enabled: Optional[bool] = None
    refresh_cadence: Optional[str] = None
    digest_enabled: Optional[bool] = None


class SnapshotImportRequest(ReadModel):
    snapshot: Dict[str, Any]
    title_suffix: str = " (Imported)"


class UpdateRunRead(ReadModel):
    id: int
    project_id: int
    status: str
    run_type: str
    trigger_type: str
    provider: str
    summary: str
    error_message: str
    current_step: str = ""
    progress_message: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    created_at: datetime
    started_at: datetime
    finished_at: Optional[datetime] = None
    papers_found: int = 0
    papers_added: int = 0
    evidence_created: int = 0
    affected_sections_count: int = 0


class PaperSearchRequest(ReadModel):
    query: str
    limit: int = 8


class PaperDetailRequest(ReadModel):
    external_id: str


class PaperReadRequest(ReadModel):
    external_id: str


class PaperCandidate(ReadModel):
    external_id: str
    title: str
    abstract: str
    authors: str
    year: int
    source: str
    url: str
    content_text: str = ""
    content_type: str = "abstract"
    source_type: str = "paper"
    origin: str = "search"
    ingestion_status: str = "completed"
    pdf_status: str = "pending"
    extraction_status: str = "pending"
    extraction_error: str = ""
    source_metadata: dict = {}


class LinkedProjectRef(ReadModel):
    id: int
    title: str


class PaperLibraryItem(PaperCandidate):
    id: int
    project_count: int = 0
    linked_projects: List[LinkedProjectRef] = []
    ingested_at: datetime
    source_updated_at: datetime
    created_at: datetime


class ProjectPaperRead(ReadModel):
    id: int
    external_id: str
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
    source_metadata: dict = {}


class AddPaperRequest(ReadModel):
    external_id: str
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
    source_metadata: dict = {}


class UploadTextRequest(ReadModel):
    text: str
    title: str = "Uploaded note"
    content_type: str = "text"
    authors: str = ""
    year: Optional[int] = None
    url: str = ""


class EvidenceCardRead(ReadModel):
    id: int
    project_id: int
    paper_id: int
    card_type: str
    title: str
    content: str
    source_title: str
    source_excerpt: str
    source_url: str
    source_chunk_id: str
    source_section: str
    snippet_start: Optional[int] = None
    snippet_end: Optional[int] = None
    confidence_score: float
    provider_name: str
    review_status: str
    is_pinned: bool = False
    pinned_at: Optional[datetime] = None
    user_note: str = ""
    edited_at: Optional[datetime] = None
    edited_by: str = ""
    extracted_at: datetime
    created_at: datetime


class EvidenceStatusUpdate(ReadModel):
    review_status: Optional[str] = None


class EvidenceCardUpdate(ReadModel):
    card_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    source_title: Optional[str] = None
    source_excerpt: Optional[str] = None
    source_section: Optional[str] = None
    confidence_score: Optional[float] = None
    review_status: Optional[str] = None
    is_pinned: Optional[bool] = None
    user_note: Optional[str] = None


class TopicNoteSectionRead(ReadModel):
    slug: str
    title: str
    content: str = ""
    evidence_count: Optional[int] = None
    is_locked: bool = False
    locked_at: Optional[datetime] = None
    lock_reason: str = ""
    edited_at: Optional[datetime] = None
    edited_by: str = ""
    last_manual_edit_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_update_source: str = ""


class TopicNoteRead(ReadModel):
    id: int
    project_id: int
    title: str
    markdown: str
    sections: List[TopicNoteSectionRead] = []
    metadata: dict = {}
    updated_at: datetime


class TopicNoteVersionRead(ReadModel):
    id: int
    note_id: int
    project_id: int
    version_number: int
    markdown: str
    metadata: dict = {}
    version_kind: str = "snapshot"
    source_suggestion_ids: List[int] = []
    update_run_id: Optional[int] = None
    created_at: datetime


class VersionComparisonRead(ReadModel):
    base_version_id: int
    compare_version_id: int
    diff: dict = {}


class NoteUpdateSuggestionRead(ReadModel):
    id: int
    project_id: int
    note_id: Optional[int] = None
    update_run_id: int
    target_section: str
    suggestion_type: str
    current_text: str
    proposed_text: str
    rationale: str
    supporting_evidence_ids: List[int] = []
    supporting_sources: List[str] = []
    diff: dict = {}
    status: str
    target_section_title: str = ""
    target_section_locked: bool = False
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    applied_by: str = ""


class SuggestionStatusUpdate(ReadModel):
    status: str


class ApplySuggestionsRequest(ReadModel):
    generation_mode: str = "accepted_only"
    suggestion_ids: List[int] = []
    section_slug: Optional[str] = None


class NoteSectionUpdate(ReadModel):
    content: Optional[str] = None
    is_locked: Optional[bool] = None
    lock_reason: Optional[str] = None


class RecentNoteRead(ReadModel):
    project_id: int
    project_title: str
    title: str
    updated_at: datetime
    metadata: dict = {}


class DashboardSourceItem(ReadModel):
    project_id: int
    project_title: str
    paper_id: int
    title: str
    extraction_status: str
    ingestion_status: str
    updated_hint: str = ""


class DashboardSummary(ReadModel):
    recent_projects: List[ProjectRead]
    recent_notes: List[RecentNoteRead]
    recent_evidence: List[EvidenceCardRead]
    pending_sources: List[DashboardSourceItem]
    stale_projects: List[ProjectRead] = []
    pending_suggestions: List[dict] = []
    locked_attention: List[dict] = []
    recent_versions: List[dict] = []
    recommended_actions: List[dict] = []
    project_health: List[dict] = []
    counts: dict = {}


class ProjectHealthRead(ReadModel):
    project_id: int
    freshness_status: str
    freshness_reason: str
    pending_review_count: int = 0
    locked_attention_count: int = 0
    stale_note: bool = False
    last_activity_at: Optional[datetime] = None
    evidence_growth_week: int = 0
    note_version_count: int = 0
    latest_note_update_at: Optional[datetime] = None


class WorkspaceDigestRead(ReadModel):
    id: int
    period_start: datetime
    period_end: datetime
    included_project_ids: List[int] = []
    summary: dict = {}
    markdown: str
    metadata: dict = {}
    delivery_status: str = "pending"
    delivery_target: str = ""
    delivery_message: str = ""
    delivered_at: Optional[datetime] = None
    generated_at: datetime


class DigestDeliveryRequest(ReadModel):
    target: str


class DigestDeliveryRead(ReadModel):
    digest_id: int
    status: str
    target: str
    message: str = ""
    delivered_at: Optional[datetime] = None
    payload: dict = {}


class NoteExportRequest(ReadModel):
    target: str


class NoteExportRead(ReadModel):
    project_id: int
    note_id: int
    status: str
    target: str
    message: str = ""
    payload: dict = {}


class ProjectDetail(ReadModel):
    project: ProjectRead
    papers: List[ProjectPaperRead]
    evidence_cards: List[EvidenceCardRead]
    topic_note: Optional[TopicNoteRead]
    health: Optional[ProjectHealthRead] = None
    update_runs: List[UpdateRunRead] = []
    note_update_suggestions: List[NoteUpdateSuggestionRead] = []
    note_versions: List[TopicNoteVersionRead] = []
