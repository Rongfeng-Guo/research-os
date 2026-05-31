from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage

import httpx

from ..models import WorkspaceDigest
from ..settings import settings
from .digest_service import digest_to_read


def deliver_digest_via_email(digest: WorkspaceDigest) -> dict:
    if not settings.smtp_host or not settings.smtp_from_email or not settings.smtp_to_emails:
        raise ValueError("SMTP_HOST, SMTP_FROM_EMAIL, and SMTP_TO_EMAILS must be configured for email delivery")

    payload = digest_to_read(digest)
    message = EmailMessage()
    message["Subject"] = f"Research OS Digest {payload['period_start'].date().isoformat()} to {payload['period_end'].date().isoformat()}"
    message["From"] = settings.smtp_from_email
    message["To"] = ", ".join(settings.smtp_to_emails)
    message.set_content(digest.markdown)
    message.add_attachment(
        digest.markdown.encode("utf-8"),
        maintype="text",
        subtype="markdown",
        filename=f"{(payload.get('metadata') or {}).get('slug') or f'weekly-digest-{digest.id}'}.md",
    )

    smtp_cls = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
    with smtp_cls(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls and not settings.smtp_use_ssl:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)

    return {
        "status": "sent",
        "message": f"Delivered digest email to {', '.join(settings.smtp_to_emails)}.",
        "recipient_count": len(settings.smtp_to_emails),
        "recipients": settings.smtp_to_emails,
        "subject": message["Subject"],
    }


def deliver_digest_via_webhook(digest: WorkspaceDigest) -> dict:
    if not settings.digest_webhook_url:
        raise ValueError("DIGEST_WEBHOOK_URL must be configured for webhook delivery")

    payload = digest_to_read(digest)
    body = {
        "digest_id": digest.id,
        "period_start": payload["period_start"].isoformat(),
        "period_end": payload["period_end"].isoformat(),
        "summary": payload["summary"],
        "metadata": payload["metadata"],
        "markdown": digest.markdown,
    }
    response = httpx.post(
        settings.digest_webhook_url,
        json=body,
        headers={"Content-Type": "application/json", "User-Agent": "research-os/0.1.0"},
        timeout=settings.digest_webhook_timeout_seconds,
    )
    response.raise_for_status()
    response_preview = response.text[:400]
    return {
        "status": "sent",
        "message": f"Delivered digest payload to webhook {settings.digest_webhook_url}.",
        "webhook_url": settings.digest_webhook_url,
        "response_status": response.status_code,
        "response_preview": response_preview,
        "request_bytes": len(json.dumps(body).encode("utf-8")),
    }
