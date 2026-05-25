from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .extraction import LLMStructuredExtractor, MockStructuredExtractor, StructuredExtractionResult
from .extraction_pipeline import TextChunk, chunk_text, merge_extraction_results
from ..settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ChunkExtractionFailure:
    chunk_id: str
    error_message: str


@dataclass
class ExtractionWorkflowResult:
    status: str
    provider: str
    result: StructuredExtractionResult | None = None
    chunks: list[TextChunk] = field(default_factory=list)
    failures: list[ChunkExtractionFailure] = field(default_factory=list)
    warning_messages: list[str] = field(default_factory=list)
    error_message: str = ""


def get_extractor():
    provider = settings.extraction_provider
    if provider == "llm":
        extractor = LLMStructuredExtractor()
        if extractor.is_available():
            return extractor
    return MockStructuredExtractor()


def _run_with_extractor(extractor, *, title: str, source_url: str, chunks: list[TextChunk]) -> ExtractionWorkflowResult:
    successful_results: list[tuple[TextChunk, StructuredExtractionResult]] = []
    failures: list[ChunkExtractionFailure] = []

    for chunk in chunks:
        try:
            result = extractor.extract(
                title=title,
                text=chunk.text,
                source_url=source_url,
                chunk_id=chunk.chunk_id,
                section_name=chunk.section_name,
            )
            successful_results.append((chunk, result))
        except Exception as exc:
            logger.exception("Chunk extraction failed provider=%s title=%s chunk=%s", extractor.provider_name, title, chunk.chunk_id)
            failures.append(ChunkExtractionFailure(chunk_id=chunk.chunk_id, error_message=str(exc)))

    if not successful_results:
        return ExtractionWorkflowResult(
            status="failed",
            provider=extractor.provider_name,
            chunks=chunks,
            failures=failures,
            error_message="All extraction chunks failed",
        )

    merged = merge_extraction_results(successful_results)
    status = "partial" if failures else "completed"
    return ExtractionWorkflowResult(
        status=status,
        provider=extractor.provider_name,
        result=merged,
        chunks=chunks,
        failures=failures,
        warning_messages=[failure.error_message for failure in failures],
        error_message="; ".join(failure.error_message for failure in failures),
    )


def extract_structured_evidence(*, title: str, text: str, source_url: str = "") -> ExtractionWorkflowResult:
    extractor = get_extractor()
    chunks = chunk_text(text or "", chunk_size=2200, overlap=250)
    if not chunks:
        return ExtractionWorkflowResult(
            status="failed",
            provider=extractor.provider_name,
            error_message="No source text available for extraction",
        )

    workflow = _run_with_extractor(extractor, title=title, source_url=source_url, chunks=chunks)
    if workflow.status != "failed":
        return workflow

    if not settings.extraction_allow_fallback or extractor.provider_name == "mock":
        return workflow

    fallback = MockStructuredExtractor()
    fallback_workflow = _run_with_extractor(fallback, title=title, source_url=source_url, chunks=chunks)
    fallback_workflow.warning_messages.insert(
        0,
        f"Primary extractor {extractor.provider_name} failed. Falling back to mock extraction.",
    )
    if workflow.error_message:
        fallback_workflow.warning_messages.append(workflow.error_message)
    return fallback_workflow
