from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import httpx

from ...settings import settings
from .base import PaperDiscoveryProvider, PaperRecord


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivPaperDiscoveryProvider(PaperDiscoveryProvider):
    provider_name = "arxiv"

    def search(self, query: str, limit: int = 8) -> list[PaperRecord]:
        encoded_query = quote_plus(query.strip() or "research topic")
        url = (
            "https://export.arxiv.org/api/query"
            f"?search_query=all:{encoded_query}&start=0&max_results={limit}&sortBy=relevance&sortOrder=descending"
        )
        response = httpx.get(url, timeout=settings.paper_discovery_timeout_seconds, headers={"User-Agent": "research-os-mvp/0.2"})
        response.raise_for_status()

        root = ET.fromstring(response.text)
        papers: list[PaperRecord] = []
        for entry in root.findall("atom:entry", ATOM_NS):
            entry_id = entry.findtext("atom:id", default="", namespaces=ATOM_NS)
            title = " ".join((entry.findtext("atom:title", default="", namespaces=ATOM_NS)).split())
            summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ATOM_NS)).split())
            published = entry.findtext("atom:published", default="", namespaces=ATOM_NS)
            authors = ", ".join(
                author.findtext("atom:name", default="", namespaces=ATOM_NS)
                for author in entry.findall("atom:author", ATOM_NS)
            )
            year = int(published[:4]) if published[:4].isdigit() else 2025
            papers.append(
                PaperRecord(
                    external_id=entry_id,
                    title=title or "Untitled paper",
                    abstract=summary,
                    authors=authors,
                    year=year,
                    source="arxiv",
                    url=entry_id,
                    content_text=summary,
                    source_type="paper",
                    origin="search",
                    source_metadata={"provider": "arxiv"},
                )
            )
        return papers
