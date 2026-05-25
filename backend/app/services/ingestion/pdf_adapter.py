from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
import re


SECTION_TITLE_ALIASES = {
    "abstract": "Abstract",
    "introduction": "Introduction",
    "background": "Background",
    "related work": "Related Work",
    "method": "Method",
    "methods": "Methods",
    "materials and methods": "Materials and Methods",
    "approach": "Approach",
    "experimental setup": "Experimental Setup",
    "experiments": "Experiments",
    "results": "Results",
    "discussion": "Discussion",
    "limitations": "Limitations",
    "limitation": "Limitations",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
    "future work": "Future Work",
    "appendix": "Appendix",
    "references": "References",
}


def _normalize_pdf_text(text: str) -> str:
    normalized = (text or "").replace("\x00", " ")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"[ \t]{2,}", " ", normalized)
    return normalized.strip()


def _normalize_pdf_lines(text: str) -> list[str]:
    normalized = (text or "").replace("\x00", " ")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    return [line.strip() for line in normalized.split("\n") if line.strip()]


def _normalize_section_heading(line: str) -> str:
    normalized = re.sub(r"^(section|chapter)\s+", "", line.strip(), flags=re.IGNORECASE)
    normalized = re.sub(r"^[0-9ivxlcdm]+(?:\.[0-9ivxlcdm]+)*[\)\].:-]?\s+", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip(" .:-")
    if not normalized:
        return ""
    alias = SECTION_TITLE_ALIASES.get(normalized.lower())
    if alias:
        return alias
    return normalized.title() if normalized.isupper() else normalized


def _looks_like_section_heading(line: str) -> bool:
    normalized = _normalize_section_heading(line)
    if not normalized:
        return False
    if normalized.lower() in {value.lower() for value in SECTION_TITLE_ALIASES.values()}:
        return True
    if len(normalized) > 80:
        return False
    if len(normalized.split()) > 8:
        return False
    if re.search(r"[.?!]$", normalized):
        return False
    alpha_count = sum(1 for char in normalized if char.isalpha())
    return alpha_count >= 3 and normalized.isupper()


def _extract_inline_section_heading(line: str) -> tuple[str, str] | None:
    compact = re.sub(r"\s+", " ", line.strip())
    if not compact:
        return None

    for raw_title, canonical_title in SECTION_TITLE_ALIASES.items():
        match = re.match(
            rf"^(?:section\s+|chapter\s+)?(?:[0-9ivxlcdm]+(?:\.[0-9ivxlcdm]+)*[\)\].:-]?\s+)?{re.escape(raw_title)}(?:\s*[:.-]|\s+)(.+)$",
            compact,
            flags=re.IGNORECASE,
        )
        if match:
            remainder = match.group(1).strip()
            if remainder and len(remainder) >= 12:
                return canonical_title, remainder
    return None


def _append_paragraph(output_lines: list[str], buffer: list[str]) -> None:
    if not buffer:
        return
    output_lines.append(_normalize_pdf_text(" ".join(buffer)))
    buffer.clear()


def _build_page_section_text(page_text: str, page_number: int) -> tuple[str, dict]:
    lines = _normalize_pdf_lines(page_text)
    if not lines:
        return "", {
            "page_number": page_number,
            "section_titles": [],
            "preview": "",
            "char_count": 0,
            "used_page_anchor": False,
        }

    output_lines: list[str] = []
    paragraph_buffer: list[str] = []
    section_titles: list[str] = []
    detected_titles: list[str] = []
    used_page_anchor = False

    for line in lines:
        inline_heading = _extract_inline_section_heading(line)
        if inline_heading is not None:
            title, remainder = inline_heading
            _append_paragraph(output_lines, paragraph_buffer)
            output_lines.append(f"## {title}")
            section_titles.append(title)
            detected_titles.append(title)
            paragraph_buffer.append(remainder)
            continue

        if _looks_like_section_heading(line):
            title = _normalize_section_heading(line)
            _append_paragraph(output_lines, paragraph_buffer)
            output_lines.append(f"## {title}")
            section_titles.append(title)
            detected_titles.append(title)
            continue

        if not output_lines:
            fallback_title = f"Page {page_number}"
            output_lines.append(f"## {fallback_title}")
            section_titles.append(fallback_title)
            used_page_anchor = True
        paragraph_buffer.append(line)

    _append_paragraph(output_lines, paragraph_buffer)
    structured_text = "\n\n".join(line for line in output_lines if line.strip()).strip()
    preview = re.sub(r"\s+", " ", structured_text.replace("#", " ")).strip()[:180]
    return structured_text, {
        "page_number": page_number,
        "section_titles": section_titles,
        "detected_section_titles": detected_titles,
        "preview": preview,
        "char_count": len(structured_text),
        "used_page_anchor": used_page_anchor,
    }


@dataclass
class PDFParseResult:
    status: str
    text: str = ""
    error: str = ""
    page_count: int = 0
    metadata: dict = field(default_factory=dict)


def parse_pdf_bytes(content: bytes, filename: str) -> PDFParseResult:
    try:
        from pypdf import PdfReader
    except ImportError:
        return PDFParseResult(
            status="failed",
            error="PDF parsing dependency is unavailable. Install `pypdf` to enable PDF uploads.",
        )

    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            reader.decrypt("")
    except Exception as exc:
        return PDFParseResult(
            status="failed",
            error=f"Could not read PDF '{filename}': {exc}",
        )

    page_count = len(reader.pages)
    page_texts: list[str] = []
    page_metadata: list[dict] = []
    detected_sections: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            extracted_text = page.extract_text() or ""
        except Exception as exc:
            return PDFParseResult(
                status="failed",
                page_count=page_count,
                metadata={"filename": filename, "parser": "pypdf", "page_count": page_count},
                error=f"Could not extract text from page {page_number} of '{filename}': {exc}",
            )
        structured_text, structured_metadata = _build_page_section_text(extracted_text, page_number)
        if structured_text:
            page_texts.append(structured_text)
            page_metadata.append(structured_metadata)
            for title in structured_metadata.get("detected_section_titles", []):
                if title not in detected_sections:
                    detected_sections.append(title)

    combined_text = "\n\n".join(page_texts).strip()
    metadata = {
        "filename": filename,
        "parser": "pypdf",
        "page_count": page_count,
        "extracted_page_count": len(page_texts),
        "section_count": len(detected_sections),
        "detected_sections": detected_sections,
        "pages": page_metadata,
    }
    if not combined_text:
        return PDFParseResult(
            status="failed",
            page_count=page_count,
            metadata=metadata,
            error="No extractable text was found in this PDF. Scanned or image-only PDFs are not supported yet.",
        )

    return PDFParseResult(
        status="parsed",
        text=combined_text,
        page_count=page_count,
        metadata=metadata,
    )
