from __future__ import annotations

from app.services.extraction import StructuredEvidenceItem, StructuredExtractionResult
from app.services.extraction_pipeline import chunk_text, merge_extraction_results
from app.services.extraction_service import extract_structured_evidence
from app.settings import settings


def test_chunk_text_preserves_order_and_metadata():
    text = "# Intro\n" + ("A" * 1500) + "\n\n# Method\n" + ("B" * 1700)
    chunks = chunk_text(text, chunk_size=1200, overlap=120)
    assert len(chunks) >= 2
    assert chunks[0].start_char < chunks[1].start_char
    assert chunks[0].chunk_id == "chunk-0"
    assert chunks[0].section_name in {"Intro", "source"}


def test_merge_extraction_results_deduplicates_by_content():
    chunks = chunk_text(("First chunk. " * 120) + "\n\n" + ("Second chunk. " * 120), chunk_size=400, overlap=0)
    results = [
        (
            chunks[0],
            StructuredExtractionResult(
                claim=[StructuredEvidenceItem(content="The system improves retrieval accuracy.", snippet="improves retrieval accuracy", confidence_score=0.6)]
            ),
        ),
        (
            chunks[1],
            StructuredExtractionResult(
                claim=[StructuredEvidenceItem(content="The system improves retrieval accuracy.", snippet="system improves retrieval accuracy with better reranking", confidence_score=0.8)]
            ),
        ),
    ]
    merged = merge_extraction_results(results)
    assert len(merged.claim) == 1
    assert merged.claim[0].confidence_score == 0.8


def test_openai_fallback_to_mock_when_primary_fails(monkeypatch):
    object.__setattr__(settings, "extraction_provider", "llm")
    object.__setattr__(settings, "extraction_allow_fallback", True)
    object.__setattr__(settings, "openai_api_key", "test-key")

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.services.extraction.llm_extractor.httpx.post", raise_error)
    workflow = extract_structured_evidence(title="Paper", text="This paper presents a benchmark.", source_url="")
    assert workflow.status in {"completed", "partial"}
    assert workflow.provider == "mock"
    assert workflow.result is not None


def test_extraction_failure_when_no_fallback(monkeypatch):
    object.__setattr__(settings, "extraction_provider", "llm")
    object.__setattr__(settings, "extraction_allow_fallback", False)
    object.__setattr__(settings, "openai_api_key", "test-key")

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.services.extraction.llm_extractor.httpx.post", raise_error)
    workflow = extract_structured_evidence(title="Paper", text="This paper presents a benchmark.", source_url="")
    assert workflow.status == "failed"
    assert "All extraction chunks failed" in workflow.error_message

    object.__setattr__(settings, "extraction_allow_fallback", True)
    object.__setattr__(settings, "extraction_provider", "mock")
    object.__setattr__(settings, "openai_api_key", "")
