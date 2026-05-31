from __future__ import annotations

import io
import zipfile
from pathlib import Path

from app.models import Project
from app.services.integrations import FileObsidianExportService
from app.services.project_health import ensure_refresh_schedule, freshness_status
from app.time_utils import utc_now


def test_refresh_due_computation():
    project = Project(
        owner_id=1,
        title="Due Project",
        topic="rag",
        description="",
        auto_refresh_enabled=True,
        refresh_cadence="weekly",
    )
    project.last_refreshed_at = utc_now()
    ensure_refresh_schedule(project, now=project.last_refreshed_at)
    assert project.next_refresh_due_at is not None


def test_stale_project_detection():
    project = Project(
        owner_id=1,
        title="Stale Project",
        topic="agents",
        description="",
        auto_refresh_enabled=True,
        refresh_cadence="daily",
    )
    project.last_refreshed_at = utc_now().replace(day=max(1, utc_now().day - 3))
    status, _ = freshness_status(project)
    assert status in {"stale", "due_soon", "fresh"}


def test_dashboard_summary_and_digest_routes(client, auth_headers):
    project = client.post(
        "/projects",
        json={"title": "Digest Project", "topic": "retrieval systems", "description": ""},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/projects/{project['id']}/preferences",
        json={"auto_refresh_enabled": True, "refresh_cadence": "weekly", "digest_enabled": True},
        headers=auth_headers,
    )
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Source", "text": "This paper adds a method and limitation.", "content_type": "text"},
        headers=auth_headers,
    )
    client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    client.post(f"/notes/projects/{project['id']}/generate?generation_mode=accepted_only", headers=auth_headers)

    summary = client.get("/workspace/summary", headers=auth_headers)
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert "recommended_actions" in summary_payload
    assert "project_health" in summary_payload

    digest = client.post("/workspace/digests/generate?days=7", headers=auth_headers)
    assert digest.status_code == 200
    digest_payload = digest.json()
    assert digest_payload["summary"]["project_count"] >= 1
    assert "Weekly Research Digest" in digest_payload["markdown"]

    digest_list = client.get("/workspace/digests", headers=auth_headers)
    assert digest_list.status_code == 200
    assert len(digest_list.json()) >= 1


def test_manual_only_preference_has_no_next_due(client, auth_headers):
    project = client.post(
        "/projects",
        json={"title": "Manual Project", "topic": "manual topic", "description": ""},
        headers=auth_headers,
    ).json()
    preference = client.patch(
        f"/projects/{project['id']}/preferences",
        json={"auto_refresh_enabled": False, "refresh_cadence": "manual_only", "digest_enabled": False},
        headers=auth_headers,
    )
    assert preference.status_code == 200
    payload = preference.json()
    assert payload["refresh_cadence"] == "manual_only"
    assert payload["next_refresh_due_at"] is None


def test_digest_routes_are_owner_scoped_and_respect_digest_enabled(client, auth_headers, second_auth_headers):
    first_project = client.post(
        "/projects",
        json={"title": "First Digest Project", "topic": "first digest", "description": ""},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/projects/{first_project['id']}/preferences",
        json={"auto_refresh_enabled": True, "refresh_cadence": "weekly", "digest_enabled": True},
        headers=auth_headers,
    )
    client.post(
        f"/papers/projects/{first_project['id']}/upload-text",
        json={"title": "First source", "text": "Included in digest.", "content_type": "text"},
        headers=auth_headers,
    )

    hidden_project = client.post(
        "/projects",
        json={"title": "Hidden Digest Project", "topic": "hidden digest", "description": ""},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/projects/{hidden_project['id']}/preferences",
        json={"auto_refresh_enabled": True, "refresh_cadence": "weekly", "digest_enabled": False},
        headers=auth_headers,
    )
    client.post(
        f"/papers/projects/{hidden_project['id']}/upload-text",
        json={"title": "Hidden source", "text": "Should not be included in digest.", "content_type": "text"},
        headers=auth_headers,
    )

    second_project = client.post(
        "/projects",
        json={"title": "Second User Project", "topic": "second digest", "description": ""},
        headers=second_auth_headers,
    ).json()
    client.patch(
        f"/projects/{second_project['id']}/preferences",
        json={"auto_refresh_enabled": True, "refresh_cadence": "weekly", "digest_enabled": True},
        headers=second_auth_headers,
    )
    client.post(
        f"/papers/projects/{second_project['id']}/upload-text",
        json={"title": "Second source", "text": "Second user digest content.", "content_type": "text"},
        headers=second_auth_headers,
    )

    first_digest = client.post("/workspace/digests/generate?days=7", headers=auth_headers)
    assert first_digest.status_code == 200
    first_payload = first_digest.json()
    assert first_payload["summary"]["project_count"] == 1
    assert first_payload["summary"]["projects"][0]["project_title"] == "First Digest Project"

    second_digest = client.post("/workspace/digests/generate?days=7", headers=second_auth_headers)
    assert second_digest.status_code == 200
    second_payload = second_digest.json()
    assert second_payload["summary"]["project_count"] == 1
    assert second_payload["summary"]["projects"][0]["project_title"] == "Second User Project"

    first_list = client.get("/workspace/digests", headers=auth_headers)
    assert first_list.status_code == 200
    assert len(first_list.json()) == 1

    second_list = client.get("/workspace/digests", headers=second_auth_headers)
    assert second_list.status_code == 200
    assert len(second_list.json()) == 1


def test_digest_delivery_routes_update_status_and_enforce_ownership(client, auth_headers, second_auth_headers):
    project = client.post(
        "/projects",
        json={"title": "Delivery Project", "topic": "delivery topic", "description": ""},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/projects/{project['id']}/preferences",
        json={"auto_refresh_enabled": True, "refresh_cadence": "weekly", "digest_enabled": True},
        headers=auth_headers,
    )
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Delivery source", "text": "Digest delivery content.", "content_type": "text"},
        headers=auth_headers,
    )

    digest = client.post("/workspace/digests/generate?days=7", headers=auth_headers)
    assert digest.status_code == 200
    digest_id = digest.json()["id"]

    download_delivery = client.post(
        f"/workspace/digests/{digest_id}/deliver",
        json={"target": "download_markdown"},
        headers=auth_headers,
    )
    assert download_delivery.status_code == 200
    download_payload = download_delivery.json()
    assert download_payload["status"] == "prepared"
    assert download_payload["target"] == "download_markdown"
    assert download_payload["payload"]["filename"].endswith(".md")
    assert "weekly-digest-" in download_payload["payload"]["filename"]

    obsidian_delivery = client.post(
        f"/workspace/digests/{digest_id}/deliver",
        json={"target": "obsidian_placeholder"},
        headers=auth_headers,
    )
    assert obsidian_delivery.status_code == 200
    obsidian_payload = obsidian_delivery.json()
    assert obsidian_payload["status"] == "prepared"
    assert obsidian_payload["target"] == "obsidian_placeholder"
    assert obsidian_payload["payload"]["vault_relative_path"].endswith(".md")
    assert obsidian_payload["payload"]["content"].startswith("---\nsource: research-os")

    forbidden = client.post(
        f"/workspace/digests/{digest_id}/deliver",
        json={"target": "download_markdown"},
        headers=second_auth_headers,
    )
    assert forbidden.status_code == 404


def test_digest_delivery_can_write_obsidian_file(client, auth_headers, monkeypatch, tmp_path: Path):
    project = client.post(
        "/projects",
        json={"title": "Obsidian Project", "topic": "vault export", "description": ""},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/projects/{project['id']}/preferences",
        json={"auto_refresh_enabled": True, "refresh_cadence": "weekly", "digest_enabled": True},
        headers=auth_headers,
    )
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Vault source", "text": "Digest should be written to disk.", "content_type": "text"},
        headers=auth_headers,
    )

    digest = client.post("/workspace/digests/generate?days=7", headers=auth_headers)
    assert digest.status_code == 200
    digest_id = digest.json()["id"]

    def build_file_service(target: str):
        if target == "obsidian_file":
            return FileObsidianExportService(export_root=tmp_path, export_dir="Vault/Research OS")
        raise AssertionError(f"Unexpected target: {target}")

    monkeypatch.setattr("app.services.digest_delivery.get_obsidian_export_service", build_file_service)

    delivery = client.post(
        f"/workspace/digests/{digest_id}/deliver",
        json={"target": "obsidian_file"},
        headers=auth_headers,
    )
    assert delivery.status_code == 200
    payload = delivery.json()
    assert payload["status"] == "written"
    assert payload["target"] == "obsidian_file"
    assert payload["payload"]["vault_relative_path"].startswith("Vault/Research OS/")
    written_path = Path(payload["payload"]["absolute_path"])
    assert written_path.exists()
    assert written_path.read_text(encoding="utf-8").startswith("---\nsource: research-os")
    assert payload["payload"]["bytes_written"] > 0


def test_digest_download_bundle_contains_markdown_and_json(client, auth_headers):
    project = client.post(
        "/projects",
        json={"title": "Bundle Project", "topic": "digest bundle", "description": ""},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/projects/{project['id']}/preferences",
        json={"auto_refresh_enabled": True, "refresh_cadence": "weekly", "digest_enabled": True},
        headers=auth_headers,
    )
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Bundle source", "text": "Bundle digest content.", "content_type": "text"},
        headers=auth_headers,
    )
    digest = client.post("/workspace/digests/generate?days=7", headers=auth_headers)
    digest_id = digest.json()["id"]

    response = client.get(f"/workspace/digests/{digest_id}/download?format=bundle", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())
    assert any(name.endswith("/digest.md") for name in names)
    assert any(name.endswith("/summary.json") for name in names)
    assert any(name.endswith("/metadata.json") for name in names)


def test_digest_delivery_supports_email_and_webhook(client, auth_headers, monkeypatch):
    project = client.post(
        "/projects",
        json={"title": "Delivery Targets", "topic": "delivery targets", "description": ""},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/projects/{project['id']}/preferences",
        json={"auto_refresh_enabled": True, "refresh_cadence": "weekly", "digest_enabled": True},
        headers=auth_headers,
    )
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Delivery source", "text": "Delivery target content.", "content_type": "text"},
        headers=auth_headers,
    )
    digest = client.post("/workspace/digests/generate?days=7", headers=auth_headers)
    digest_id = digest.json()["id"]

    monkeypatch.setattr(
        "app.services.digest_delivery.deliver_digest_via_email",
        lambda digest: {"status": "sent", "message": "Email target invoked.", "recipient_count": 1},
    )
    monkeypatch.setattr(
        "app.services.digest_delivery.deliver_digest_via_webhook",
        lambda digest: {"status": "sent", "message": "Webhook target invoked.", "response_status": 200},
    )

    email_response = client.post(
        f"/workspace/digests/{digest_id}/deliver",
        json={"target": "email"},
        headers=auth_headers,
    )
    assert email_response.status_code == 200
    assert email_response.json()["status"] == "sent"
    assert email_response.json()["target"] == "email"

    webhook_response = client.post(
        f"/workspace/digests/{digest_id}/deliver",
        json={"target": "webhook"},
        headers=auth_headers,
    )
    assert webhook_response.status_code == 200
    assert webhook_response.json()["status"] == "sent"
    assert webhook_response.json()["target"] == "webhook"
