from __future__ import annotations

from app.services.paper_discovery.arxiv_provider import ArxivPaperDiscoveryProvider
from app.services.paper_discovery.openalex_provider import OpenAlexPaperDiscoveryProvider


class MockResponse:
    def __init__(self, payload=None, text=""):
        self._payload = payload or {}
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_openalex_provider_normalizes_response(monkeypatch):
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "display_name": "Test Paper",
                "publication_year": 2024,
                "authorships": [{"author": {"display_name": "Jane Doe"}}],
                "abstract_inverted_index": {"hello": [0], "world": [1]},
                "cited_by_count": 42,
                "primary_location": {"landing_page_url": "https://example.org/paper"},
                "open_access": {"oa_url": "https://example.org/pdf"},
            }
        ]
    }

    monkeypatch.setattr("app.services.paper_discovery.openalex_provider.httpx.get", lambda *args, **kwargs: MockResponse(payload=payload))
    papers = OpenAlexPaperDiscoveryProvider().search("test")
    assert papers[0].external_id == "https://openalex.org/W123"
    assert papers[0].abstract == "hello world"
    assert papers[0].source == "openalex"
    assert papers[0].url == "https://example.org/paper"


def test_arxiv_provider_normalizes_response(monkeypatch):
    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/1234.5678</id>
        <updated>2024-01-01T00:00:00Z</updated>
        <published>2024-01-01T00:00:00Z</published>
        <title> Arxiv Test Paper </title>
        <summary> A short summary. </summary>
        <author><name>Alice</name></author>
      </entry>
    </feed>
    """

    monkeypatch.setattr("app.services.paper_discovery.arxiv_provider.httpx.get", lambda *args, **kwargs: MockResponse(text=xml_payload))
    papers = ArxivPaperDiscoveryProvider().search("test")
    assert papers[0].external_id == "http://arxiv.org/abs/1234.5678"
    assert papers[0].title == "Arxiv Test Paper"
    assert papers[0].authors == "Alice"
    assert papers[0].source == "arxiv"
