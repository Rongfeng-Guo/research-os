from __future__ import annotations

from typing import Any

import httpx

from ...settings import settings
from .base import PaperDiscoveryProvider, PaperRecord


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    positions: dict[int, str] = {}
    for word, indexes in inverted_index.items():
        for index in indexes:
            positions[index] = word
    return " ".join(positions[i] for i in sorted(positions))


class OpenAlexPaperDiscoveryProvider(PaperDiscoveryProvider):
    provider_name = "openalex"

    def __init__(self) -> None:
        self.mailto = settings.openalex_email
        self.timeout = settings.paper_discovery_timeout_seconds

    def search(self, query: str, limit: int = 8) -> list[PaperRecord]:
        params: dict[str, Any] = {
            "search": query.strip() or "research topic",
            "per-page": limit,
        }
        if self.mailto:
            params["mailto"] = self.mailto

        response = httpx.get(
            "https://api.openalex.org/works",
            params=params,
            timeout=self.timeout,
            headers={"User-Agent": "research-os-mvp/0.2"},
        )
        response.raise_for_status()
        payload = response.json()

        papers: list[PaperRecord] = []
        for item in payload.get("results", []):
            authors = ", ".join(
                authorship.get("author", {}).get("display_name", "")
                for authorship in item.get("authorships", [])
                if authorship.get("author", {}).get("display_name")
            )
            year = item.get("publication_year") or 0
            paper_url = item.get("primary_location", {}).get("landing_page_url") or item.get("id", "")
            abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
            papers.append(
                PaperRecord(
                    external_id=item.get("id", ""),
                    title=item.get("display_name", "Untitled paper"),
                    abstract=abstract,
                    authors=authors,
                    year=year or 2025,
                    source="openalex",
                    url=paper_url,
                    content_text=abstract,
                    source_type="paper",
                    origin="search",
                    source_metadata={
                        "provider": "openalex",
                        "cited_by_count": item.get("cited_by_count", 0),
                        "open_access_url": item.get("open_access", {}).get("oa_url", ""),
                    },
                )
            )
        return papers
