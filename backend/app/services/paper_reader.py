from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import httpx
from sqlmodel import Session, select

from ..models import SourcePaper
from ..settings import settings
from .paper_discovery.base import PaperRecord
from .paper_discovery.openalex_provider import _reconstruct_abstract


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def read_paper_by_external_id(session: Session, external_id: str) -> PaperRecord:
    candidate = (external_id or "").strip()
    if not candidate:
        raise ValueError("external_id is required")

    cached = _read_cached_paper(session, candidate)
    if cached is not None:
        return cached

    provider = _detect_provider(candidate)
    if provider == "openalex":
        return _read_openalex_paper(candidate)
    if provider == "arxiv":
        return _read_arxiv_paper(candidate)

    raise LookupError(f"Paper not found for external_id={candidate}")


def _read_cached_paper(session: Session, external_id: str) -> PaperRecord | None:
    paper = session.exec(select(SourcePaper).where(SourcePaper.external_id == external_id)).first()
    if not paper:
        return None

    source_metadata = _parse_source_metadata(paper.source_metadata)
    return PaperRecord(
        external_id=paper.external_id,
        title=paper.title,
        abstract=paper.abstract,
        authors=paper.authors,
        year=paper.year,
        source=paper.source,
        url=paper.url,
        content_text=paper.content_text,
        content_type=paper.content_type,
        source_type=paper.source_type,
        origin=paper.origin,
        ingestion_status=paper.ingestion_status,
        pdf_status=paper.pdf_status,
        extraction_status=paper.extraction_status,
        extraction_error=paper.extraction_error,
        source_metadata={
            **source_metadata,
            "research_os_cached_detail": True,
        },
    )


def _read_openalex_paper(external_id: str) -> PaperRecord:
    normalized = _normalize_openalex_external_id(external_id)
    params: dict[str, str] = {}
    if settings.openalex_email:
        params["mailto"] = settings.openalex_email

    response = httpx.get(
        f"https://api.openalex.org/works/{normalized}",
        params=params,
        timeout=settings.paper_discovery_timeout_seconds,
        headers={"User-Agent": "research-os-mvp/0.2"},
    )
    response.raise_for_status()
    payload = response.json()

    authors = ", ".join(
        authorship.get("author", {}).get("display_name", "")
        for authorship in payload.get("authorships", [])
        if authorship.get("author", {}).get("display_name")
    )
    abstract = _reconstruct_abstract(payload.get("abstract_inverted_index"))
    paper_url = payload.get("primary_location", {}).get("landing_page_url") or payload.get("id", "")

    return PaperRecord(
        external_id=external_id,
        title=payload.get("display_name", "Untitled paper"),
        abstract=abstract,
        authors=authors,
        year=payload.get("publication_year") or 2025,
        source="openalex",
        url=paper_url,
        content_text=abstract,
        source_type="paper",
        origin="search",
        source_metadata={
            "provider": "openalex",
            "research_os_exact_read": True,
            "cited_by_count": payload.get("cited_by_count", 0),
            "open_access_url": payload.get("open_access", {}).get("oa_url", ""),
            "normalized_external_id": normalized,
        },
    )


def _read_arxiv_paper(external_id: str) -> PaperRecord:
    normalized = _normalize_arxiv_external_id(external_id)
    response = httpx.get(
        "https://export.arxiv.org/api/query",
        params={"id_list": normalized},
        timeout=settings.paper_discovery_timeout_seconds,
        headers={"User-Agent": "research-os-mvp/0.2"},
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    entry = root.find("atom:entry", ATOM_NS)
    if entry is None:
        raise LookupError(f"ArXiv paper not found for external_id={external_id}")

    entry_id = entry.findtext("atom:id", default="", namespaces=ATOM_NS)
    title = " ".join(entry.findtext("atom:title", default="", namespaces=ATOM_NS).split())
    summary = " ".join(entry.findtext("atom:summary", default="", namespaces=ATOM_NS).split())
    published = entry.findtext("atom:published", default="", namespaces=ATOM_NS)
    authors = ", ".join(
        author.findtext("atom:name", default="", namespaces=ATOM_NS)
        for author in entry.findall("atom:author", ATOM_NS)
    )
    year = int(published[:4]) if published[:4].isdigit() else 2025

    return PaperRecord(
        external_id=external_id,
        title=title or "Untitled paper",
        abstract=summary,
        authors=authors,
        year=year,
        source="arxiv",
        url=entry_id or f"https://arxiv.org/abs/{normalized}",
        content_text=summary,
        source_type="paper",
        origin="search",
        source_metadata={
            "provider": "arxiv",
            "research_os_exact_read": True,
            "normalized_external_id": normalized,
        },
    )


def _detect_provider(external_id: str) -> str | None:
    text = (external_id or "").strip()
    lower = text.lower()
    if "openalex.org" in lower or "/works/w" in lower:
        return "openalex"
    if text.upper().startswith("W") and "/" not in text:
        return "openalex"
    if "arxiv.org" in lower or lower.startswith("arxiv:"):
        return "arxiv"

    compact = lower.replace(".pdf", "")
    if "." in compact:
        left, right = compact.split(".", 1)
        if left.isdigit() and right and right[0].isdigit():
            return "arxiv"
    return None


def _normalize_openalex_external_id(external_id: str) -> str:
    text = (external_id or "").strip().rstrip("/")
    lower = text.lower()
    if "/works/" in lower or "openalex.org/" in lower:
        return text.split("/")[-1].upper()
    return text.upper()


def _normalize_arxiv_external_id(external_id: str) -> str:
    text = (external_id or "").strip()
    lower = text.lower()
    if lower.startswith("arxiv:"):
        text = text.split(":", 1)[1].strip()
        lower = text.lower()
    if "arxiv.org/abs/" in lower or "arxiv.org/pdf/" in lower:
        text = text.rstrip("/").split("/")[-1]
    if text.endswith(".pdf"):
        text = text[:-4]
    return text


def _parse_source_metadata(raw: str) -> dict:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
