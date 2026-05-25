from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from ...settings import settings
from .base import EXTRACTION_CARD_TYPES, StructuredExtractionResult, StructuredExtractor

logger = logging.getLogger(__name__)


class LLMStructuredExtractor(StructuredExtractor):
    provider_name = "openai"

    def __init__(self) -> None:
        self.api_key = settings.openai_api_key

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _sanitize_payload(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("LLM response is not a JSON object")

        sanitized: dict[str, Any] = {}
        for card_type in EXTRACTION_CARD_TYPES:
            raw_items = payload.get(card_type, [])
            if isinstance(raw_items, dict):
                raw_items = [raw_items]
            if not isinstance(raw_items, list):
                raw_items = []

            cleaned_items = []
            for item in raw_items:
                if isinstance(item, str):
                    cleaned_items.append(
                        {
                            "content": item.strip(),
                            "snippet": "",
                            "section_name": "",
                            "confidence_score": 0.5,
                        }
                    )
                    continue
                if not isinstance(item, dict):
                    continue

                content = str(item.get("content", "")).strip()
                if not content:
                    continue
                try:
                    confidence = float(item.get("confidence_score", 0.5) or 0.5)
                except (TypeError, ValueError):
                    confidence = 0.5
                cleaned_items.append(
                    {
                        "content": content,
                        "snippet": str(item.get("snippet", "")).strip(),
                        "section_name": str(item.get("section_name", "")).strip(),
                        "confidence_score": max(0.0, min(1.0, confidence)),
                    }
                )
            sanitized[card_type] = cleaned_items
        return sanitized

    def extract(
        self,
        *,
        title: str,
        text: str,
        source_url: str = "",
        chunk_id: str = "",
        section_name: str = "",
    ) -> StructuredExtractionResult:
        prompt = (
            "You extract source-grounded research evidence from academic text. "
            "Return strict JSON with exactly these top-level keys: claim, method, dataset, limitation, open_question. "
            "Each key must map to an array of objects. "
            "Each object must include: content, snippet, section_name, confidence_score. "
            "Only include evidence grounded in the given chunk. Do not fabricate citations or unsupported claims. "
            "Use short snippets copied from the source chunk when possible."
        )
        response = httpx.post(
            f"{settings.openai_base_url}/chat/completions",
            timeout=45.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Title: {title}\n"
                            f"Source URL: {source_url or 'N/A'}\n"
                            f"Chunk ID: {chunk_id or 'chunk-0'}\n"
                            f"Section: {section_name or 'unknown'}\n"
                            f"Source Text:\n{text[:12000]}"
                        ),
                    },
                ],
                "temperature": 0.1,
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.warning("OpenAI extractor returned malformed JSON for chunk=%s: %s", chunk_id, exc)
            raise ValueError("Malformed JSON returned by OpenAI extractor") from exc

        sanitized = self._sanitize_payload(parsed)
        return StructuredExtractionResult.model_validate(sanitized)
