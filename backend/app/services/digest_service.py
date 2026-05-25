from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from ..models import EvidenceCard, NoteUpdateSuggestion, Project, TopicNote, TopicNoteVersion, UpdateRun, WorkspaceDigest
from ..settings import settings
from .dashboard_service import build_workspace_summary
from .project_health import _normalize_dt, compute_project_health, ensure_refresh_schedule, recommended_actions


def digest_slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return normalized or "digest"


def digest_to_read(digest: WorkspaceDigest) -> dict:
    return {
        "id": digest.id,
        "period_start": digest.period_start,
        "period_end": digest.period_end,
        "included_project_ids": json.loads(digest.included_project_ids_json or "[]"),
        "summary": json.loads(digest.summary_json or "{}"),
        "markdown": digest.markdown,
        "metadata": json.loads(digest.metadata_json or "{}"),
        "delivery_status": digest.delivery_status or "pending",
        "delivery_target": digest.delivery_target or "",
        "delivery_message": digest.delivery_message or "",
        "delivered_at": digest.delivered_at,
        "generated_at": digest.generated_at,
    }


def _resolve_owner_id(current_user: Any | None = None, *, owner_id: int | None = None) -> int:
    resolved = owner_id or getattr(current_user, "id", None)
    if not resolved:
        raise ValueError("owner_id is required to generate a workspace digest")
    return int(resolved)


def _resolve_projects_for_digest(session: Session, *, owner_id: int) -> list[Project]:
    return session.exec(
        select(Project).where(Project.owner_id == owner_id, Project.digest_enabled == True).order_by(Project.updated_at.desc())  # noqa: E712
    ).all()


def get_latest_digest_for_owner(session: Session, *, owner_id: int) -> WorkspaceDigest | None:
    return session.exec(
        select(WorkspaceDigest).where(WorkspaceDigest.owner_id == owner_id).order_by(WorkspaceDigest.generated_at.desc())
    ).first()


def should_generate_scheduled_digest(session: Session, *, owner_id: int, now: datetime | None = None, days: int | None = None) -> bool:
    now = _normalize_dt(now or datetime.now(UTC))
    digest_days = days or settings.digest_window_days
    projects = _resolve_projects_for_digest(session, owner_id=owner_id)
    if not projects:
        return False
    latest = get_latest_digest_for_owner(session, owner_id=owner_id)
    if latest is None:
        return True
    return _normalize_dt(latest.generated_at) <= now - timedelta(days=digest_days)


def generate_workspace_digest(
    session: Session,
    *,
    current_user=None,
    owner_id: int | None = None,
    days: int = 7,
    persist: bool = True,
    generated_from: str = "manual_request",
) -> WorkspaceDigest:
    resolved_owner_id = _resolve_owner_id(current_user, owner_id=owner_id)
    now = datetime.now(UTC)
    period_end = now
    period_start = now - timedelta(days=days)
    projects = _resolve_projects_for_digest(session, owner_id=resolved_owner_id)
    included_project_ids = [project.id for project in projects]

    updates = [run for run in session.exec(select(UpdateRun)).all() if run.project_id in included_project_ids and _normalize_dt(run.created_at) >= period_start]
    evidence_cards = [card for card in session.exec(select(EvidenceCard)).all() if card.project_id in included_project_ids and _normalize_dt(card.created_at) >= period_start]
    suggestions = [item for item in session.exec(select(NoteUpdateSuggestion)).all() if item.project_id in included_project_ids]
    recent_notes = [note for note in session.exec(select(TopicNote)).all() if note.project_id in included_project_ids and _normalize_dt(note.updated_at) >= period_start]
    note_versions = [item for item in session.exec(select(TopicNoteVersion)).all() if item.project_id in included_project_ids and _normalize_dt(item.created_at) >= period_start]

    project_notes = {note.project_id: note for note in session.exec(select(TopicNote)).all() if note.project_id in included_project_ids}
    project_versions: dict[int, list[TopicNoteVersion]] = {}
    for version in session.exec(select(TopicNoteVersion)).all():
        if version.project_id in included_project_ids:
            project_versions.setdefault(version.project_id, []).append(version)
    project_runs: dict[int, list[UpdateRun]] = {}
    for run in session.exec(select(UpdateRun)).all():
        if run.project_id in included_project_ids:
            project_runs.setdefault(run.project_id, []).append(run)
    project_cards: dict[int, list[EvidenceCard]] = {}
    for card in session.exec(select(EvidenceCard)).all():
        if card.project_id in included_project_ids:
            project_cards.setdefault(card.project_id, []).append(card)
    project_suggestions: dict[int, list[NoteUpdateSuggestion]] = {}
    for suggestion in suggestions:
        project_suggestions.setdefault(suggestion.project_id, []).append(suggestion)

    project_summaries = []
    recommended = []
    for project in projects:
        project = ensure_refresh_schedule(project, now=now)
        health = compute_project_health(
            project,
            note=project_notes.get(project.id),
            suggestions=project_suggestions.get(project.id, []),
            evidence_cards=project_cards.get(project.id, []),
            note_versions=project_versions.get(project.id, []),
            update_runs=project_runs.get(project.id, []),
            now=now,
        )
        recommended.extend(recommended_actions(project, health))
        project_summaries.append(
            {
                "project_id": project.id,
                "project_title": project.title,
                "freshness_status": health["freshness_status"],
                "pending_review_count": health["pending_review_count"],
                "locked_attention_count": health["locked_attention_count"],
                "evidence_growth_week": health["evidence_growth_week"],
                "last_refresh": project.last_refreshed_at.isoformat() if project.last_refreshed_at else None,
            }
        )

    accepted_count = len([card for card in evidence_cards if card.review_status == "accepted"])
    rejected_count = len([card for card in evidence_cards if card.review_status == "rejected"])
    pending_suggestion_count = len([item for item in suggestions if item.status == "suggested"])
    locked_attention_count = 0
    for item in suggestions:
        note = project_notes.get(item.project_id)
        if not note:
            continue
        for section in note.section_list():
            if section.get("slug") == item.target_section and section.get("is_locked") and item.status in {"suggested", "accepted"}:
                locked_attention_count += 1
                break

    summary = {
        "project_count": len(projects),
        "projects_updated": len({run.project_id for run in updates}),
        "new_papers_found": sum(run.papers_found for run in updates),
        "papers_added": sum(run.papers_added for run in updates),
        "new_evidence_cards": len(evidence_cards),
        "accepted_evidence_count": accepted_count,
        "rejected_evidence_count": rejected_count,
        "notes_updated": len(recent_notes),
        "new_note_versions": len(note_versions),
        "pending_update_suggestions": pending_suggestion_count,
        "locked_sections_awaiting_review": locked_attention_count,
        "recommended_next_actions": len(recommended),
        "projects": project_summaries,
    }

    slug = digest_slug(f"weekly-digest-{period_start.date().isoformat()}-{period_end.date().isoformat()}")
    markdown_lines = [
        f"# Weekly Research Digest",
        "",
        f"Period: {period_start.date().isoformat()} to {period_end.date().isoformat()}",
        "",
        f"- Projects updated: {summary['projects_updated']}",
        f"- New papers found: {summary['new_papers_found']}",
        f"- Papers added: {summary['papers_added']}",
        f"- New evidence cards: {summary['new_evidence_cards']}",
        f"- Accepted evidence this period: {summary['accepted_evidence_count']}",
        f"- Rejected evidence this period: {summary['rejected_evidence_count']}",
        f"- Notes updated: {summary['notes_updated']}",
        f"- Pending update suggestions: {summary['pending_update_suggestions']}",
        f"- Locked sections awaiting review: {summary['locked_sections_awaiting_review']}",
        "",
        "## Projects",
        "",
    ]
    if not project_summaries:
        markdown_lines.append("- No project activity in this period.")
    else:
        for item in project_summaries:
            markdown_lines.append(
                f"- {item['project_title']}: {item['freshness_status']}, {item['pending_review_count']} pending suggestions, {item['locked_attention_count']} locked-section reviews"
            )

    markdown_lines.extend(["", "## Recommended Next Actions", ""])
    if not recommended:
        markdown_lines.append("- No urgent actions. Your workspace looks steady.")
    else:
        for action in recommended[:8]:
            markdown_lines.append(f"- {action['label']}")

    digest = WorkspaceDigest(
        period_start=period_start,
        period_end=period_end,
        included_project_ids_json=json.dumps(included_project_ids),
        summary_json=json.dumps(summary),
        markdown="\n".join(markdown_lines).strip(),
        metadata_json=json.dumps(
            {
                "days": days,
                "generated_from": generated_from,
                "slug": slug,
                "dashboard_counts": build_workspace_summary(session, owner_id=resolved_owner_id)["counts"],
            }
        ),
        owner_id=resolved_owner_id,
    )
    if persist:
        session.add(digest)
        session.commit()
        session.refresh(digest)
    return digest
