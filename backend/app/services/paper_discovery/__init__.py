from .base import PaperDiscoveryProvider, PaperRecord
from .arxiv_provider import ArxivPaperDiscoveryProvider
from .mock_provider import MockPaperDiscoveryProvider
from .openalex_provider import OpenAlexPaperDiscoveryProvider

__all__ = [
    "ArxivPaperDiscoveryProvider",
    "MockPaperDiscoveryProvider",
    "OpenAlexPaperDiscoveryProvider",
    "PaperDiscoveryProvider",
    "PaperRecord",
]
