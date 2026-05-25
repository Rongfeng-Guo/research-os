from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ..models import EvidenceCard, NoteUpdateSuggestion, Project, TopicNote, TopicNoteVersion, UpdateRun


CADENCE_WINDOWS = {
    "manual_only": None,
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "custom": timedelta(days=14),
}


def _normalize_dt(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def ensure_refresh_schedule(project: Project, *, now: datetime | None = None) -> Project:
    now = _normalize_dt(now or datetime.now(UTC))
    cadence_window = CADENCE_WINDOWS.get(project.refresh_cadence, None)
    if not cadence_window or not project.auto_refresh_enabled:
        project.next_refresh_due_at = None
        return project

    anchor = _normalize_dt(project.last_refreshed_at or project.updated_at or project.created_at)
    project.next_refresh_due_at = anchor + cadence_window
    return project


def freshness_status(project: Project, *, now: datetime | None = None) -> tuple[str, str]:
    now = _normalize_dt(now or datetime.now(UTC))
    project = ensure_refresh_schedule(project, now=now)
    if project.refresh_cadence == "manual_only" or not project.auto_refresh_enabled:
        if not project.last_refreshed_at:
            return "manual", "Manual-only project without a recorded refresh yet."
        return "manual", "Refresh cadence is manual only."

    due_at = _normalize_dt(project.next_refresh_due_at) if project.next_refresh_due_at else None
    if due_at is None:
        return "manual", "Refresh cadence is manual only."

    delta = due_at - now
    if delta.total_seconds() < 0:
        return "stale", f"Refresh was due on {due_at.date().isoformat()}."
    if delta <= timedelta(days=2):
        return "due_soon", f"Refresh is due by {due_at.date().isoformat()}."
    return "fresh", f"Next refresh is due on {due_at.date().isoformat()}."


def project_is_due_for_refresh(project: Project, *, now: datetime | None = None) -> bool:
    now = _normalize_dt(now or datetime.now(UTC))
    project = ensure_refresh_schedule(project, now=now)
    if not project.auto_refresh_enabled or project.refresh_cadence == "manual_only":
        return False
    due_at = _normalize_dt(project.next_refresh_due_at) if project.next_refresh_due_at else None
    if due_at is None:
        return False
    return due_at <= now


def compute_project_health(
    project: Project,
    *,
    note: TopicNote | None,
    suggestions: list[NoteUpdateSuggestion],
    evidence_cards: list[EvidenceCard],
    note_versions: list[TopicNoteVersion],
    update_runs: list[UpdateRun],
    now: datetime | None = None,
) -> dict:
    now = _normalize_dt(now or datetime.now(UTC))
    freshness, freshness_reason = freshness_status(project, now=now)
    week_ago = now - timedelta(days=7)
    pending_review_count = len([item for item in suggestions if item.status == "suggested"])
    locked_attention_count = len(
        [
            item
            for item in suggestions
            if item.status in {"suggested", "accepted"} and note and any(
                section.get("slug") == item.target_section and section.get("is_locked")
                for section in note.section_list()
            )
        ]
    )
    last_activity = max(
        [_normalize_dt(project.updated_at)]
        + [_normalize_dt(card.created_at) for card in evidence_cards]
        + [_normalize_dt(version.created_at) for version in note_versions]
        + [_normalize_dt(run.created_at) for run in update_runs],
        default=_normalize_dt(project.updated_at),
    )
    evidence_growth_week = len([card for card in evidence_cards if _normalize_dt(card.created_at) >= week_ago])
    latest_note_update_at = _normalize_dt(note.updated_at) if note and note.updated_at else None
    stale_note = bool(note and _normalize_dt(note.updated_at) < _normalize_dt(project.updated_at))
    return {
        "project_id": project.id,
        "freshness_status": freshness,
        "freshness_reason": freshness_reason,
        "pending_review_count": pending_review_count,
        "locked_attention_count": locked_attention_count,
        "stale_note": stale_note,
        "last_activity_at": last_activity,
        "evidence_growth_week": evidence_growth_week,
        "note_version_count": len(note_versions),
        "latest_note_update_at": latest_note_update_at,
    }


def recommended_actions(project: Project, health: dict) -> list[dict]:
    actions: list[dict] = []
    if health["pending_review_count"] > 0:
        actions.append(
            {
                "kind": "review_suggestions",
                "project_id": project.id,
                "project_title": project.title,
                "label": f"Review {health['pending_review_count']} pending update suggestions",
                "href": f"/projects/{project.id}/history",
            }
        )
    if health["freshness_status"] in {"stale", "due_soon"}:
        actions.append(
            {
                "kind": "refresh_project",
                "project_id": project.id,
                "project_title": project.title,
                "label": f"Refresh {project.title} because it is {health['freshness_status'].replace('_', ' ')}",
                "href": f"/projects/{project.id}",
            }
        )
    if health["locked_attention_count"] > 0:
        actions.append(
            {
                "kind": "locked_review",
                "project_id": project.id,
                "project_title": project.title,
                "label": f"Inspect {health['locked_attention_count']} locked-section updates",
                "href": f"/projects/{project.id}/history",
            }
        )
    if health["stale_note"]:
        actions.append(
            {
                "kind": "update_note",
                "project_id": project.id,
                "project_title": project.title,
                "label": f"Regenerate the note for {project.title}",
                "href": f"/projects/{project.id}",
            }
        )
    return actions
