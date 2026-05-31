from __future__ import annotations

from io import BytesIO
import io
from pathlib import Path
import zipfile

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.services.integrations import FileObsidianExportService


def _build_test_pdf_bytes(text: str | list[str]) -> bytes:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page_texts = text if isinstance(text, list) else [text]

    for page_text in page_texts:
        page = writer.add_blank_page(width=420, height=640)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref}),
            }
        )
        commands = ["BT", "/F1 14 Tf", "36 580 Td"]
        lines = page_text.splitlines() or [page_text]
        for index, line in enumerate(lines):
            encoded_text = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if index > 0:
                commands.append("0 -18 Td")
            commands.append(f"({encoded_text}) Tj")
        commands.append("ET")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(commands).encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_source_upload_extract_note_and_project_detail(client: TestClient, auth_headers: dict[str, str]):
    project = client.post(
        "/projects",
        json={"title": "Demo Project", "topic": "retrieval augmented generation", "description": "demo"},
        headers=auth_headers,
    ).json()

    upload_response = client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={
            "title": "Uploaded abstract",
            "text": "This study proposes a retrieval augmented generation system evaluated on QA benchmarks.",
            "content_type": "abstract",
            "authors": "Researcher A",
            "year": 2024,
            "url": "https://example.org/uploaded-source",
        },
        headers=auth_headers,
    )
    assert upload_response.status_code == 200

    extract_response = client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    assert extract_response.status_code == 200
    evidence_cards = extract_response.json()
    assert len(evidence_cards) >= 1
    assert evidence_cards[0]["source_excerpt"]
    assert evidence_cards[0]["review_status"] == "suggested"

    update_response = client.patch(
        f"/evidence/{evidence_cards[0]['id']}",
        json={"review_status": "accepted"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["review_status"] == "accepted"

    note_response = client.post(f"/notes/projects/{project['id']}/generate", headers=auth_headers)
    assert note_response.status_code == 200
    assert "Source:" in note_response.json()["markdown"]
    assert note_response.json()["metadata"]["source_count"] == 1
    assert note_response.json()["metadata"]["generation_mode"] == "accepted_only"

    project_detail = client.get(f"/projects/{project['id']}", headers=auth_headers)
    assert project_detail.status_code == 200
    payload = project_detail.json()
    assert payload["papers"][0]["ingestion_status"] == "completed"
    assert payload["papers"][0]["extraction_status"] in {"completed", "partial"}
    assert payload["topic_note"]["metadata"]["evidence_count"] >= 1


def test_upload_markdown_file(client: TestClient, auth_headers: dict[str, str]):
    project = client.post(
        "/projects",
        json={"title": "File Project", "topic": "agentic search", "description": ""},
        headers=auth_headers,
    ).json()

    response = client.post(
        f"/papers/projects/{project['id']}/upload-file",
        headers=auth_headers,
        files={"file": ("notes.md", b"# Notes\n\nThis source discusses agentic search systems.", "text/markdown")},
    )
    assert response.status_code == 200
    assert response.json()["source_type"] == "markdown"


def test_upload_pdf_file_and_extract_text(client: TestClient, auth_headers: dict[str, str]):
    project = client.post(
        "/projects",
        json={"title": "PDF Project", "topic": "pdf ingestion", "description": ""},
        headers=auth_headers,
    ).json()

    pdf_bytes = _build_test_pdf_bytes(
        [
            "ABSTRACT\nHello PDF World",
            "METHODS\nWe evaluate the parser with section-aware extraction context.",
        ]
    )
    response = client.post(
        f"/papers/projects/{project['id']}/upload-file",
        headers=auth_headers,
        files={"file": ("paper.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["source_type"] == "pdf"

    detail = client.get(f"/projects/{project['id']}", headers=auth_headers)
    assert detail.status_code == 200
    paper = detail.json()["papers"][0]
    assert paper["source_type"] == "pdf"
    assert paper["content_type"] == "pdf"
    assert paper["pdf_status"] == "parsed"
    assert "Hello PDF World" in paper["content_text"]
    assert "## Abstract" in paper["content_text"]
    assert paper["source_metadata"]["parser"] == "pypdf"
    assert paper["source_metadata"]["page_count"] == 2
    assert paper["source_metadata"]["section_count"] == 2
    assert paper["source_metadata"]["detected_sections"] == ["Abstract", "Methods"]
    assert paper["source_metadata"]["pages"][0]["section_titles"] == ["Abstract"]
    assert paper["source_metadata"]["pages"][1]["section_titles"] == ["Methods"]


def test_upload_pdf_file_can_flow_into_extraction(client: TestClient, auth_headers: dict[str, str]):
    project = client.post(
        "/projects",
        json={"title": "PDF Extraction", "topic": "retrieval pdf", "description": ""},
        headers=auth_headers,
    ).json()

    pdf_bytes = _build_test_pdf_bytes(
        "ABSTRACT\nThis PDF describes a retrieval method and an evaluation dataset."
    )
    upload = client.post(
        f"/papers/projects/{project['id']}/upload-file",
        headers=auth_headers,
        files={"file": ("retrieval.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload.status_code == 200

    extract = client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    assert extract.status_code == 200
    cards = extract.json()
    assert cards
    assert any(card["source_excerpt"] for card in cards)
    assert any(card["source_section"] == "Abstract" for card in cards)


def test_export_and_import_project_snapshot(client: TestClient, auth_headers: dict[str, str]):
    project = client.post(
        "/projects",
        json={"title": "Snapshot Source", "topic": "literature maintenance", "description": "source project"},
        headers=auth_headers,
    ).json()

    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={
            "title": "Snapshot source text",
            "text": "This source contains a claim, method, and limitation for import testing.",
            "content_type": "text",
        },
        headers=auth_headers,
    )
    extracted = client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    assert extracted.status_code == 200
    cards = extracted.json()
    assert cards
    client.patch(
        f"/evidence/{cards[0]['id']}",
        json={"review_status": "accepted", "is_pinned": True, "user_note": "Preserve this in snapshot"},
        headers=auth_headers,
    )
    generated = client.post(f"/notes/projects/{project['id']}/generate", headers=auth_headers)
    assert generated.status_code == 200

    snapshot = client.get(f"/projects/{project['id']}/export", headers=auth_headers)
    assert snapshot.status_code == 200

    imported = client.post(
        "/projects/import",
        json={"snapshot": snapshot.json(), "title_suffix": " (Restored)"},
        headers=auth_headers,
    )
    assert imported.status_code == 200
    imported_project = imported.json()
    assert imported_project["title"].endswith("(Restored)")

    imported_detail = client.get(f"/projects/{imported_project['id']}", headers=auth_headers)
    assert imported_detail.status_code == 200
    payload = imported_detail.json()
    assert len(payload["papers"]) == 1
    assert len(payload["evidence_cards"]) >= 1
    assert payload["topic_note"] is not None
    assert payload["note_versions"]
    assert payload["papers"][0]["origin"] == "import_snapshot"
    assert any(card["is_pinned"] for card in payload["evidence_cards"])


def test_export_project_note_to_obsidian_file(client: TestClient, auth_headers: dict[str, str], monkeypatch, tmp_path: Path):
    project = client.post(
        "/projects",
        json={"title": "Exported Note Project", "topic": "knowledge capture", "description": ""},
        headers=auth_headers,
    ).json()

    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={
            "title": "Note source",
            "text": "This source should appear in the exported project note.",
            "content_type": "text",
        },
        headers=auth_headers,
    )
    client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    note_response = client.post(f"/notes/projects/{project['id']}/generate", headers=auth_headers)
    assert note_response.status_code == 200

    def build_file_service(target: str):
        if target == "obsidian_file":
            return FileObsidianExportService(export_root=tmp_path, export_dir="Vault/Research OS")
        raise AssertionError(f"Unexpected target: {target}")

    monkeypatch.setattr("app.services.note_delivery.get_obsidian_export_service", build_file_service)

    export_response = client.post(
        f"/notes/projects/{project['id']}/export",
        json={"target": "obsidian_file"},
        headers=auth_headers,
    )
    assert export_response.status_code == 200
    payload = export_response.json()
    assert payload["project_id"] == project["id"]
    assert payload["status"] == "written"
    assert payload["target"] == "obsidian_file"
    assert payload["payload"]["vault_relative_path"].startswith("Vault/Research OS/")
    assert payload["payload"]["filename"].endswith(".md")
    written_path = Path(payload["payload"]["absolute_path"])
    assert written_path.exists()
    written_content = written_path.read_text(encoding="utf-8")
    assert "kind: topic_note" in written_content
    assert "note_title: Exported Note Project Research Note" in written_content


def test_download_project_note_bundle(client: TestClient, auth_headers: dict[str, str]):
    project = client.post(
        "/projects",
        json={"title": "Bundle Note Project", "topic": "note bundle", "description": ""},
        headers=auth_headers,
    ).json()

    client.post(
        f"/papers/projects/{project['id']}/upload-text",
        json={"title": "Source", "text": "Bundle note content.", "content_type": "text"},
        headers=auth_headers,
    )
    client.post(f"/papers/projects/{project['id']}/extract", headers=auth_headers)
    client.post(f"/notes/projects/{project['id']}/generate", headers=auth_headers)

    response = client.get(f"/notes/projects/{project['id']}/download?format=bundle", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())
    assert any(name.endswith("/note.md") for name in names)
    assert any(name.endswith("/note.json") for name in names)
    assert any(name.endswith("/metadata.json") for name in names)
