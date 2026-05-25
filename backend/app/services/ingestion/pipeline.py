from __future__ import annotations

import json

from fastapi import HTTPException, UploadFile

from ...models import SourcePaper
from ...time_utils import utc_now
from .pdf_adapter import parse_pdf_bytes


def create_source_paper_from_text(
    *,
    title: str,
    text: str,
    origin: str,
    source_type: str,
    external_id: str,
    authors: str = "",
    year: int | None = None,
    url: str = "",
    source: str = "upload",
    metadata: dict | None = None,
) -> SourcePaper:
    normalized_text = text.strip()
    return SourcePaper(
        external_id=external_id,
        title=title.strip() or "Untitled source",
        abstract=normalized_text[:1200],
        authors=authors,
        year=year or utc_now().year,
        source=source,
        url=url,
        content_text=normalized_text,
        content_type=source_type,
        source_type=source_type,
        origin=origin,
        ingestion_status="completed" if normalized_text else "failed",
        extraction_status="pending",
        source_metadata=json.dumps(metadata or {}),
    )


async def ingest_uploaded_file(*, project_id: int, file: UploadFile) -> SourcePaper:
    filename = file.filename or "uploaded-source"
    content = await file.read()
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    external_id = f"upload-file-{project_id}-{int(utc_now().timestamp())}"

    if suffix == "pdf":
        parse_result = parse_pdf_bytes(content, filename)
        if parse_result.status != "parsed" or not parse_result.text.strip():
            raise HTTPException(status_code=422, detail=parse_result.error or "PDF parsing failed")
        paper = create_source_paper_from_text(
            title=filename,
            text=parse_result.text,
            origin="upload_file",
            source_type="pdf",
            external_id=external_id,
            metadata=parse_result.metadata,
        )
        paper.pdf_status = "parsed"
        return paper

    if suffix not in {"txt", "md", "markdown"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use .txt, .md, .markdown, or .pdf.")

    decoded = content.decode("utf-8", errors="ignore").strip()
    source_type = "markdown" if suffix in {"md", "markdown"} else "text"
    return create_source_paper_from_text(
        title=filename,
        text=decoded,
        origin="upload_file",
        source_type=source_type,
        external_id=external_id,
        metadata={"filename": filename},
    )
