import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..auth import get_current_user
from ..db import get_session
from ..models import EvidenceCard, NoteUpdateSuggestion, Project, ProjectPaper, SourcePaper, TopicNote, TopicNoteVersion, User
from ..schemas import (
    ApplySuggestionsRequest,
    NoteSectionUpdate,
    NoteUpdateSuggestionRead,
    SuggestionStatusUpdate,
    TopicNoteRead,
    TopicNoteSectionRead,
    TopicNoteVersionRead,
    VersionComparisonRead,
)
from ..services.diffing import build_diff_payload
from ..services.note_generation import build_note
from ..services.note_sections import get_section, merge_generated_sections, normalize_note_sections, render_note_markdown, sections_to_json
from ..services.note_versions import create_note_version, version_to_read
from ..services.update_runs import create_update_run, finish_update_run
from ..services.update_suggestions import apply_suggestions_to_sections, suggestion_to_read
from ..time_utils import utc_now

router = APIRouter(prefix="/notes", tags=["notes"])

VALID_GENERATION_MODES = {
    "accepted_only",
    "all_non_rejected",
    "accepted_plus_pinned_priority",
    "pinned_only",
}


def _note_to_read(note: TopicNote) -> TopicNoteRead:
    sections = normalize_note_sections(note.markdown, note.sections_json)
    return TopicNoteRead(
        id=note.id,
        project_id=note.project_id,
        title=note.title,
        markdown=note.markdown,
        sections=[TopicNoteSectionRead(**section) for section in sections],
        metadata=json.loads(note.metadata_json or "{}"),
        updated_at=note.updated_at,
    )


def _load_project_note(session: Session, project_id: int, current_user: User) -> tuple[Project, TopicNote]:
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    note = session.exec(select(TopicNote).where(TopicNote.project_id == project_id)).first()
    if not note:
        raise HTTPException(status_code=404, detail="Topic note not found")
    return project, note


def _build_note_inputs(session: Session, project_id: int) -> tuple[list[dict], list[dict]]:
    joins = session.exec(select(ProjectPaper).where(ProjectPaper.project_id == project_id)).all()
    papers = []
    for join in joins:
        paper = session.get(SourcePaper, join.paper_id)
        if paper:
            papers.append(
                {
                    "id": paper.id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "year": paper.year,
                    "abstract": paper.abstract,
                    "url": paper.url,
                    "source": paper.source,
                    "content_text": paper.content_text,
                    "content_type": paper.content_type,
                }
            )

    paper_title_map = {paper["id"]: paper["title"] for paper in papers}
    cards = session.exec(select(EvidenceCard).where(EvidenceCard.project_id == project_id)).all()
    card_dicts: List[dict] = []
    for card in cards:
        card_dicts.append(
            {
                "card_type": card.card_type,
                "title": card.title,
                "content": card.content,
                "review_status": card.review_status,
                "confidence_score": card.confidence_score,
                "source_url": card.source_url,
                "source_title": card.source_title or paper_title_map.get(card.paper_id, ""),
                "source_excerpt": card.source_excerpt,
                "source_chunk_id": card.source_chunk_id,
                "source_section": card.source_section,
                "user_note": card.user_note,
                "is_pinned": card.is_pinned,
            }
        )
    return papers, card_dicts


def _apply_suggestions(
    *,
    session: Session,
    project: Project,
    note: TopicNote,
    generation_mode: str,
    suggestions: list[NoteUpdateSuggestion],
    run_type: str,
    summary: str,
) -> TopicNote:
    run = create_update_run(
        session,
        project_id=project.id,
        run_type=run_type,
        trigger_type="manual",
        provider="note_compiler",
        summary=summary,
    )
    if not suggestions:
        finish_update_run(session, run, status="completed", summary="No matching suggestions to apply")
        return note

    sections = normalize_note_sections(note.markdown, note.sections_json)
    updated_sections, applied, blocked = apply_suggestions_to_sections(sections, suggestions)
    if not applied:
        metadata = json.loads(note.metadata_json or "{}")
        metadata["generation_mode"] = generation_mode
        metadata["blocked_locked_suggestion_count"] = len(blocked)
        metadata["last_applied_at"] = utc_now().isoformat()
        note.metadata_json = json.dumps(metadata)
        session.add(note)
        session.commit()
        session.refresh(note)
        finish_update_run(session, run, status="completed", summary=f"{len(blocked)} suggestions blocked by locked sections")
        return note

    note.sections_json = sections_to_json(updated_sections)
    note.markdown = render_note_markdown(project.title, project.topic, updated_sections)
    metadata = json.loads(note.metadata_json or "{}")
    metadata["generation_mode"] = generation_mode
    metadata["applied_suggestion_count"] = len(applied)
    metadata["blocked_locked_suggestion_count"] = len(blocked)
    metadata["last_applied_at"] = utc_now().isoformat()
    metadata["last_update_source"] = "apply_suggestion"
    metadata["source_suggestion_ids"] = [suggestion.id for suggestion in applied]
    note.metadata_json = json.dumps(metadata)
    note.updated_at = utc_now()
    session.add(note)

    for suggestion in applied:
        suggestion.status = "applied"
        suggestion.reviewed_at = utc_now()
        suggestion.applied_at = utc_now()
        suggestion.applied_by = "user"
        session.add(suggestion)

    project.updated_at = utc_now()
    session.add(project)
    session.commit()
    session.refresh(note)
    create_note_version(
        session,
        note=note,
        update_run_id=run.id,
        version_kind="apply_suggestion",
        source_suggestion_ids=[suggestion.id for suggestion in applied],
    )
    summary_text = f"Applied {len(applied)} suggestions"
    if blocked:
        summary_text += f"; {len(blocked)} blocked by locked sections"
    finish_update_run(session, run, status="completed", summary=summary_text)
    return note


@router.post("/projects/{project_id}/generate", response_model=TopicNoteRead)
def generate_note(
    project_id: int,
    generation_mode: str = Query(default="accepted_only"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    if generation_mode not in VALID_GENERATION_MODES:
        raise HTTPException(status_code=400, detail="Invalid generation mode")

    papers, card_dicts = _build_note_inputs(session, project_id)
    run = create_update_run(
        session,
        project_id=project_id,
        run_type="note_generation",
        trigger_type="manual",
        provider="note_compiler",
        summary="Note generation requested",
    )

    markdown, sections_json, metadata_json = build_note(
        project.title,
        project.topic,
        papers,
        card_dicts,
        provider="note_compiler",
        generation_mode=generation_mode,
    )
    generated_sections = normalize_note_sections(markdown, sections_json)

    note = session.exec(select(TopicNote).where(TopicNote.project_id == project_id)).first()
    if note:
        existing_sections = normalize_note_sections(note.markdown, note.sections_json)
        merged_sections = merge_generated_sections(existing_sections, generated_sections)
        note.markdown = render_note_markdown(project.title, project.topic, merged_sections)
        note.title = f"{project.title} Research Note"
        note.sections_json = sections_to_json(merged_sections)
        note.metadata_json = metadata_json
        note.updated_at = utc_now()
        session.add(note)
        session.commit()
        session.refresh(note)
        create_note_version(session, note=note, update_run_id=run.id, version_kind="generation")
    else:
        note = TopicNote(
            project_id=project_id,
            title=f"{project.title} Research Note",
            markdown=render_note_markdown(project.title, project.topic, generated_sections),
            sections_json=sections_to_json(generated_sections),
            metadata_json=metadata_json,
        )
        session.add(note)
        session.commit()
        session.refresh(note)
        create_note_version(session, note=note, update_run_id=run.id, version_kind="generation")

    project.updated_at = utc_now()
    session.add(project)
    session.commit()
    session.refresh(note)
    finish_update_run(session, run, status="completed", summary="Topic note generated")
    return _note_to_read(note)


@router.get("/projects/{project_id}", response_model=TopicNoteRead)
def get_project_note(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _, note = _load_project_note(session, project_id, current_user)
    return _note_to_read(note)


@router.patch("/projects/{project_id}/sections/{section_slug}", response_model=TopicNoteRead)
def update_note_section(
    project_id: int,
    section_slug: str,
    payload: NoteSectionUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project, note = _load_project_note(session, project_id, current_user)

    sections = normalize_note_sections(note.markdown, note.sections_json)
    section = get_section(sections, section_slug)
    if not section:
        raise HTTPException(status_code=404, detail="Note section not found")

    timestamp = utc_now().isoformat()
    if payload.content is not None:
        section["content"] = payload.content
        section["edited_at"] = timestamp
        section["edited_by"] = "user"
        section["last_manual_edit_at"] = timestamp
        section["updated_at"] = timestamp
        section["last_update_source"] = "user"
    if payload.is_locked is not None:
        section["is_locked"] = payload.is_locked
        section["locked_at"] = timestamp if payload.is_locked else None
        if not payload.is_locked:
            section["lock_reason"] = ""
    if payload.lock_reason is not None:
        section["lock_reason"] = payload.lock_reason

    note.sections_json = sections_to_json(sections)
    note.markdown = render_note_markdown(project.title, project.topic, sections)
    note.updated_at = utc_now()
    metadata = json.loads(note.metadata_json or "{}")
    metadata["last_section_edit_at"] = timestamp
    metadata["last_update_source"] = "user"
    note.metadata_json = json.dumps(metadata)
    session.add(note)
    session.commit()
    session.refresh(note)
    create_note_version(session, note=note, version_kind="manual_edit")

    project.updated_at = utc_now()
    session.add(project)
    session.commit()
    return _note_to_read(note)


@router.get("/projects/{project_id}/versions", response_model=List[TopicNoteVersionRead])
def list_note_versions(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    versions = session.exec(
        select(TopicNoteVersion).where(TopicNoteVersion.project_id == project_id).order_by(TopicNoteVersion.version_number.desc())
    ).all()
    return [TopicNoteVersionRead(**version_to_read(version)) for version in versions]


@router.get("/projects/{project_id}/versions/{version_id}/compare", response_model=VersionComparisonRead)
def compare_note_version(
    project_id: int,
    version_id: int,
    against_version_id: int | None = Query(default=None),
    compare_to_current: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    base_version = session.get(TopicNoteVersion, version_id)
    if not base_version or base_version.project_id != project_id:
        raise HTTPException(status_code=404, detail="Base version not found")

    if compare_to_current:
        note = session.exec(select(TopicNote).where(TopicNote.project_id == project_id)).first()
        if not note:
            raise HTTPException(status_code=404, detail="Topic note not found")
        compare_markdown = note.markdown
        compare_id = note.id
    else:
        if against_version_id is None:
            raise HTTPException(status_code=400, detail="against_version_id is required unless compare_to_current=true")
        compare_version = session.get(TopicNoteVersion, against_version_id)
        if not compare_version or compare_version.project_id != project_id:
            raise HTTPException(status_code=404, detail="Compare version not found")
        compare_markdown = compare_version.markdown
        compare_id = compare_version.id

    return VersionComparisonRead(
        base_version_id=base_version.id,
        compare_version_id=compare_id,
        diff=build_diff_payload(base_version.markdown, compare_markdown),
    )


@router.get("/projects/{project_id}/suggestions", response_model=List[NoteUpdateSuggestionRead])
def list_note_suggestions(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    note = session.exec(select(TopicNote).where(TopicNote.project_id == project_id)).first()
    suggestions = session.exec(
        select(NoteUpdateSuggestion).where(NoteUpdateSuggestion.project_id == project_id).order_by(NoteUpdateSuggestion.created_at.desc())
    ).all()
    return [NoteUpdateSuggestionRead(**suggestion_to_read(suggestion, note=note)) for suggestion in suggestions]


@router.patch("/suggestions/{suggestion_id}", response_model=NoteUpdateSuggestionRead)
def review_note_suggestion(
    suggestion_id: int,
    payload: SuggestionStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if payload.status not in {"suggested", "accepted", "rejected", "applied"}:
        raise HTTPException(status_code=400, detail="Invalid suggestion status")

    suggestion = session.get(NoteUpdateSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    project = session.get(Project, suggestion.project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    suggestion.status = payload.status
    suggestion.reviewed_at = utc_now()
    session.add(suggestion)
    project.updated_at = utc_now()
    session.add(project)
    session.commit()
    session.refresh(suggestion)
    note = session.exec(select(TopicNote).where(TopicNote.project_id == project.id)).first()
    return NoteUpdateSuggestionRead(**suggestion_to_read(suggestion, note=note))


@router.post("/suggestions/{suggestion_id}/apply", response_model=TopicNoteRead)
def apply_single_suggestion(
    suggestion_id: int,
    payload: ApplySuggestionsRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    suggestion = session.get(NoteUpdateSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    project, note = _load_project_note(session, suggestion.project_id, current_user)
    if payload.generation_mode not in VALID_GENERATION_MODES:
        raise HTTPException(status_code=400, detail="Invalid generation mode")
    if suggestion.status == "rejected":
        raise HTTPException(status_code=400, detail="Rejected suggestions cannot be applied")

    updated_note = _apply_suggestions(
        session=session,
        project=project,
        note=note,
        generation_mode=payload.generation_mode,
        suggestions=[suggestion],
        run_type="apply_single_suggestion",
        summary=f"Applying suggestion {suggestion.id}",
    )
    return _note_to_read(updated_note)


@router.post("/projects/{project_id}/sections/{section_slug}/apply-suggestions", response_model=TopicNoteRead)
def apply_section_suggestions(
    project_id: int,
    section_slug: str,
    payload: ApplySuggestionsRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project, note = _load_project_note(session, project_id, current_user)
    if payload.generation_mode not in VALID_GENERATION_MODES:
        raise HTTPException(status_code=400, detail="Invalid generation mode")
    statement = select(NoteUpdateSuggestion).where(
        NoteUpdateSuggestion.project_id == project_id,
        NoteUpdateSuggestion.target_section == section_slug,
        NoteUpdateSuggestion.status == "accepted",
    )
    if payload.suggestion_ids:
        statement = statement.where(NoteUpdateSuggestion.id.in_(payload.suggestion_ids))
    suggestions = session.exec(statement.order_by(NoteUpdateSuggestion.created_at.asc())).all()
    updated_note = _apply_suggestions(
        session=session,
        project=project,
        note=note,
        generation_mode=payload.generation_mode,
        suggestions=suggestions,
        run_type="apply_section_suggestions",
        summary=f"Applying accepted suggestions for section {section_slug}",
    )
    return _note_to_read(updated_note)


@router.post("/projects/{project_id}/apply-suggestions", response_model=TopicNoteRead)
def apply_accepted_suggestions(
    project_id: int,
    payload: ApplySuggestionsRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project, note = _load_project_note(session, project_id, current_user)
    if payload.generation_mode not in VALID_GENERATION_MODES:
        raise HTTPException(status_code=400, detail="Invalid generation mode")

    statement = select(NoteUpdateSuggestion).where(
        NoteUpdateSuggestion.project_id == project_id,
        NoteUpdateSuggestion.status == "accepted",
    )
    if payload.section_slug:
        statement = statement.where(NoteUpdateSuggestion.target_section == payload.section_slug)
    if payload.suggestion_ids:
        statement = statement.where(NoteUpdateSuggestion.id.in_(payload.suggestion_ids))

    suggestions = session.exec(statement.order_by(NoteUpdateSuggestion.created_at.asc())).all()
    updated_note = _apply_suggestions(
        session=session,
        project=project,
        note=note,
        generation_mode=payload.generation_mode,
        suggestions=suggestions,
        run_type="apply_note_updates",
        summary="Applying accepted note update suggestions",
    )
    return _note_to_read(updated_note)
