from __future__ import annotations


def test_project_refresh_creates_new_sources_suggestions_and_update_run(client, auth_headers, monkeypatch):
    project = client.post(
        "/projects",
        json={"title": "Living Note", "topic": "retrieval augmented generation", "description": "refreshable"},
        headers=auth_headers,
    ).json()

    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Seed source", "text": "Initial source text for the topic.", "content_type": "text"},
        headers=auth_headers,
    )
    client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    client.post(f"/notes/projects/{project['id']}/generate?generation_mode=all_non_rejected", headers=auth_headers)

    def fake_search(query: str, limit: int = 8):
        return [
            {
                "external_id": "refresh-paper-1",
                "title": "A New Paper",
                "abstract": "This paper proposes a stronger retrieval augmented system.",
                "authors": "Author One",
                "year": 2025,
                "source": "mock",
                "url": "https://example.org/new-paper",
                "content_text": "This paper proposes a stronger retrieval augmented system and evaluates it on new benchmarks.",
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
    refresh_response = client.post(f"/projects/{project['id']}/refresh", headers=auth_headers)
    assert refresh_response.status_code == 200
    payload = refresh_response.json()
    assert any(run["run_type"] == "project_refresh" for run in payload["update_runs"])
    assert len(payload["note_update_suggestions"]) >= 1
    assert any(paper["external_id"] == "refresh-paper-1" for paper in payload["papers"])
    assert payload["note_update_suggestions"][0]["diff"]["blocks"]


def test_project_refresh_returns_500_and_marks_run_failed_when_workflow_errors(client, auth_headers, monkeypatch):
    project = client.post(
        "/projects",
        json={"title": "Broken Refresh", "topic": "failing topic", "description": ""},
        headers=auth_headers,
    ).json()

    def broken_search(*args, **kwargs):
        raise RuntimeError("paper provider timeout")

    monkeypatch.setattr("app.services.refresh_workflow.search_papers", broken_search)

    refresh_response = client.post(f"/projects/{project['id']}/refresh", headers=auth_headers)
    assert refresh_response.status_code == 500
    assert refresh_response.json()["detail"] == "Project refresh failed"

    detail = client.get(f"/projects/{project['id']}", headers=auth_headers)
    assert detail.status_code == 200
    refresh_runs = [run for run in detail.json()["update_runs"] if run["run_type"] == "project_refresh"]
    assert len(refresh_runs) == 1
    assert refresh_runs[0]["status"] == "failed"
    assert refresh_runs[0]["error_message"] == "paper provider timeout"


def test_apply_accepted_suggestions_creates_note_version(client, auth_headers):
    project = client.post(
        "/projects",
        json={"title": "Versioned Topic", "topic": "multimodal retrieval", "description": ""},
        headers=auth_headers,
    ).json()
    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Source", "text": "This source describes a multimodal retrieval method and new limitations.", "content_type": "text"},
        headers=auth_headers,
    )
    client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    client.post(f"/notes/projects/{project['id']}/generate?generation_mode=all_non_rejected", headers=auth_headers)

    detail = client.get(f"/projects/{project['id']}", headers=auth_headers).json()
    suggestion_id = detail["note_update_suggestions"][0]["id"] if detail["note_update_suggestions"] else None
    if suggestion_id is None:
        refresh_response = client.post(f"/projects/{project['id']}/refresh", headers=auth_headers)
        detail = refresh_response.json()
        suggestion_id = detail["note_update_suggestions"][0]["id"]

    review = client.patch(
        f"/notes/suggestions/{suggestion_id}",
        json={"status": "accepted"},
        headers=auth_headers,
    )
    assert review.status_code == 200

    apply_response = client.post(
        f"/notes/projects/{project['id']}/apply-suggestions",
        json={"generation_mode": "all_non_rejected"},
        headers=auth_headers,
    )
    assert apply_response.status_code == 200

    versions = client.get(f"/notes/projects/{project['id']}/versions", headers=auth_headers)
    assert versions.status_code == 200
    assert len(versions.json()) >= 2
