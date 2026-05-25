from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from ..models import EvidenceCard, Project, ProjectPaper, SourcePaper, TopicNote, UpdateRun


def _normalize_text(value: str) -> str:
    return " ".join((value or "").lower().split())


def fingerprint_text(value: str) -> str:
    normalized = _normalize_text(value)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def source_fingerprint(*, title: str, text: str, authors: str = "", year: int | None = None, url: str = "") -> str:
    payload = {
        "title": _normalize_text(title),
        "text": _normalize_text(text),
        "authors": _normalize_text(authors),
        "year": year or 0,
        "url": (url or "").strip().lower(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def evidence_fingerprint(
    *,
    card_type: str,
    content: str,
    source_title: str = "",
    source_section: str = "",
    source_chunk_id: str = "",
) -> str:
    payload = {
        "card_type": card_type.strip().lower(),
        "content": _normalize_text(content),
        "source_title": _normalize_text(source_title),
        "source_section": _normalize_text(source_section),
        "source_chunk_id": _normalize_text(source_chunk_id),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def sync_project_paper_state(link: ProjectPaper, paper: SourcePaper) -> ProjectPaper:
    if link.extraction_state == "queued":
        return link
    if paper.extraction_status == "failed":
        link.extraction_state = "failed"
        return link
    if not paper.content_fingerprint:
        link.extraction_state = "not_started"
        return link
    if not link.extracted_fingerprint:
        link.extraction_state = "not_started"
        return link
    if link.extracted_fingerprint != paper.content_fingerprint:
        link.extraction_state = "stale"
        return link
    link.extraction_state = "completed"
    return link


def mark_source_changed(project: Project, link: ProjectPaper, paper: SourcePaper) -> None:
    project.knowledge_status = "needs_refresh"
    link.extraction_state = "stale" if link.extracted_fingerprint else "not_started"
    paper.extraction_status = "stale"


def compute_note_status(
    *,
    note: TopicNote | None,
    project_papers: list[ProjectPaper],
    update_runs: list[UpdateRun],
) -> str:
    if any(run.run_type == "note_generation" and run.status == "running" for run in update_runs):
        return "generating"
    if any(run.run_type == "note_generation" and run.status == "failed" for run in update_runs) and note is None:
        return "failed"
    if note is None:
        return "missing"
    if any(link.extraction_state in {"not_started", "queued", "failed", "stale"} for link in project_papers):
        return "stale"
    return "current"


def compute_project_knowledge_status(
    *,
    project: Project,
    project_papers: list[ProjectPaper],
    update_runs: list[UpdateRun],
) -> str:
    if any(run.run_type in {"project_refresh", "extraction"} and run.status == "running" for run in update_runs):
        return "refreshing"
    if update_runs:
        latest_refresh = next((run for run in update_runs if run.run_type == "project_refresh"), None)
        if latest_refresh and latest_refresh.status == "failed":
            return "refresh_failed"
    if not project_papers:
        return "idle"
    if any(link.extraction_state in {"not_started", "queued", "failed", "stale"} for link in project_papers):
        return "needs_refresh"
    return "up_to_date"


def build_project_status_summary(
    *,
    project: Project,
    project_papers: list[ProjectPaper],
    papers: list[SourcePaper],
    evidence_cards: list[EvidenceCard],
    note: TopicNote | None,
    update_runs: list[UpdateRun],
) -> dict:
    paper_map = {paper.id: paper for paper in papers if paper.id is not None}
    for link in project_papers:
        paper = paper_map.get(link.paper_id)
        if paper:
            sync_project_paper_state(link, paper)

    knowledge_status = compute_project_knowledge_status(project=project, project_papers=project_papers, update_runs=update_runs)
    note_status = compute_note_status(note=note, project_papers=project_papers, update_runs=update_runs)

    evidence_by_review_status = {
        "suggested": len([card for card in evidence_cards if (card.review_status or "suggested") == "suggested"]),
        "accepted": len([card for card in evidence_cards if card.review_status == "accepted"]),
        "rejected": len([card for card in evidence_cards if card.review_status == "rejected"]),
    }
    source_state_counts = {
        "not_started": len([link for link in project_papers if link.extraction_state == "not_started"]),
        "queued": len([link for link in project_papers if link.extraction_state == "queued"]),
        "completed": len([link for link in project_papers if link.extraction_state == "completed"]),
        "failed": len([link for link in project_papers if link.extraction_state == "failed"]),
        "stale": len([link for link in project_papers if link.extraction_state == "stale"]),
    }

    note_metadata = json.loads(note.metadata_json or "{}") if note else {}
    accepted_only = bool(note_metadata.get("accepted_evidence_only")) if note else False
    return {
        "knowledge_status": knowledge_status,
        "needs_refresh": knowledge_status in {"needs_refresh", "refresh_failed"},
        "note_status": note_status,
        "source_count": len(project_papers),
        "source_state_counts": source_state_counts,
        "evidence_count": len(evidence_cards),
        "evidence_by_review_status": evidence_by_review_status,
        "stale_evidence_count": len([card for card in evidence_cards if bool(card.is_stale)]),
        "last_refresh_at": project.last_refreshed_at,
        "last_generation_at": _as_utc(note.updated_at) if note else None,
        "accepted_evidence_only": accepted_only,
    }
