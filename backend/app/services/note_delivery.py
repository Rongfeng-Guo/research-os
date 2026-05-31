from __future__ import annotations

from ..models import TopicNote
from ..settings import settings
from .integrations import FileObsidianExportService, PlaceholderObsidianExportService


SUPPORTED_NOTE_EXPORT_TARGETS = {"obsidian_placeholder", "obsidian_file"}


def get_obsidian_export_service(target: str):
    if target == "obsidian_file":
        return FileObsidianExportService(export_root=settings.obsidian_export_root)
    return PlaceholderObsidianExportService()


def export_project_note(*, note: TopicNote, target: str) -> dict:
    requested_target = (target or "").strip().lower()
    if requested_target not in SUPPORTED_NOTE_EXPORT_TARGETS:
        raise ValueError("Unsupported note export target")

    obsidian = get_obsidian_export_service(requested_target)
    payload = obsidian.export_project_note(note.project_id, note.title, note.markdown)
    return {
        "project_id": note.project_id,
        "note_id": note.id,
        "status": payload.get("status", "prepared"),
        "target": requested_target,
        "message": payload.get("message", "Project note export was prepared."),
        "payload": payload,
    }
