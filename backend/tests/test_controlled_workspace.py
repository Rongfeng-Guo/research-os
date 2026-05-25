from __future__ import annotations

from app.models import EvidenceCard
from app.routers.projects import _evidence_card_to_read
from app.time_utils import utc_now


def test_edit_evidence_card_and_pin_unpin(client, auth_headers):
    project = client.post(
        "/projects",
        json={"title": "Controlled Project", "topic": "retrieval systems", "description": ""},
        headers=auth_headers,
    ).json()
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Source", "text": "This paper proposes a retrieval method with limitations.", "content_type": "text"},
        headers=auth_headers,
    )
    extracted = client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers).json()
    card_id = extracted[0]["id"]

    update = client.patch(
        f"/evidence/{card_id}",
        json={
            "card_type": "claim",
            "content": "User-corrected evidence summary",
            "source_excerpt": "retrieval method with limitations",
            "user_note": "keep this for the weekly review",
            "is_pinned": True,
        },
        headers=auth_headers,
    )
    assert update.status_code == 200
    payload = update.json()
    assert payload["content"] == "User-corrected evidence summary"
    assert payload["user_note"] == "keep this for the weekly review"
    assert payload["is_pinned"] is True

    unpin = client.post(f"/evidence/{card_id}/unpin", headers=auth_headers)
    assert unpin.status_code == 200
    assert unpin.json()["is_pinned"] is False


def test_generation_mode_pinned_only(client, auth_headers):
    project = client.post(
        "/projects",
        json={"title": "Pinned Mode", "topic": "rag", "description": ""},
        headers=auth_headers,
    ).json()
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Source", "text": "This system uses retrieval and benchmark datasets.", "content_type": "text"},
        headers=auth_headers,
    )
    cards = client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers).json()
    first = cards[0]
    client.patch(
        f"/evidence/{first['id']}",
        json={"is_pinned": True, "review_status": "accepted"},
        headers=auth_headers,
    )
    for card in cards[1:]:
        client.patch(f"/evidence/{card['id']}", json={"review_status": "rejected"}, headers=auth_headers)

    note_response = client.post(
        f"/notes/projects/{project['id']}/generate?generation_mode=pinned_only",
        headers=auth_headers,
    )
    assert note_response.status_code == 200
    note = note_response.json()
    assert note["metadata"]["generation_mode"] == "pinned_only"
    assert first["content"] in note["markdown"]


def test_manual_section_edit_and_lock_blocks_apply(client, auth_headers, monkeypatch):
    project = client.post(
        "/projects",
        json={"title": "Locked Sections", "topic": "retrieval augmented generation", "description": ""},
        headers=auth_headers,
    ).json()
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Seed source", "text": "This source describes the first claim and method.", "content_type": "text"},
        headers=auth_headers,
    )
    client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    client.post(f"/notes/projects/{project['id']}/generate?generation_mode=accepted_only", headers=auth_headers)

    lock_response = client.patch(
        f"/notes/projects/{project['id']}/sections/claim",
        json={"content": "Manual locked claim section", "is_locked": True, "lock_reason": "Trusted manual rewrite"},
        headers=auth_headers,
    )
    assert lock_response.status_code == 200

    def fake_search(query: str, limit: int = 8):
        return [
            {
                "external_id": "refresh-locked-1",
                "title": "Fresh source",
                "abstract": "New claim evidence arrived.",
                "authors": "Author A",
                "year": 2025,
                "source": "mock",
                "url": "https://example.org/fresh",
                "content_text": "New claim evidence arrived with a new method and dataset.",
                "content_type": "abstract",
                "source_type": "paper",
                "origin": "search",
                "ingestion_status": "completed",
                "pdf_status": "pending",
                "extraction_status": "pending",
                "extraction_error": "",
                "source_metadata": {"provider": "mock"},
            }
        ]

    monkeypatch.setattr("app.services.refresh_workflow.search_papers", fake_search)
    refresh = client.post(f"/projects/{project['id']}/refresh", headers=auth_headers)
    assert refresh.status_code == 200
    suggestions = [item for item in refresh.json()["note_update_suggestions"] if item["target_section"] == "claim"]
    assert suggestions

    for suggestion in suggestions:
        client.patch(f"/notes/suggestions/{suggestion['id']}", json={"status": "accepted"}, headers=auth_headers)

    apply_response = client.post(
        f"/notes/projects/{project['id']}/apply-suggestions",
        json={"generation_mode": "accepted_only"},
        headers=auth_headers,
    )
    assert apply_response.status_code == 200
    note = apply_response.json()
    claim_section = next(section for section in note["sections"] if section["slug"] == "claim")
    assert claim_section["content"] == "Manual locked claim section"
    assert note["metadata"]["blocked_locked_suggestion_count"] >= 1


def test_apply_single_suggestion_creates_version_and_marks_applied(client, auth_headers, monkeypatch):
    project = client.post(
        "/projects",
        json={"title": "Single Suggestion", "topic": "retrieval agents", "description": ""},
        headers=auth_headers,
    ).json()
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Seed source", "text": "Initial retrieval claim.", "content_type": "text"},
        headers=auth_headers,
    )
    client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    client.post(f"/notes/projects/{project['id']}/generate?generation_mode=accepted_only", headers=auth_headers)

    def fake_search(query: str, limit: int = 8):
        return [
            {
                "external_id": "single-apply-1",
                "title": "New source",
                "abstract": "A new retrieval claim appears.",
                "authors": "Author B",
                "year": 2025,
                "source": "mock",
                "url": "https://example.org/new-source",
                "content_text": "A new retrieval claim appears with extra context.",
                "content_type": "abstract",
                "source_type": "paper",
                "origin": "search",
                "ingestion_status": "completed",
                "pdf_status": "pending",
                "extraction_status": "pending",
                "extraction_error": "",
                "source_metadata": {"provider": "mock"},
            }
        ]

    monkeypatch.setattr("app.services.refresh_workflow.search_papers", fake_search)
    refresh = client.post(f"/projects/{project['id']}/refresh", headers=auth_headers).json()
    suggestion = refresh["note_update_suggestions"][0]

    apply_response = client.post(
        f"/notes/suggestions/{suggestion['id']}/apply",
        json={"generation_mode": "accepted_only"},
        headers=auth_headers,
    )
    assert apply_response.status_code == 200

    suggestions = client.get(f"/notes/projects/{project['id']}/suggestions", headers=auth_headers).json()
    applied = next(item for item in suggestions if item["id"] == suggestion["id"])
    assert applied["status"] == "applied"
    assert applied["applied_by"] == "user"

    versions = client.get(f"/notes/projects/{project['id']}/versions", headers=auth_headers).json()
    assert versions[0]["version_kind"] == "apply_suggestion"
    assert suggestion["id"] in versions[0]["source_suggestion_ids"]


def test_apply_section_suggestions_only_updates_one_section(client, auth_headers, monkeypatch):
    project = client.post(
        "/projects",
        json={"title": "Section Apply", "topic": "multimodal retrieval", "description": ""},
        headers=auth_headers,
    ).json()
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Seed source", "text": "Initial claim and method.", "content_type": "text"},
        headers=auth_headers,
    )
    client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    client.post(f"/notes/projects/{project['id']}/generate?generation_mode=accepted_only", headers=auth_headers)

    def fake_search(query: str, limit: int = 8):
        return [
            {
                "external_id": "section-apply-1",
                "title": "Method paper",
                "abstract": "This work adds a method update.",
                "authors": "Author C",
                "year": 2025,
                "source": "mock",
                "url": "https://example.org/method",
                "content_text": "This work adds a method update for multimodal retrieval.",
                "content_type": "abstract",
                "source_type": "paper",
                "origin": "search",
                "ingestion_status": "completed",
                "pdf_status": "pending",
                "extraction_status": "pending",
                "extraction_error": "",
                "source_metadata": {"provider": "mock"},
            }
        ]

    monkeypatch.setattr("app.services.refresh_workflow.search_papers", fake_search)
    refresh = client.post(f"/projects/{project['id']}/refresh", headers=auth_headers).json()
    method_suggestions = [item for item in refresh["note_update_suggestions"] if item["target_section"] == "method"]
    for suggestion in method_suggestions:
        client.patch(f"/notes/suggestions/{suggestion['id']}", json={"status": "accepted"}, headers=auth_headers)

    apply_response = client.post(
        f"/notes/projects/{project['id']}/sections/method/apply-suggestions",
        json={"generation_mode": "accepted_only"},
        headers=auth_headers,
    )
    assert apply_response.status_code == 200
    note = apply_response.json()
    method_section = next(section for section in note["sections"] if section["slug"] == "method")
    assert method_section["last_update_source"] == "apply_suggestion"


def test_apply_selected_section_suggestions_only_uses_requested_ids(client, auth_headers, monkeypatch):
    project = client.post(
        "/projects",
        json={"title": "Selected Section Apply", "topic": "agent retrieval", "description": ""},
        headers=auth_headers,
    ).json()
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Seed source", "text": "Initial method baseline.", "content_type": "text"},
        headers=auth_headers,
    )
    client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    client.post(f"/notes/projects/{project['id']}/generate?generation_mode=accepted_only", headers=auth_headers)

    search_batches = iter(
        [
            [
                {
                    "external_id": "selected-method-1",
                    "title": "Method paper A",
                    "abstract": "Adds alpha method evidence.",
                    "authors": "Author D",
                    "year": 2025,
                    "source": "mock",
                    "url": "https://example.org/method-a",
                    "content_text": "Method update alpha with benchmark details.",
                    "content_type": "abstract",
                    "source_type": "paper",
                    "origin": "search",
                    "ingestion_status": "completed",
                    "pdf_status": "pending",
                    "extraction_status": "pending",
                    "extraction_error": "",
                    "source_metadata": {"provider": "mock"},
                }
            ],
            [
                {
                    "external_id": "selected-method-2",
                    "title": "Method paper B",
                    "abstract": "Adds beta method evidence.",
                    "authors": "Author E",
                    "year": 2025,
                    "source": "mock",
                    "url": "https://example.org/method-b",
                    "content_text": "Method update beta with deployment caveats.",
                    "content_type": "abstract",
                    "source_type": "paper",
                    "origin": "search",
                    "ingestion_status": "completed",
                    "pdf_status": "pending",
                    "extraction_status": "pending",
                    "extraction_error": "",
                    "source_metadata": {"provider": "mock"},
                }
            ],
        ]
    )

    def fake_search(query: str, limit: int = 8):
        return next(search_batches)

    monkeypatch.setattr("app.services.refresh_workflow.search_papers", fake_search)

    first_refresh = client.post(f"/projects/{project['id']}/refresh", headers=auth_headers)
    assert first_refresh.status_code == 200
    second_refresh = client.post(f"/projects/{project['id']}/refresh", headers=auth_headers)
    assert second_refresh.status_code == 200

    suggestions_response = client.get(f"/notes/projects/{project['id']}/suggestions", headers=auth_headers)
    assert suggestions_response.status_code == 200
    method_suggestions = [item for item in suggestions_response.json() if item["target_section"] == "method"]
    assert len(method_suggestions) >= 2

    for suggestion in method_suggestions:
        client.patch(f"/notes/suggestions/{suggestion['id']}", json={"status": "accepted"}, headers=auth_headers)

    selected = method_suggestions[0]
    apply_response = client.post(
        f"/notes/projects/{project['id']}/sections/method/apply-suggestions",
        json={"generation_mode": "accepted_only", "suggestion_ids": [selected["id"]]},
        headers=auth_headers,
    )
    assert apply_response.status_code == 200
    note = apply_response.json()
    assert note["metadata"]["source_suggestion_ids"] == [selected["id"]]

    suggestions = client.get(f"/notes/projects/{project['id']}/suggestions", headers=auth_headers).json()
    applied = [item for item in suggestions if item["status"] == "applied"]
    accepted = [item for item in suggestions if item["status"] == "accepted" and item["target_section"] == "method"]
    assert [item["id"] for item in applied] == [selected["id"]]
    assert accepted


def test_compare_versions_and_export_snapshot(client, auth_headers):
    project = client.post(
        "/projects",
        json={"title": "Compare Export", "topic": "rag", "description": ""},
        headers=auth_headers,
    ).json()
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Source", "text": "A claim and method for retrieval.", "content_type": "text"},
        headers=auth_headers,
    )
    client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    client.post(f"/notes/projects/{project['id']}/generate?generation_mode=accepted_only", headers=auth_headers)
    client.patch(
        f"/notes/projects/{project['id']}/sections/overview",
        json={"content": "Manual overview edit"},
        headers=auth_headers,
    )

    versions = client.get(f"/notes/projects/{project['id']}/versions", headers=auth_headers).json()
    compare = client.get(
        f"/notes/projects/{project['id']}/versions/{versions[1]['id']}/compare?against_version_id={versions[0]['id']}",
        headers=auth_headers,
    )
    assert compare.status_code == 200
    assert compare.json()["diff"]["blocks"]

    export_response = client.get(f"/projects/{project['id']}/export", headers=auth_headers)
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["project"]["id"] == project["id"]
    assert export_payload["topic_note"]["sections"]


def test_old_data_null_extracted_at_still_serializes():
    created_at = utc_now()
    legacy_card = EvidenceCard.model_construct(
        id=99,
        project_id=1,
        paper_id=1,
        card_type="claim",
        title="Legacy card",
        content="Legacy content",
        source_title="Legacy source",
        source_excerpt="Legacy snippet",
        source_url="",
        source_chunk_id="",
        source_section="",
        snippet_start=None,
        snippet_end=None,
        confidence_score=0.5,
        provider_name="mock",
        review_status="suggested",
        is_pinned=False,
        pinned_at=None,
        user_note="",
        edited_at=None,
        edited_by="",
        extraction_run_id=None,
        extracted_at=None,
        created_at=created_at,
    )

    serialized = _evidence_card_to_read(legacy_card)
    assert serialized.id == 99
    assert serialized.extracted_at == created_at
