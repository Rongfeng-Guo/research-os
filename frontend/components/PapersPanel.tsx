import Link from "next/link";
import { getPdfMetadata, isPdfPaper, type ProjectPaper } from "@/lib/papers";

function badgeTone(status: string) {
  if (status === "completed") return "bg-emerald-50 text-emerald-700";
  if (status === "failed") return "bg-rose-50 text-rose-700";
  if (status === "partial") return "bg-amber-50 text-amber-700";
  return "bg-stone-100 text-stone-700";
}

export default function PapersPanel({ papers, projectId }: { papers: ProjectPaper[]; projectId: number }) {
  return (
    <section className="card">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Project sources</h2>
          <p className="text-sm text-slate-600">Academic papers and uploaded texts connected to this project.</p>
        </div>
        <div className="rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-700">
          {papers.length} sources
        </div>
      </div>
      <div className="space-y-3">
        {papers.length === 0 ? <p className="text-sm text-slate-500">No sources added yet.</p> : null}
        {papers.map((paper) => {
          const pdfMetadata = getPdfMetadata(paper);
          const visiblePages = pdfMetadata?.pages.slice(0, 6) || [];
          return (
            <div key={paper.id} className="rounded-2xl border border-stone-200 bg-stone-50/60 p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-medium text-slate-900">{paper.title}</h3>
                    <span className="rounded-full bg-white px-2 py-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                      {paper.source}
                    </span>
                    <span className="rounded-full bg-white px-2 py-1 text-xs text-slate-500">{paper.content_type}</span>
                    <span className={`rounded-full px-2 py-1 text-xs ${badgeTone(paper.ingestion_status)}`}>{paper.ingestion_status}</span>
                    <span className={`rounded-full px-2 py-1 text-xs ${badgeTone(paper.extraction_status)}`}>{paper.extraction_status}</span>
                    {isPdfPaper(paper) ? (
                      <span className={`rounded-full px-2 py-1 text-xs ${badgeTone(paper.pdf_status)}`}>{paper.pdf_status}</span>
                    ) : null}
                    {pdfMetadata?.page_count ? <span className="rounded-full bg-white px-2 py-1 text-xs text-slate-500">{pdfMetadata.page_count} pages</span> : null}
                    {pdfMetadata?.section_count ? <span className="rounded-full bg-white px-2 py-1 text-xs text-slate-500">{pdfMetadata.section_count} sections</span> : null}
                  </div>
                  <p className="text-sm text-slate-600">
                    {paper.authors || "Unknown authors"} • {paper.year || "Unknown year"}
                  </p>
                  <p className="text-sm leading-6 text-slate-500">{paper.abstract || "No abstract or source preview available yet."}</p>
                  {paper.extraction_error ? <p className="text-xs text-rose-600">{paper.extraction_error}</p> : null}
                </div>
                <div className="flex shrink-0 flex-col gap-2">
                  <Link className="btn-secondary" href={`/papers?external_id=${encodeURIComponent(paper.external_id)}&project_id=${projectId}`}>
                    Read in app
                  </Link>
                  {paper.url ? (
                    <a className="btn-secondary" href={paper.url} rel="noreferrer" target="_blank">
                      Open source
                    </a>
                  ) : null}
                </div>
              </div>

              {pdfMetadata ? (
                <div className="mt-4 rounded-2xl bg-white px-4 py-4 text-sm text-slate-600">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span className="rounded-full bg-stone-100 px-2 py-1">{pdfMetadata.parser || "pdf parser"}</span>
                    {pdfMetadata.extracted_page_count ? (
                      <span className="rounded-full bg-stone-100 px-2 py-1">{pdfMetadata.extracted_page_count} extracted pages</span>
                    ) : null}
                  </div>
                  {pdfMetadata.detected_sections.length ? (
                    <div className="mt-3">
                      <p className="text-xs font-medium uppercase tracking-[0.18em] text-stone-500">Detected sections</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {pdfMetadata.detected_sections.map((section) => (
                          <span key={`${paper.id}-${section}`} className="rounded-full bg-stone-100 px-2 py-1 text-xs text-stone-700">
                            {section}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {visiblePages.length ? (
                    <details className="mt-3 rounded-2xl border border-stone-200 bg-stone-50 px-3 py-3">
                      <summary className="cursor-pointer text-sm font-medium text-slate-700">
                        Page previews
                      </summary>
                      <div className="mt-3 space-y-3">
                        {visiblePages.map((page) => (
                          <div key={`${paper.id}-page-${page.page_number}`} className="rounded-xl bg-white px-3 py-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-xs font-medium uppercase tracking-[0.18em] text-stone-500">Page {page.page_number}</span>
                              {page.used_page_anchor ? (
                                <span className="rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-700">page anchor</span>
                              ) : null}
                              {page.section_titles.map((section) => (
                                <span key={`${paper.id}-page-${page.page_number}-${section}`} className="rounded-full bg-stone-100 px-2 py-1 text-xs text-stone-700">
                                  {section}
                                </span>
                              ))}
                            </div>
                            {page.preview ? <p className="mt-2 text-sm leading-6 text-slate-600">{page.preview}</p> : null}
                          </div>
                        ))}
                        {pdfMetadata.pages.length > visiblePages.length ? (
                          <p className="text-xs text-slate-500">
                            Showing the first {visiblePages.length} pages of {pdfMetadata.pages.length}.
                          </p>
                        ) : null}
                      </div>
                    </details>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
