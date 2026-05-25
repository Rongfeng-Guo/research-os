from __future__ import annotations

import json
from datetime import datetime


NOTE_SECTION_ORDER = [
    ("overview", "Topic overview"),
    ("claim", "Key claims"),
    ("method", "Methods"),
    ("dataset", "Datasets / tasks"),
    ("limitation", "Limitations"),
    ("open_question", "Open questions"),
    ("sources", "Source summary"),
]

SECTION_TITLE_MAP = {slug: title for slug, title in NOTE_SECTION_ORDER}
SECTION_SLUG_BY_TITLE = {title: slug for slug, title in NOTE_SECTION_ORDER}


def _normalize_timestamp(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def default_sections() -> list[dict]:
    return [
        {
            "slug": slug,
            "title": title,
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
        for slug, title in NOTE_SECTION_ORDER
    ]


def parse_sections_json(raw: str | None) -> list[dict]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def parse_markdown_sections(markdown: str) -> dict[str, str]:
    section_bodies: dict[str, str] = {}
    for slug, title in NOTE_SECTION_ORDER:
        marker = f"## {title}"
        if marker not in markdown:
            continue
        tail = markdown.split(marker, 1)[1]
        next_section = tail.find("\n## ")
        body = tail[:next_section].strip() if next_section >= 0 else tail.strip()
        section_bodies[slug] = body
    return section_bodies


def normalize_note_sections(markdown: str, sections_json: str | None) -> list[dict]:
    stored = {section.get("slug"): section for section in parse_sections_json(sections_json)}
    parsed_content = parse_markdown_sections(markdown or "")
    sections: list[dict] = []
    for slug, title in NOTE_SECTION_ORDER:
        current = stored.get(slug, {})
        sections.append(
            {
                "slug": slug,
                "title": title,
                "content": current.get("content") or parsed_content.get(slug, ""),
                "evidence_count": current.get("evidence_count", 0),
                "is_locked": bool(current.get("is_locked", False)),
                "locked_at": _normalize_timestamp(current.get("locked_at")),
                "lock_reason": current.get("lock_reason", "") or "",
                "edited_at": _normalize_timestamp(current.get("edited_at")),
                "edited_by": current.get("edited_by", "") or "",
                "last_manual_edit_at": _normalize_timestamp(current.get("last_manual_edit_at")),
                "updated_at": _normalize_timestamp(current.get("updated_at") or current.get("edited_at")),
                "last_update_source": current.get("last_update_source", "") or "",
            }
        )
    return sections


def sections_to_json(sections: list[dict]) -> str:
    return json.dumps(sections)


def render_note_markdown(project_title: str, topic: str, sections: list[dict]) -> str:
    markdown_parts: list[str] = [f"# {project_title}", "", "## Topic", topic.strip(), ""]
    for section in sections:
        markdown_parts.append(f"## {section['title']}")
        markdown_parts.append("")
        content = (section.get("content") or "").strip()
        markdown_parts.append(content if content else "- No evidence available yet.")
        markdown_parts.append("")
    return "\n".join(markdown_parts).strip()


def merge_generated_sections(existing_sections: list[dict], generated_sections: list[dict]) -> list[dict]:
    existing_by_slug = {section["slug"]: section for section in existing_sections}
    merged: list[dict] = []
    for generated in generated_sections:
        current = existing_by_slug.get(generated["slug"], {})
        if current.get("is_locked"):
            merged.append(
                {
                    **generated,
                    "content": current.get("content", generated.get("content", "")),
                    "is_locked": True,
                    "locked_at": current.get("locked_at"),
                    "lock_reason": current.get("lock_reason", ""),
                    "edited_at": current.get("edited_at"),
                    "edited_by": current.get("edited_by", ""),
                    "last_manual_edit_at": current.get("last_manual_edit_at"),
                    "updated_at": current.get("updated_at"),
                    "last_update_source": current.get("last_update_source", "user"),
                }
            )
            continue
        merged.append(
            {
                **generated,
                "is_locked": bool(current.get("is_locked", False)),
                "locked_at": current.get("locked_at"),
                "lock_reason": current.get("lock_reason", ""),
                "edited_at": generated.get("edited_at") or current.get("edited_at"),
                "edited_by": generated.get("edited_by") or current.get("edited_by", "system"),
                "last_manual_edit_at": current.get("last_manual_edit_at"),
                "updated_at": generated.get("updated_at") or current.get("updated_at"),
                "last_update_source": generated.get("last_update_source") or current.get("last_update_source", "generation"),
            }
        )
    return merged


def get_section(sections: list[dict], slug: str) -> dict | None:
    for section in sections:
        if section["slug"] == slug:
            return section
    return None
