from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PaperRecord:
    external_id: str
    title: str
    abstract: str
    authors: str = ""
    year: int = 2025
    source: str = "mock"
    url: str = ""
    content_text: str = ""
    content_type: str = "abstract"
    source_type: str = "paper"
    origin: str = "search"
    ingestion_status: str = "completed"
    pdf_status: str = "pending"
    extraction_status: str = "pending"
    extraction_error: str = ""
    source_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PaperDiscoveryProvider(ABC):
    provider_name = "base"

    @abstractmethod
    def search(self, query: str, limit: int = 8) -> list[PaperRecord]:
        raise NotImplementedError
