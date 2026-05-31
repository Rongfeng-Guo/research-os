from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .digest_service import digest_slug
from ..settings import settings


class ZoteroSyncService(ABC):
    @abstractmethod
    def sync_project(self, project_id: int) -> dict:
        raise NotImplementedError


class ObsidianExportService(ABC):
    @abstractmethod
    def export_digest(self, markdown: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def export_project_note(self, project_id: int, note_title: str, markdown: str) -> dict:
        raise NotImplementedError


class PlaceholderZoteroSyncService(ZoteroSyncService):
    def sync_project(self, project_id: int) -> dict:
        return {
            "status": "not_implemented",
            "project_id": project_id,
            "message": "TODO: connect project papers and notes to Zotero collections and items.",
        }


class PlaceholderObsidianExportService(ObsidianExportService):
    def _build_payload(
        self,
        *,
        project_id: int,
        markdown: str,
        export_label: str,
        kind: str,
        export_dir: str | None = None,
        extra_frontmatter: dict[str, str | int] | None = None,
    ) -> dict:
        resolved_export_dir = (export_dir if export_dir is not None else settings.obsidian_export_dir).strip().strip("/\\")
        filename = f"{digest_slug(export_label)}.md"
        relative_path = f"{resolved_export_dir}/{filename}" if resolved_export_dir else filename
        frontmatter = [
            "---",
            "source: research-os",
            f"kind: {kind}",
            f"project_id: {project_id}",
            f"vault_path: {relative_path}",
        ]
        for key, value in (extra_frontmatter or {}).items():
            frontmatter.append(f"{key}: {value}")
        frontmatter.extend(["---", ""])
        rendered_markdown = "\n".join(frontmatter) + markdown.strip() + "\n"
        return {
            "status": "prepared",
            "project_id": project_id,
            "message": f"Prepared an Obsidian-ready markdown export for {relative_path}.",
            "vault_relative_path": relative_path,
            "filename": filename,
            "content_type": "text/markdown",
            "content": rendered_markdown,
            "preview_length": len(rendered_markdown),
        }

    def export_digest(self, markdown: str) -> dict:
        return self._build_payload(
            project_id=0,
            markdown=markdown,
            export_label="weekly-digest-workspace",
            kind="workspace_digest",
        )

    def export_project_note(self, project_id: int, note_title: str, markdown: str) -> dict:
        return self._build_payload(
            project_id=project_id,
            markdown=markdown,
            export_label=note_title or f"project-note-{project_id}",
            kind="topic_note",
            extra_frontmatter={"note_title": note_title or f"Project Note {project_id}"},
        )


class FileObsidianExportService(PlaceholderObsidianExportService):
    def __init__(self, *, export_root: str | Path, export_dir: str | None = None):
        self.export_root = Path(export_root).expanduser()
        self.export_dir = (export_dir if export_dir is not None else settings.obsidian_export_dir).strip().strip("/\\")

    def _write_payload(self, payload: dict) -> dict:
        if not str(self.export_root).strip():
            raise ValueError("OBSIDIAN_EXPORT_ROOT must be configured for file export")

        target_dir = self.export_root / self.export_dir if self.export_dir else self.export_root
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / payload["filename"]
        target_path.write_text(payload["content"], encoding="utf-8")
        payload["export_root"] = str(self.export_root)
        payload["absolute_path"] = str(target_path.resolve())
        payload["bytes_written"] = target_path.stat().st_size
        payload["status"] = "written"
        payload["message"] = f"Wrote an Obsidian-ready markdown export to {target_path.resolve()}."
        return payload

    def export_digest(self, markdown: str) -> dict:
        payload = self._build_payload(
            project_id=0,
            markdown=markdown,
            export_label="weekly-digest-workspace",
            kind="workspace_digest",
            export_dir=self.export_dir,
        )
        return self._write_payload(payload)

    def export_project_note(self, project_id: int, note_title: str, markdown: str) -> dict:
        payload = self._build_payload(
            project_id=project_id,
            markdown=markdown,
            export_label=note_title or f"project-note-{project_id}",
            kind="topic_note",
            export_dir=self.export_dir,
            extra_frontmatter={"note_title": note_title or f"Project Note {project_id}"},
        )
        return self._write_payload(payload)
