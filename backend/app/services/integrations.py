from __future__ import annotations

from abc import ABC, abstractmethod

from .digest_service import digest_slug
from ..settings import settings


class ZoteroSyncService(ABC):
    @abstractmethod
    def sync_project(self, project_id: int) -> dict:
        raise NotImplementedError


class ObsidianExportService(ABC):
    @abstractmethod
    def export_note(self, project_id: int, markdown: str) -> dict:
        raise NotImplementedError


class PlaceholderZoteroSyncService(ZoteroSyncService):
    def sync_project(self, project_id: int) -> dict:
        return {
            "status": "not_implemented",
            "project_id": project_id,
            "message": "TODO: connect project papers and notes to Zotero collections and items.",
        }


class PlaceholderObsidianExportService(ObsidianExportService):
    def export_note(self, project_id: int, markdown: str) -> dict:
        export_label = f"weekly-digest-{project_id or 'workspace'}"
        filename = f"{digest_slug(export_label)}.md"
        export_dir = settings.obsidian_export_dir.strip().strip("/\\")
        relative_path = f"{export_dir}/{filename}" if export_dir else filename
        frontmatter = [
            "---",
            "source: research-os",
            "kind: workspace_digest",
            f"project_id: {project_id}",
            f"vault_path: {relative_path}",
            "---",
            "",
        ]
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
