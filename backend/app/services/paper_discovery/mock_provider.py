from __future__ import annotations

from .base import PaperDiscoveryProvider, PaperRecord


class MockPaperDiscoveryProvider(PaperDiscoveryProvider):
    provider_name = "mock"

    def search(self, query: str, limit: int = 8) -> list[PaperRecord]:
        q = query.strip() or "research topic"
        return [
            PaperRecord(
                external_id=f"mock-{i}",
                title=f"{q.title()} Study {i}",
                abstract=(
                    f"This paper explores {q} with a focus on method design, evaluation settings, "
                    "and practical limitations. It provides a useful starting point for structured literature review."
                ),
                authors="A. Student, B. Researcher",
                year=2020 + i,
                source="mock",
                url=f"https://example.org/papers/{i}",
                content_text=(
                    f"This mock source discusses {q}, proposes a research workflow, evaluates it on benchmarks, "
                    "and highlights open limitations for later investigation."
                ),
                source_metadata={"provider": "mock"},
            )
            for i in range(1, limit + 1)
        ]
