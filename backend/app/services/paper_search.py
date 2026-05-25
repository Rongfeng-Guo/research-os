from __future__ import annotations

import logging
from typing import List, Dict

from ..settings import settings
from .paper_discovery import (
    ArxivPaperDiscoveryProvider,
    MockPaperDiscoveryProvider,
    OpenAlexPaperDiscoveryProvider,
)

logger = logging.getLogger(__name__)


def get_paper_discovery_provider():
    provider_name = settings.paper_discovery_provider
    providers = {
        "mock": MockPaperDiscoveryProvider,
        "openalex": OpenAlexPaperDiscoveryProvider,
        "arxiv": ArxivPaperDiscoveryProvider,
    }
    provider_cls = providers.get(provider_name, MockPaperDiscoveryProvider)
    return provider_cls()


def search_papers(query: str, limit: int = 8) -> List[Dict]:
    provider = get_paper_discovery_provider()
    try:
        return [paper.to_dict() for paper in provider.search(query, limit=limit)]
    except Exception as exc:
        logger.exception("Paper discovery failed for provider=%s query=%s", provider.provider_name, query)
        if not settings.paper_discovery_allow_fallback or provider.provider_name == "mock":
            raise RuntimeError(f"Paper discovery failed using provider '{provider.provider_name}': {exc}") from exc

        fallback = MockPaperDiscoveryProvider()
        logger.warning("Falling back to mock paper discovery after %s failure", provider.provider_name)
        fallback_results = [paper.to_dict() for paper in fallback.search(query, limit=limit)]
        for row in fallback_results:
            row["source_metadata"] = {
                **row.get("source_metadata", {}),
                "fallback_from": provider.provider_name,
                "fallback_reason": str(exc),
            }
        return fallback_results
