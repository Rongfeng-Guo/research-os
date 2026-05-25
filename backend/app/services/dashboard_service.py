from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlmodel import Session, select

from ..models import EvidenceCard, NoteUpdateSuggestion, Project, ProjectPaper, SourcePaper, TopicNote, TopicNoteVersion, UpdateRun, User
from ..schemas import DashboardSourceItem, EvidenceCardRead, ProjectHealthRead, ProjectRead, RecentNoteRead
from .project_health import compute_project_health, ensure_refresh_schedule, recommended_actions


def evidence_card_to_read(card: EvidenceCard) -> EvidenceCardRead:
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


def build_workspace_summary(session: Session, current_user: User | None = None, owner_id: int | None = None) -> dict:
    resolved_owner_id = owner_id or getattr(current_user, "id", None)
    if not resolved_owner_id:
        raise ValueError("owner_id is required to build workspace summary")
    now = datetime.now(UTC)
    projects = session.exec(select(Project).where(Project.owner_id == resolved_owner_id).order_by(Project.updated_at.desc())).all()
    project_map = {project.id: ensure_refresh_schedule(project, now=now) for project in projects}

    all_notes = session.exec(select(TopicNote).order_by(TopicNote.updated_at.desc())).all()
    notes = {note.project_id: note for note in all_notes if note.project_id in project_map}
    all_cards = [card for card in session.exec(select(EvidenceCard).order_by(EvidenceCard.created_at.desc())).all() if card.project_id in project_map]
    all_suggestions = [item for item in session.exec(select(NoteUpdateSuggestion).order_by(NoteUpdateSuggestion.created_at.desc())).all() if item.project_id in project_map]
    all_versions = [item for item in session.exec(select(TopicNoteVersion).order_by(TopicNoteVersion.created_at.desc())).all() if item.project_id in project_map]
    all_runs = [item for item in session.exec(select(UpdateRun).order_by(UpdateRun.created_at.desc())).all() if item.project_id in project_map]

    cards_by_project: dict[int, list[EvidenceCard]] = {}
    for card in all_cards:
        cards_by_project.setdefault(card.project_id, []).append(card)
    suggestions_by_project: dict[int, list[NoteUpdateSuggestion]] = {}
    for suggestion in all_suggestions:
        suggestions_by_project.setdefault(suggestion.project_id, []).append(suggestion)
    versions_by_project: dict[int, list[TopicNoteVersion]] = {}
    for version in all_versions:
        versions_by_project.setdefault(version.project_id, []).append(version)
    runs_by_project: dict[int, list[UpdateRun]] = {}
    for run in all_runs:
        runs_by_project.setdefault(run.project_id, []).append(run)

    health_map: dict[int, dict] = {}
    actions: list[dict] = []
    for project in projects:
        health = compute_project_health(
            project_map[project.id],
            note=notes.get(project.id),
            suggestions=suggestions_by_project.get(project.id, []),
            evidence_cards=cards_by_project.get(project.id, []),
            note_versions=versions_by_project.get(project.id, []),
            update_runs=runs_by_project.get(project.id, []),
            now=now,
        )
        health_map[project.id] = health
        actions.extend(recommended_actions(project, health))

    recent_notes = [
        RecentNoteRead(
            project_id=note.project_id,
            project_title=project_map[note.project_id].title,
            title=note.title,
            updated_at=note.updated_at,
            metadata=json.loads(note.metadata_json or "{}"),
        )
        for note in all_notes
        if note.project_id in project_map
    ][:6]

    pending_sources = []
    for join in session.exec(select(ProjectPaper)).all():
        if join.project_id not in project_map:
            continue
        paper = session.get(SourcePaper, join.paper_id)
        if not paper:
            continue
        if paper.extraction_status in {"pending", "partial", "failed"} or paper.ingestion_status != "completed":
            pending_sources.append(
                DashboardSourceItem(
                    project_id=join.project_id,
                    project_title=project_map[join.project_id].title,
                    paper_id=paper.id,
                    title=paper.title,
                    extraction_status=paper.extraction_status,
                    ingestion_status=paper.ingestion_status,
                    updated_hint=paper.origin,
                )
            )

    stale_projects = [
        ProjectRead.model_validate(project_map[project.id])
        for project in projects
        if health_map[project.id]["freshness_status"] in {"stale", "due_soon"}
    ][:6]

    pending_suggestions = [
        {
            "id": item.id,
            "project_id": item.project_id,
            "project_title": project_map[item.project_id].title,
            "target_section": item.target_section,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
        }
        for item in all_suggestions
        if item.status == "suggested"
    ][:8]

    locked_attention = []
    for item in all_suggestions:
        note = notes.get(item.project_id)
        if not note:
            continue
        for section in note.section_list():
            if section.get("slug") == item.target_section and section.get("is_locked") and item.status in {"suggested", "accepted"}:
                locked_attention.append(
                    {
                        "suggestion_id": item.id,
                        "project_id": item.project_id,
                        "project_title": project_map[item.project_id].title,
                        "target_section": item.target_section,
                        "status": item.status,
                    }
                )
                break

    recent_versions = [
        {
            "id": version.id,
            "project_id": version.project_id,
            "project_title": project_map[version.project_id].title,
            "version_number": version.version_number,
            "version_kind": version.version_kind,
            "created_at": version.created_at.isoformat(),
        }
        for version in all_versions[:8]
    ]

    counts = {
        "project_count": len(projects),
        "note_count": len(notes),
        "evidence_count": len(all_cards),
        "pending_source_count": len(pending_sources),
        "stale_project_count": len(stale_projects),
        "pending_suggestion_count": len([item for item in all_suggestions if item.status == "suggested"]),
        "locked_attention_count": len(locked_attention),
    }

    return {
        "recent_projects": [ProjectRead.model_validate(project_map[project.id]) for project in projects[:6]],
        "recent_notes": recent_notes,
        "recent_evidence": [evidence_card_to_read(card) for card in all_cards[:8]],
        "pending_sources": pending_sources[:8],
        "stale_projects": stale_projects,
        "pending_suggestions": pending_suggestions,
        "locked_attention": locked_attention[:8],
        "recent_versions": recent_versions,
        "recommended_actions": actions[:8],
        "counts": counts,
        "project_health": [ProjectHealthRead(**health_map[project.id]).model_dump(mode="json") for project in projects[:8]],
    }
