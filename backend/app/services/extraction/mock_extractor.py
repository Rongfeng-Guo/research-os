from __future__ import annotations

from .base import StructuredEvidenceItem, StructuredExtractionResult, StructuredExtractor


class MockStructuredExtractor(StructuredExtractor):
    provider_name = "mock"

    def extract(
        self,
        *,
        title: str,
        text: str,
        source_url: str = "",
        chunk_id: str = "",
        section_name: str = "",
    ) -> StructuredExtractionResult:
        compact = " ".join(text.split())
        snippet = compact[:220].strip()
        seed = snippet or "the proposed method improves the target task under the stated setting."
        section = section_name or "source"
        return StructuredExtractionResult(
            claim=[
                StructuredEvidenceItem(
                    content=f"{title} argues that {seed}",
                    snippet=snippet,
                    section_name=section,
                    confidence_score=0.58,
                )
            ],
            method=[
                StructuredEvidenceItem(
                    content="The paper describes a method pipeline with task framing, system design, and comparative evaluation.",
                    snippet=snippet,
                    section_name=section,
                    confidence_score=0.55,
                )
            ],
            dataset=[
                StructuredEvidenceItem(
                    content="The study references one or more datasets or benchmarks used to evaluate the proposed approach.",
                    snippet=snippet,
                    section_name=section,
                    confidence_score=0.5,
                )
            ],
            limitation=[
                StructuredEvidenceItem(
                    content="The evidence remains limited by benchmark coverage, implementation detail, or unclear generalization claims.",
                    snippet=snippet,
                    section_name=section,
                    confidence_score=0.5,
                )
            ],
            open_question=[
                StructuredEvidenceItem(
                    content="How well does this approach transfer to broader domains, stronger baselines, or larger-scale settings?",
                    snippet=snippet,
                    section_name=section,
                    confidence_score=0.48,
                )
            ],
        )
