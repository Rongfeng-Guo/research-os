from __future__ import annotations

import json

from sqlmodel import Session

from ..models import WorkspaceDigest
from ..time_utils import utc_now
from .integrations import PlaceholderObsidianExportService


SUPPORTED_DIGEST_DELIVERY_TARGETS = {"download_markdown", "obsidian_placeholder"}


def deliver_digest(session: Session, *, digest: WorkspaceDigest, target: str) -> dict:
    requested_target = (target or "").strip().lower()
    if requested_target not in SUPPORTED_DIGEST_DELIVERY_TARGETS:
        raise ValueError("Unsupported digest delivery target")

    if requested_target == "download_markdown":
        metadata_filename = None
        try:
            metadata = json.loads(digest.metadata_json or "{}")
            metadata_filename = metadata.get("slug")
        except Exception:
            metadata_filename = None
        payload = {
            "filename": f"{metadata_filename or f'weekly-digest-{digest.id}'}.md",
            "content_type": "text/markdown",
            "content": digest.markdown,
        }
        digest.delivery_status = "prepared"
        digest.delivery_target = requested_target
        digest.delivery_message = "Digest markdown is ready for download."
        digest.delivered_at = utc_now()
    else:
        obsidian = PlaceholderObsidianExportService()
        result = obsidian.export_note(project_id=0, markdown=digest.markdown)
        payload = result
        digest.delivery_status = result.get("status", "prepared")
        digest.delivery_target = requested_target
        digest.delivery_message = result.get("message", "Digest export was prepared for Obsidian.")
        digest.delivered_at = utc_now()

    session.add(digest)
    session.commit()
    session.refresh(digest)
    return {
        "digest_id": digest.id,
        "status": digest.delivery_status,
        "target": digest.delivery_target,
        "message": digest.delivery_message,
        "delivered_at": digest.delivered_at,
        "payload": payload,
    }
