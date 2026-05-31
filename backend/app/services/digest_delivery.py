from __future__ import annotations

import json

from sqlmodel import Session

from ..models import WorkspaceDigest
from ..settings import settings
from ..time_utils import utc_now
from .digest_delivery_integrations import deliver_digest_via_email, deliver_digest_via_webhook
from .integrations import FileObsidianExportService, PlaceholderObsidianExportService


SUPPORTED_DIGEST_DELIVERY_TARGETS = {"download_markdown", "obsidian_placeholder", "obsidian_file", "email", "webhook"}


def get_obsidian_export_service(target: str):
    if target == "obsidian_file":
        return FileObsidianExportService(export_root=settings.obsidian_export_root)
    return PlaceholderObsidianExportService()


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
    elif requested_target == "email":
        result = deliver_digest_via_email(digest)
        payload = result
        digest.delivery_status = result.get("status", "sent")
        digest.delivery_target = requested_target
        digest.delivery_message = result.get("message", "Digest email was sent.")
        digest.delivered_at = utc_now()
    elif requested_target == "webhook":
        result = deliver_digest_via_webhook(digest)
        payload = result
        digest.delivery_status = result.get("status", "sent")
        digest.delivery_target = requested_target
        digest.delivery_message = result.get("message", "Digest webhook delivery completed.")
        digest.delivered_at = utc_now()
    else:
        obsidian = get_obsidian_export_service(requested_target)
        result = obsidian.export_digest(digest.markdown)
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
