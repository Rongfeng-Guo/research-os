export type PaperCandidate = {
  external_id: string;
  title: string;
  abstract: string;
  authors: string;
  year: number;
  source: string;
  url: string;
  content_text: string;
  content_type: string;
  source_type: string;
  origin: string;
  ingestion_status: string;
  pdf_status: string;
  extraction_status: string;
  extraction_error: string;
  source_metadata: Record<string, unknown>;
};

export type PdfPageMetadata = {
  page_number: number;
  section_titles: string[];
  detected_section_titles: string[];
  preview: string;
  char_count: number;
  used_page_anchor: boolean;
};

export type PdfMetadata = {
  filename: string;
  parser: string;
  page_count: number;
  extracted_page_count: number;
  section_count: number;
  detected_sections: string[];
  pages: PdfPageMetadata[];
};

export type ProjectPaper = PaperCandidate & {
  id: number;
};

export type LinkedProjectRef = {
  id: number;
  title: string;
};

export type LibraryPaperItem = PaperCandidate & {
  id: number;
  project_count: number;
  linked_projects: LinkedProjectRef[];
  ingested_at: string;
  source_updated_at: string;
  created_at: string;
};

export function getPaperReaderText(paper: PaperCandidate | null | undefined): string {
  return (paper?.content_text || paper?.abstract || "").trim();
}

export function getPaperAbstractText(paper: PaperCandidate | null | undefined): string {
  return (paper?.abstract || paper?.content_text || "").trim();
}

export function getPaperAuthorsLabel(authors: string | undefined): string {
  return authors?.trim() || "Unknown authors";
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function asBoolean(value: unknown): boolean {
  return value === true;
}

export function isPdfPaper(paper: PaperCandidate | null | undefined): boolean {
  return paper?.source_type === "pdf" || paper?.content_type === "pdf";
}

export function getPdfMetadata(paper: PaperCandidate | null | undefined): PdfMetadata | null {
  if (!paper || !isPdfPaper(paper)) {
    return null;
  }

  const metadata = asRecord(paper.source_metadata);
  if (!metadata) {
    return null;
  }

  const pages = Array.isArray(metadata.pages)
    ? metadata.pages
        .map((page) => {
          const record = asRecord(page);
          if (!record) {
            return null;
          }
          return {
            page_number: asNumber(record.page_number),
            section_titles: asStringArray(record.section_titles),
            detected_section_titles: asStringArray(record.detected_section_titles),
            preview: typeof record.preview === "string" ? record.preview : "",
            char_count: asNumber(record.char_count),
            used_page_anchor: asBoolean(record.used_page_anchor),
          } satisfies PdfPageMetadata;
        })
        .filter((page): page is PdfPageMetadata => page !== null)
    : [];

  return {
    filename: typeof metadata.filename === "string" ? metadata.filename : "",
    parser: typeof metadata.parser === "string" ? metadata.parser : "",
    page_count: asNumber(metadata.page_count),
    extracted_page_count: asNumber(metadata.extracted_page_count),
    section_count: asNumber(metadata.section_count),
    detected_sections: asStringArray(metadata.detected_sections),
    pages,
  };
}
