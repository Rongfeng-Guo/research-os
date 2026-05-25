from __future__ import annotations

import re
from dataclasses import dataclass

from .extraction import EXTRACTION_CARD_TYPES, StructuredEvidenceItem, StructuredExtractionResult


@dataclass
class TextChunk:
    chunk_id: str
    text: str
    start_char: int
    end_char: int
    section_name: str


def infer_sections(text: str) -> list[tuple[int, str]]:
    sections: list[tuple[int, str]] = [(0, "source")]
    for match in re.finditer(r"^(#+)\s+(.+)$", text, flags=re.MULTILINE):
        sections.append((match.start(), match.group(2).strip()))
    return sorted(sections, key=lambda item: item[0])


def section_for_offset(offset: int, sections: list[tuple[int, str]]) -> str:
    current = "source"
    for start, name in sections:
        if start > offset:
            break
        current = name
    return current


def chunk_text(text: str, *, chunk_size: int = 2200, overlap: int = 250) -> list[TextChunk]:
    normalized = text.strip()
    if not normalized:
        return []

    sections = infer_sections(normalized)
    chunks: list[TextChunk] = []
    start = 0
    index = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        if end < len(normalized):
            boundary = normalized.rfind("\n\n", start, end)
            if boundary > start + 600:
                end = boundary

        chunk_text_value = normalized[start:end].strip()
        if chunk_text_value:
            chunks.append(
                TextChunk(
                    chunk_id=f"chunk-{index}",
                    text=chunk_text_value,
                    start_char=start,
                    end_char=end,
                    section_name=section_for_offset(start, sections),
                )
            )
            index += 1

        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def normalize_merge_key(card_type: str, content: str) -> str:
    normalized = re.sub(r"\W+", " ", content.lower()).strip()
    return f"{card_type}:{normalized}"


def merge_extraction_results(results: list[tuple[TextChunk, StructuredExtractionResult]]) -> StructuredExtractionResult:
    merged: dict[str, dict[str, StructuredEvidenceItem]] = {card_type: {} for card_type in EXTRACTION_CARD_TYPES}

    for chunk, result in results:
        for card_type, item in result.iter_cards():
            key = normalize_merge_key(card_type, item.content)
            candidate = StructuredEvidenceItem(
                content=item.content.strip(),
                snippet=(item.snippet or chunk.text[:220]).strip(),
                section_name=item.section_name or chunk.section_name,
                confidence_score=item.confidence_score,
            )
            existing = merged[card_type].get(key)
            if not existing:
                merged[card_type][key] = candidate
                continue

            existing_signal = (existing.confidence_score, len(existing.snippet), len(existing.content))
            candidate_signal = (candidate.confidence_score, len(candidate.snippet), len(candidate.content))
            if candidate_signal > existing_signal:
                merged[card_type][key] = candidate

    return StructuredExtractionResult(
        **{card_type: list(items.values()) for card_type, items in merged.items()}
    )
