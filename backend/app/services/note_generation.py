from __future__ import annotations

import json
from typing import Iterable

from ..time_utils import utc_now
from .note_sections import NOTE_SECTION_ORDER, render_note_markdown, sections_to_json


def _source_reference(card: dict) -> str:
    title = card.get("source_title") or card.get("paper_title") or "Unknown source"
    chunk = card.get("source_chunk_id") or ""
    snippet = card.get("source_excerpt") or ""
    label = title if not chunk else f"{title} ({chunk})"
    if card.get("source_url"):
        return f"[{label}]({card['source_url']})"
    if snippet:
        return f"{label} | {snippet}"
    return label


def _format_evidence_bullet(card: dict) -> str:
    lines = [f"- {card['content']}"]
    lines.append(f"  Source: {_source_reference(card)}")
    if card.get("source_section"):
        lines.append(f"  Section: {card['source_section']}")
    if card.get("source_excerpt"):
        lines.append(f'  Snippet: "{card["source_excerpt"]}"')
    if card.get("user_note"):
        lines.append(f"  Note: {card['user_note']}")
    return "\n".join(lines)


def _is_visible_for_mode(card: dict, generation_mode: str) -> bool:
    status = card.get("review_status") or "suggested"
    is_pinned = bool(card.get("is_pinned"))
    if generation_mode == "accepted_only":
        return status == "accepted"
    if generation_mode == "pinned_only":
        return is_pinned and status != "rejected"
    return status != "rejected"


def _sort_weight(card: dict, generation_mode: str) -> tuple[int, int, float, str]:
    status = card.get("review_status") or "suggested"
    is_pinned = bool(card.get("is_pinned"))
    if generation_mode == "accepted_plus_pinned_priority":
        return (
            0 if is_pinned else 1,
            0 if status == "accepted" else 1,
            -(card.get("confidence_score") or 0.0),
            card.get("source_title", ""),
        )
    return (
        0 if status == "accepted" else 1,
        0 if is_pinned else 1,
        -(card.get("confidence_score") or 0.0),
        card.get("source_title", ""),
    )


def _group_visible_evidence(evidence_cards: Iterable[dict], generation_mode: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for card in evidence_cards:
        if not _is_visible_for_mode(card, generation_mode):
            continue
        grouped.setdefault(card["card_type"], []).append(card)

    for items in grouped.values():
        items.sort(key=lambda card: _sort_weight(card, generation_mode))
    return grouped


def build_note(
    project_title: str,
    topic: str,
    papers: list[dict],
    evidence_cards: Iterable[dict],
    *,
    provider: str,
    generation_mode: str = "accepted_only",
) -> tuple[str, str, str]:
    grouped = _group_visible_evidence(evidence_cards, generation_mode)
    generated_at = utc_now().isoformat()

    sections: list[dict] = []
    for slug, title in NOTE_SECTION_ORDER:
        content = ""
        if slug == "overview":
            content = "\n".join(
                [
                    f"This note compiles source-grounded evidence for **{project_title}**.",
                    f"Generated at: {generated_at}",
                    f"Provider used: {provider}",
                    f"Generation mode: {generation_mode}",
                ]
            )
        elif slug == "sources":
            source_lines: list[str] = []
            for paper in papers:
                title_value = paper.get("title", "Untitled source")
                line = f"- {title_value}"
                if paper.get("url"):
                    line = f"- [{title_value}]({paper['url']})"
                line += f" ({paper.get('year', 'n.d.')})"
                if paper.get("authors"):
                    line += f" - {paper['authors']}"
                line += f" - {paper.get('source', 'unknown')}"
                source_lines.append(line)
            content = "\n".join(source_lines) if source_lines else "- No sources added yet."
        else:
            cards = grouped.get(slug, [])
            content = "\n".join(_format_evidence_bullet(card) for card in cards) if cards else "- No evidence available yet."

        sections.append(
            {
                "slug": slug,
                "title": title,
                "content": content.strip(),
                "evidence_count": len(grouped.get(slug, [])),
                "is_locked": False,
                "locked_at": None,
                "lock_reason": "",
                "edited_at": generated_at,
                "edited_by": "system",
                "last_manual_edit_at": None,
                "updated_at": generated_at,
                "last_update_source": "generation",
            }
        )

    markdown = render_note_markdown(project_title, topic, sections)
    metadata_json = json.dumps(
        {
            "generated_at": generated_at,
            "provider_used": provider,
            "source_count": len(papers),
            "evidence_count": sum(len(items) for items in grouped.values()),
            "generation_mode": generation_mode,
        }
    )
    return markdown, sections_to_json(sections), metadata_json
