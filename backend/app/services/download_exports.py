from __future__ import annotations

import io
import json
import zipfile

from ..models import TopicNote, WorkspaceDigest
from .digest_service import digest_slug, digest_to_read
from .note_sections import normalize_note_sections


def build_digest_markdown_export(digest: WorkspaceDigest) -> tuple[str, bytes, str]:
    payload = digest_to_read(digest)
    metadata = payload.get("metadata") or {}
    filename = f"{metadata.get('slug') or f'weekly-digest-{digest.id}'}.md"
    return filename, digest.markdown.encode("utf-8"), "text/markdown; charset=utf-8"


def build_digest_bundle_export(digest: WorkspaceDigest) -> tuple[str, bytes, str]:
    payload = digest_to_read(digest)
    metadata = payload.get("metadata") or {}
    slug = metadata.get("slug") or f"weekly-digest-{digest.id}"
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{slug}/digest.md", digest.markdown)
        archive.writestr(f"{slug}/summary.json", json.dumps(payload["summary"], indent=2, ensure_ascii=False))
        archive.writestr(f"{slug}/metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))
    return f"{slug}.zip", zip_buffer.getvalue(), "application/zip"


def build_note_markdown_export(note: TopicNote) -> tuple[str, bytes, str]:
    slug = digest_slug(note.title or f"project-note-{note.project_id}")
    return f"{slug}.md", note.markdown.encode("utf-8"), "text/markdown; charset=utf-8"


def build_note_bundle_export(note: TopicNote) -> tuple[str, bytes, str]:
    slug = digest_slug(note.title or f"project-note-{note.project_id}")
    metadata = json.loads(note.metadata_json or "{}")
    sections = normalize_note_sections(note.markdown, note.sections_json)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{slug}/note.md", note.markdown)
        archive.writestr(
            f"{slug}/note.json",
            json.dumps(
                {
                    "id": note.id,
                    "project_id": note.project_id,
                    "title": note.title,
                    "metadata": metadata,
                    "sections": sections,
                    "updated_at": note.updated_at.isoformat(),
                },
                indent=2,
                ensure_ascii=False,
            ),
        )
        archive.writestr(f"{slug}/metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))
    return f"{slug}.zip", zip_buffer.getvalue(), "application/zip"
