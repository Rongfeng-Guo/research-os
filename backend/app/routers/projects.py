import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from ..db import engine, get_session
from ..auth import get_current_user
from ..models import NoteUpdateSuggestion, Project, ProjectPaper, SourcePaper, EvidenceCard, TopicNote, TopicNoteVersion, User
from ..schemas import (
    NoteUpdateSuggestionRead,
    TopicNoteVersionRead,
    UpdateRunRead,
    EvidenceCardRead,
    ProjectCreate,
    ProjectDetail,
    SnapshotImportRequest,
    ProjectHealthRead,
    ProjectPreferencesUpdate,
    ProjectPaperRead,
    ProjectRead,
    TopicNoteRead,
    TopicNoteSectionRead,
)
from ..models import UpdateRun
from ..services.refresh_workflow import run_project_refresh, run_project_refresh_job
from ..services.project_health import compute_project_health, ensure_refresh_schedule
from ..services.note_sections import normalize_note_sections
from ..services.note_versions import version_to_read
from ..services.update_runs import create_update_run
from ..services.update_suggestions import suggestion_to_read
from ..time_utils import utc_now

router = APIRouter(prefix="/projects", tags=["projects"])


def _parse_source_metadata(raw: str) -> dict:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}


def _evidence_card_to_read(card: EvidenceCard) -> EvidenceCardRead:
    return EvidenceCardRead(
        id=card.id,
        project_id=card.project_id,
        paper_id=card.paper_id,
        card_type=card.card_type,
        title=card.title,
        content=card.content,
        source_title=card.source_title or "",
        source_excerpt=card.source_excerpt or "",
        source_url=card.source_url or "",
        source_chunk_id=card.source_chunk_id or "",
        source_section=card.source_section or "",
        snippet_start=card.snippet_start,
        snippet_end=card.snippet_end,
        confidence_score=card.confidence_score or 0.0,
        provider_name=card.provider_name or "unknown",
        review_status=card.review_status or "suggested",
        is_pinned=bool(card.is_pinned),
        pinned_at=card.pinned_at,
        user_note=card.user_note or "",
        edited_at=card.edited_at,
        edited_by=card.edited_by or "",
        extracted_at=card.extracted_at or card.created_at,
        created_at=card.created_at,
    )


def _run_to_read(run: UpdateRun) -> UpdateRunRead:
    return UpdateRunRead.model_validate(run)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _refresh_project_task(project_id: int, run_id: int) -> None:
    with Session(engine) as session:
        project = session.get(Project, project_id)
        run = session.get(UpdateRun, run_id)
        if not project or not run:
            return

        try:
            run_project_refresh_job(session, project=project, run=run)
        except Exception:
            return


@router.get("", response_model=List[ProjectRead])
def list_projects(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    projects = session.exec(select(Project).where(Project.owner_id == current_user.id)).all()
    return projects


@router.post("", response_model=ProjectRead)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = Project(
        owner_id=current_user.id,
        title=payload.title,
        topic=payload.topic,
        description=payload.description,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.post("/import", response_model=ProjectRead)
def import_project_snapshot(
    payload: SnapshotImportRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    snapshot = payload.snapshot or {}
    project_payload = snapshot.get("project")
    if not isinstance(project_payload, dict):
        raise HTTPException(status_code=400, detail="Snapshot is missing a valid project object")

    title = (project_payload.get("title") or "Imported project").strip()
    topic = (project_payload.get("topic") or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Snapshot project is missing a topic")

    imported_project = Project(
        owner_id=current_user.id,
        title=f"{title}{payload.title_suffix}" if payload.title_suffix else title,
        topic=topic,
        description=project_payload.get("description") or "",
        auto_refresh_enabled=bool(project_payload.get("auto_refresh_enabled", False)),
        refresh_cadence=project_payload.get("refresh_cadence") or "manual_only",
        digest_enabled=bool(project_payload.get("digest_enabled", True)),
        last_refreshed_at=_parse_dt(project_payload.get("last_refreshed_at")),
        next_refresh_due_at=_parse_dt(project_payload.get("next_refresh_due_at")),
    )
    session.add(imported_project)
    session.commit()
    session.refresh(imported_project)

    paper_id_map: dict[int, int] = {}
    for raw_paper in snapshot.get("papers", []):
        if not isinstance(raw_paper, dict):
            continue
        metadata = raw_paper.get("source_metadata", {})
        restored_paper = SourcePaper(
            external_id=f"{raw_paper.get('external_id') or 'imported-paper'}-import-{imported_project.id}-{len(paper_id_map) + 1}",
            title=raw_paper.get("title") or "Imported source",
            abstract=raw_paper.get("abstract") or "",
            authors=raw_paper.get("authors") or "",
            year=raw_paper.get("year") or datetime.now().year,
            source=raw_paper.get("source") or "import",
            url=raw_paper.get("url") or "",
            content_text=raw_paper.get("content_text") or "",
            content_type=raw_paper.get("content_type") or "abstract",
            source_type=raw_paper.get("source_type") or "paper",
            origin="import_snapshot",
            ingestion_status=raw_paper.get("ingestion_status") or "completed",
            pdf_status=raw_paper.get("pdf_status") or "pending",
            extraction_status=raw_paper.get("extraction_status") or "pending",
            extraction_error=raw_paper.get("extraction_error") or "",
            source_metadata=json.dumps(metadata if isinstance(metadata, dict) else {}),
            ingested_at=_parse_dt(raw_paper.get("ingested_at")) or utc_now(),
            source_updated_at=_parse_dt(raw_paper.get("source_updated_at")) or utc_now(),
        )
        session.add(restored_paper)
        session.commit()
        session.refresh(restored_paper)
        session.add(ProjectPaper(project_id=imported_project.id, paper_id=restored_paper.id))
        session.commit()
        if raw_paper.get("id") is not None:
            paper_id_map[int(raw_paper["id"])] = restored_paper.id

    for raw_card in snapshot.get("evidence_cards", []):
        if not isinstance(raw_card, dict):
            continue
        restored_card = EvidenceCard(
            project_id=imported_project.id,
            paper_id=paper_id_map.get(raw_card.get("paper_id"), next(iter(paper_id_map.values()), 0)),
            card_type=raw_card.get("card_type") or "claim",
            title=raw_card.get("title") or "Imported evidence",
            content=raw_card.get("content") or "",
            source_title=raw_card.get("source_title") or "",
            source_excerpt=raw_card.get("source_excerpt") or "",
            source_url=raw_card.get("source_url") or "",
            source_chunk_id=raw_card.get("source_chunk_id") or "",
            source_section=raw_card.get("source_section") or "",
            snippet_start=raw_card.get("snippet_start"),
            snippet_end=raw_card.get("snippet_end"),
            confidence_score=raw_card.get("confidence_score") or 0.0,
            provider_name=raw_card.get("provider_name") or "import",
            review_status=raw_card.get("review_status") or "suggested",
            is_pinned=bool(raw_card.get("is_pinned", False)),
            pinned_at=_parse_dt(raw_card.get("pinned_at")),
            user_note=raw_card.get("user_note") or "",
            edited_at=_parse_dt(raw_card.get("edited_at")),
            edited_by=raw_card.get("edited_by") or "",
            extracted_at=_parse_dt(raw_card.get("extracted_at")) or utc_now(),
            created_at=_parse_dt(raw_card.get("created_at")) or utc_now(),
        )
        session.add(restored_card)
    session.commit()

    note_payload = snapshot.get("topic_note")
    note_id_map: dict[int, int] = {}
    if isinstance(note_payload, dict):
        metadata = note_payload.get("metadata", {})
        sections = note_payload.get("sections", [])
        restored_note = TopicNote(
            project_id=imported_project.id,
            title=note_payload.get("title") or f"{imported_project.title} Research Note",
            markdown=note_payload.get("markdown") or "",
            sections_json=json.dumps(sections if isinstance(sections, list) else []),
            metadata_json=json.dumps(metadata if isinstance(metadata, dict) else {}),
            updated_at=_parse_dt(note_payload.get("updated_at")) or utc_now(),
        )
        session.add(restored_note)
        session.commit()
        session.refresh(restored_note)
        if note_payload.get("id") is not None:
            note_id_map[int(note_payload["id"])] = restored_note.id

    run_id_map: dict[int, int] = {}
    for raw_run in snapshot.get("update_runs", []):
        if not isinstance(raw_run, dict):
            continue
        restored_run = UpdateRun(
            project_id=imported_project.id,
            status=raw_run.get("status") or "completed",
            run_type=raw_run.get("run_type") or "generic",
            trigger_type=raw_run.get("trigger_type") or "manual",
            provider=raw_run.get("provider") or "",
            summary=raw_run.get("summary") or "",
            error_message=raw_run.get("error_message") or "",
            current_step=raw_run.get("current_step") or "",
            progress_message=raw_run.get("progress_message") or "",
            total_steps=raw_run.get("total_steps") or 0,
            completed_steps=raw_run.get("completed_steps") or 0,
            papers_found=raw_run.get("papers_found") or 0,
            papers_added=raw_run.get("papers_added") or 0,
            evidence_created=raw_run.get("evidence_created") or 0,
            affected_sections_count=raw_run.get("affected_sections_count") or 0,
            created_at=_parse_dt(raw_run.get("created_at")) or utc_now(),
            started_at=_parse_dt(raw_run.get("started_at")) or utc_now(),
            finished_at=_parse_dt(raw_run.get("finished_at")),
        )
        session.add(restored_run)
        session.commit()
        session.refresh(restored_run)
        if raw_run.get("id") is not None:
            run_id_map[int(raw_run["id"])] = restored_run.id

    for raw_suggestion in snapshot.get("note_update_suggestions", []):
        if not isinstance(raw_suggestion, dict):
            continue
        restored_suggestion = NoteUpdateSuggestion(
            project_id=imported_project.id,
            note_id=note_id_map.get(raw_suggestion.get("note_id")),
            update_run_id=run_id_map.get(raw_suggestion.get("update_run_id"), 0),
            target_section=raw_suggestion.get("target_section") or "overview",
            suggestion_type=raw_suggestion.get("suggestion_type") or "revise",
            current_text=raw_suggestion.get("current_text") or "",
            proposed_text=raw_suggestion.get("proposed_text") or "",
            rationale=raw_suggestion.get("rationale") or "",
            supporting_evidence_ids_json=json.dumps(raw_suggestion.get("supporting_evidence_ids") or []),
            supporting_sources_json=json.dumps(raw_suggestion.get("supporting_sources") or []),
            diff_payload_json=json.dumps(raw_suggestion.get("diff") or {}),
            status=raw_suggestion.get("status") or "suggested",
            created_at=_parse_dt(raw_suggestion.get("created_at")) or utc_now(),
            reviewed_at=_parse_dt(raw_suggestion.get("reviewed_at")),
            applied_at=_parse_dt(raw_suggestion.get("applied_at")),
            applied_by=raw_suggestion.get("applied_by") or "",
        )
        session.add(restored_suggestion)
    session.commit()

    for raw_version in snapshot.get("note_versions", []):
        if not isinstance(raw_version, dict) or not note_id_map:
            continue
        restored_version = TopicNoteVersion(
            note_id=next(iter(note_id_map.values())),
            project_id=imported_project.id,
            version_number=raw_version.get("version_number") or 1,
            markdown=raw_version.get("markdown") or "",
            metadata_json=json.dumps(raw_version.get("metadata") or {}),
            version_kind=raw_version.get("version_kind") or "snapshot",
            source_suggestion_ids_json=json.dumps(raw_version.get("source_suggestion_ids") or []),
            update_run_id=run_id_map.get(raw_version.get("update_run_id")),
            created_at=_parse_dt(raw_version.get("created_at")) or utc_now(),
        )
        session.add(restored_version)
    session.commit()

    imported_project.updated_at = utc_now()
    session.add(imported_project)
    session.commit()
    session.refresh(imported_project)
    return imported_project


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project_detail(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    ensure_refresh_schedule(project)

    joins = session.exec(select(ProjectPaper).where(ProjectPaper.project_id == project_id)).all()
    papers = []
    for join in joins:
        paper = session.get(SourcePaper, join.paper_id)
        if paper:
            source_metadata = _parse_source_metadata(paper.source_metadata)
            papers.append(
                ProjectPaperRead(
                    id=paper.id,
                    external_id=paper.external_id,
                    title=paper.title,
                    abstract=paper.abstract,
                    authors=paper.authors,
                    year=paper.year,
                    source=paper.source,
                    url=paper.url,
                    content_text=paper.content_text,
                    content_type=paper.content_type,
                    source_type=paper.source_type,
                    origin=paper.origin,
                    ingestion_status=paper.ingestion_status,
                    pdf_status=paper.pdf_status,
                    extraction_status=paper.extraction_status,
                    extraction_error=paper.extraction_error,
                    source_metadata=source_metadata,
                )
            )

    cards = session.exec(select(EvidenceCard).where(EvidenceCard.project_id == project_id)).all()
    note = session.exec(select(TopicNote).where(TopicNote.project_id == project_id)).first()
    update_runs = session.exec(
        select(UpdateRun).where(UpdateRun.project_id == project_id).order_by(UpdateRun.created_at.desc())
    ).all()
    suggestions = session.exec(
        select(NoteUpdateSuggestion).where(NoteUpdateSuggestion.project_id == project_id).order_by(NoteUpdateSuggestion.created_at.desc())
    ).all()
    note_versions = session.exec(
        select(TopicNoteVersion).where(TopicNoteVersion.project_id == project_id).order_by(TopicNoteVersion.version_number.desc())
    ).all()
    health = compute_project_health(
        project,
        note=note,
        suggestions=suggestions,
        evidence_cards=cards,
        note_versions=note_versions,
        update_runs=update_runs,
    )

    return ProjectDetail(
        project=ProjectRead.model_validate(project),
        papers=papers,
        evidence_cards=[_evidence_card_to_read(card) for card in cards],
        topic_note=(
            TopicNoteRead(
                id=note.id,
                project_id=note.project_id,
                title=note.title,
                markdown=note.markdown,
                sections=[TopicNoteSectionRead(**section) for section in normalize_note_sections(note.markdown, note.sections_json)],
                metadata=json.loads(note.metadata_json or "{}"),
                updated_at=note.updated_at,
            )
            if note
            else None
        ),
        health=ProjectHealthRead(**health),
        update_runs=[UpdateRunRead.model_validate(run) for run in update_runs],
        note_update_suggestions=[
            NoteUpdateSuggestionRead(**suggestion_to_read(suggestion, note=note))
            for suggestion in suggestions
        ],
        note_versions=[
            TopicNoteVersionRead(**version_to_read(version))
            for version in note_versions
        ],
    )


@router.post("/{project_id}/refresh", response_model=ProjectDetail)
def refresh_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    run = create_update_run(
        session,
        project_id=project_id,
        run_type="project_refresh",
        trigger_type="manual",
        provider="paper_discovery+extraction",
        summary="Refreshing topic and checking for new papers",
        current_step="Searching for new papers",
        progress_message="Starting refresh workflow...",
        total_steps=3,
    )

    try:
        run_project_refresh_job(session, project=project, run=run)
    except Exception:
        pass

    session.refresh(project)
    return get_project_detail(project_id=project_id, current_user=current_user, session=session)


@router.post("/{project_id}/refresh/start", response_model=UpdateRunRead)
def start_refresh_project(
    project_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    running = session.exec(
        select(UpdateRun).where(
            UpdateRun.project_id == project_id,
            UpdateRun.run_type == "project_refresh",
            UpdateRun.status == "running",
        )
    ).first()
    if running:
        return _run_to_read(running)

    run = create_update_run(
        session,
        project_id=project_id,
        run_type="project_refresh",
        trigger_type="manual",
        provider="paper_discovery+extraction",
        summary="Refreshing topic and checking for new papers",
        current_step="Queued",
        progress_message="Refresh job has been scheduled.",
        total_steps=3,
    )
    background_tasks.add_task(_refresh_project_task, project_id, run.id)
    return _run_to_read(run)


@router.get("/{project_id}/runs/{run_id}", response_model=UpdateRunRead)
def get_project_run(
    project_id: int,
    run_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    run = session.get(UpdateRun, run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Update run not found")
    return _run_to_read(run)


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    project.title = payload.title
    project.topic = payload.topic
    project.description = payload.description
    project.updated_at = utc_now()
    ensure_refresh_schedule(project)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.patch("/{project_id}/preferences", response_model=ProjectRead)
def update_project_preferences(
    project_id: int,
    payload: ProjectPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.refresh_cadence and payload.refresh_cadence not in {"manual_only", "daily", "weekly", "custom"}:
        raise HTTPException(status_code=400, detail="Invalid refresh cadence")
    if payload.auto_refresh_enabled is not None:
        project.auto_refresh_enabled = payload.auto_refresh_enabled
    if payload.refresh_cadence is not None:
        project.refresh_cadence = payload.refresh_cadence
    if payload.digest_enabled is not None:
        project.digest_enabled = payload.digest_enabled
    project.updated_at = utc_now()
    ensure_refresh_schedule(project)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/{project_id}/export")
def export_project_snapshot(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    detail = get_project_detail(project_id=project_id, current_user=current_user, session=session)
    return {
        "exported_at": utc_now().isoformat(),
        "project": detail.project.model_dump(),
        "papers": [paper.model_dump() for paper in detail.papers],
        "evidence_cards": [card.model_dump(mode="json") for card in detail.evidence_cards],
        "topic_note": detail.topic_note.model_dump(mode="json") if detail.topic_note else None,
        "update_runs": [run.model_dump(mode="json") for run in detail.update_runs],
        "note_update_suggestions": [suggestion.model_dump(mode="json") for suggestion in detail.note_update_suggestions],
        "note_versions": [version.model_dump(mode="json") for version in detail.note_versions],
    }
