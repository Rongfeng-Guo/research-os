from __future__ import annotations

import json
from collections import defaultdict

from sqlmodel import Session

from ..models import EvidenceCard, NoteUpdateSuggestion, Project, TopicNote
from ..time_utils import utc_now
from .diffing import build_diff_payload
from .note_sections import SECTION_TITLE_MAP, get_section, normalize_note_sections


SECTION_MAP = {
    "claim": "claim",
    "method": "method",
    "dataset": "dataset",
    "limitation": "limitation",
    "open_question": "open_question",
}


def infer_target_section(card_type: str) -> str:
    return SECTION_MAP.get(card_type, "overview")


def _build_proposed_text(cards: list[EvidenceCard]) -> str:
    proposed_lines = []
    for card in cards:
        proposed_lines.append(f"- {card.content}")
        if card.source_excerpt:
            proposed_lines.append(f'  Snippet: "{card.source_excerpt}"')
        if card.source_title:
            proposed_lines.append(f"  Source: {card.source_title}")
    return "\n".join(proposed_lines).strip()


def create_update_suggestions(
    session: Session,
    *,
    project: Project,
    note: TopicNote | None,
    update_run_id: int,
    new_evidence_cards: list[EvidenceCard],
) -> list[NoteUpdateSuggestion]:
    grouped: dict[str, list[EvidenceCard]] = defaultdict(list)
    for card in new_evidence_cards:
        grouped[infer_target_section(card.card_type)].append(card)

    note_sections = normalize_note_sections(note.markdown, note.sections_json) if note else []
    created: list[NoteUpdateSuggestion] = []
    for section_slug, cards in grouped.items():
        section_title = SECTION_TITLE_MAP.get(section_slug, section_slug)
        note_section = get_section(note_sections, section_slug) if note_sections else None
        current_text = note_section.get("content", "") if note_section else ""
        supporting_sources: list[str] = []
        for card in cards:
            label = card.source_title or f"Source {card.paper_id}"
            if label not in supporting_sources:
                supporting_sources.append(label)

        proposed_text = _build_proposed_text(cards)
        suggestion_type = "add" if not current_text else "revise"
        diff_payload = build_diff_payload(current_text, proposed_text)

        suggestion = NoteUpdateSuggestion(
            project_id=project.id,
            note_id=note.id if note else None,
            update_run_id=update_run_id,
            target_section=section_slug,
            suggestion_type=suggestion_type,
            current_text=current_text,
            proposed_text=proposed_text,
            rationale=f"New evidence cards were added for {section_title.lower()} during the latest refresh run.",
            supporting_evidence_ids_json=json.dumps([card.id for card in cards]),
            supporting_sources_json=json.dumps(supporting_sources),
            diff_payload_json=json.dumps(diff_payload),
            status="suggested",
            created_at=utc_now(),
        )
        session.add(suggestion)
        session.flush()
        created.append(suggestion)

    session.commit()
    for suggestion in created:
        session.refresh(suggestion)
    return created


def suggestion_to_read(suggestion: NoteUpdateSuggestion, *, note: TopicNote | None = None) -> dict:
    note_sections = normalize_note_sections(note.markdown, note.sections_json) if note else []
    target = get_section(note_sections, suggestion.target_section) if note_sections else None
    return {
        "id": suggestion.id,
        "project_id": suggestion.project_id,
        "note_id": suggestion.note_id,
        "update_run_id": suggestion.update_run_id,
        "target_section": suggestion.target_section,
        "suggestion_type": suggestion.suggestion_type,
        "current_text": suggestion.current_text,
        "proposed_text": suggestion.proposed_text,
        "rationale": suggestion.rationale,
        "supporting_evidence_ids": json.loads(suggestion.supporting_evidence_ids_json or "[]"),
        "supporting_sources": json.loads(suggestion.supporting_sources_json or "[]"),
        "diff": json.loads(suggestion.diff_payload_json or "{}"),
        "status": suggestion.status,
        "target_section_title": SECTION_TITLE_MAP.get(suggestion.target_section, suggestion.target_section),
        "target_section_locked": bool(target.get("is_locked")) if target else False,
        "created_at": suggestion.created_at,
        "reviewed_at": suggestion.reviewed_at,
        "applied_at": suggestion.applied_at,
        "applied_by": suggestion.applied_by or "",
    }


def apply_suggestions_to_sections(
    sections: list[dict],
    suggestions: list[NoteUpdateSuggestion],
) -> tuple[list[dict], list[NoteUpdateSuggestion], list[NoteUpdateSuggestion]]:
    section_map = {section["slug"]: section for section in sections}
    applied: list[NoteUpdateSuggestion] = []
    blocked: list[NoteUpdateSuggestion] = []
    for suggestion in suggestions:
        section = section_map.get(suggestion.target_section)
        if section and section.get("is_locked"):
            blocked.append(suggestion)
            continue

        if not section:
            section = {
                "slug": suggestion.target_section,
                "title": SECTION_TITLE_MAP.get(suggestion.target_section, suggestion.target_section),
                "content": "",
                "evidence_count": 0,
                "is_locked": False,
                "locked_at": None,
                "lock_reason": "",
                "edited_at": None,
                "edited_by": "",
                "last_manual_edit_at": None,
                "updated_at": None,
                "last_update_source": "",
            }
            sections.append(section)
            section_map[section["slug"]] = section

        current = (section.get("content") or "").strip()
        proposed = suggestion.proposed_text.strip()
        if suggestion.suggestion_type == "add" and current:
            section["content"] = f"{current}\n\n{proposed}".strip()
        else:
            section["content"] = proposed
        timestamp = utc_now().isoformat()
        section["edited_at"] = timestamp
        section["edited_by"] = "system"
        section["updated_at"] = timestamp
        section["last_update_source"] = "apply_suggestion"
        applied.append(suggestion)
    return sections, applied, blocked
