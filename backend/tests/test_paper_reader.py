from __future__ import annotations


class MockResponse:
    def __init__(self, payload=None):
        self._payload = payload or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_read_cached_paper(client, auth_headers):
    project = client.post(
        "/projects",
        json={"title": "Reader Demo", "topic": "graph rag", "description": ""},
        headers=auth_headers,
    ).json()

    upload_response = client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={
            "title": "Seed Source",
            "text": "This paper studies retrieval augmented generation systems and compares benchmark settings.",
            "content_type": "abstract",
            "authors": "Uploaded by user",
            "year": 2026,
        },
        headers=auth_headers,
    )
    assert upload_response.status_code == 200

    project_detail = client.get(f"/projects/{project['id']}", headers=auth_headers)
    assert project_detail.status_code == 200
    external_id = project_detail.json()["papers"][0]["external_id"]

    response = client.post(
        "/papers/read",
        json={"external_id": external_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["external_id"] == external_id
    assert payload["source_metadata"]["research_os_cached_detail"] is True


def test_read_openalex_paper_from_remote(client, auth_headers, monkeypatch):
    payload = {
        "id": "https://openalex.org/W123",
        "display_name": "Test Paper",
        "publication_year": 2024,
        "authorships": [{"author": {"display_name": "Jane Doe"}}],
        "abstract_inverted_index": {"hello": [0], "world": [1]},
        "cited_by_count": 42,
        "primary_location": {"landing_page_url": "https://example.org/paper"},
        "open_access": {"oa_url": "https://example.org/pdf"},
    }

    monkeypatch.setattr("app.services.paper_reader.httpx.get", lambda *args, **kwargs: MockResponse(payload=payload))

    response = client.post(
        "/papers/read",
        json={"external_id": "https://openalex.org/W123"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["external_id"] == "https://openalex.org/W123"
    assert body["abstract"] == "hello world"
    assert body["source"] == "openalex"
    assert body["source_metadata"]["research_os_exact_read"] is True


def test_list_library_papers_for_current_user_projects(client, auth_headers):
    project_one = client.post(
        "/projects",
        json={"title": "Paper Project A", "topic": "graph rag", "description": ""},
        headers=auth_headers,
    ).json()
    project_two = client.post(
        "/projects",
        json={"title": "Paper Project B", "topic": "graph rag follow-up", "description": ""},
        headers=auth_headers,
    ).json()

    upload_response = client.post(
        f"/papers/projects/{project_one['id']}/upload-text",
        json={
            "title": "Seed Source",
            "text": "This paper studies retrieval augmented generation systems and compares benchmark settings.",
            "content_type": "abstract",
            "authors": "Uploaded by user",
            "year": 2026,
        },
        headers=auth_headers,
    )
    assert upload_response.status_code == 200

    project_detail = client.get(f"/projects/{project_one['id']}", headers=auth_headers)
    paper = project_detail.json()["papers"][0]

    add_response = client.post(
        f"/papers/projects/{project_two['id']}/add",
        json=paper,
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    library_response = client.get("/papers/library?query=seed&source=upload", headers=auth_headers)
    assert library_response.status_code == 200
    items = library_response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Seed Source"
    assert items[0]["project_count"] == 2
    assert {project["title"] for project in items[0]["linked_projects"]} == {"Paper Project A", "Paper Project B"}
