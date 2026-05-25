from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


EXTRACTION_CARD_TYPES = ["claim", "method", "dataset", "limitation", "open_question"]


class StructuredEvidenceItem(BaseModel):
    content: str = Field(min_length=1)
    snippet: str = ""
    section_name: str = ""
    confidence_score: float = Field(default=0.6, ge=0.0, le=1.0)


class StructuredExtractionResult(BaseModel):
    claim: list[StructuredEvidenceItem] = Field(default_factory=list)
    method: list[StructuredEvidenceItem] = Field(default_factory=list)
    dataset: list[StructuredEvidenceItem] = Field(default_factory=list)
    limitation: list[StructuredEvidenceItem] = Field(default_factory=list)
    open_question: list[StructuredEvidenceItem] = Field(default_factory=list)

    def iter_cards(self):
        for card_type in EXTRACTION_CARD_TYPES:
            for item in getattr(self, card_type):
                yield card_type, item


class StructuredExtractor(ABC):
    provider_name = "base"

    @abstractmethod
    def extract(
        self,
        *,
        title: str,
        text: str,
        source_url: str = "",
        chunk_id: str = "",
        section_name: str = "",
    ) -> StructuredExtractionResult:
        raise NotImplementedError
