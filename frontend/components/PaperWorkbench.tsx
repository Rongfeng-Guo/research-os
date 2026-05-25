"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import LoadingSpinner from "@/components/LoadingSpinner";
import { useToast } from "@/components/ToastProvider";
import { apiFetch, getApiErrorMessage, isApiError } from "@/lib/api";
import { getLastProjectId, setLastProjectId } from "@/lib/local-state";
import { getPaperAbstractText, getPaperAuthorsLabel, getPaperReaderText, getPdfMetadata, isPdfPaper, type PaperCandidate } from "@/lib/papers";

type ProjectOption = {
  id: number;
  title: string;
  topic: string;
};

function metadataBadges(paper: PaperCandidate | null): string[] {
  if (!paper) return [];
  const badges = [paper.source, paper.content_type || "abstract", paper.source_type || "paper"].filter(Boolean);
  const sourceMetadata = paper.source_metadata || {};
  const pdfMetadata = getPdfMetadata(paper);
  if (isPdfPaper(paper) && paper.pdf_status) {
    badges.push(`pdf: ${paper.pdf_status}`);
  }
  if (pdfMetadata?.page_count) {
    badges.push(`pages: ${pdfMetadata.page_count}`);
  }
  if (pdfMetadata?.section_count) {
    badges.push(`sections: ${pdfMetadata.section_count}`);
  }
  for (const [key, value] of Object.entries(sourceMetadata)) {
    if (key === "pages" || key === "detected_sections" || key === "page_count" || key === "section_count") {
      continue;
    }
    if (typeof value === "boolean" && value) {
      badges.push(key.replaceAll("_", " "));
    }
    if (typeof value === "string" && value && badges.length < 8 && key !== "normalized_external_id") {
      badges.push(`${key.replaceAll("_", " ")}: ${value}`);
    }
    if (typeof value === "number" && badges.length < 8) {
      badges.push(`${key.replaceAll("_", " ")}: ${value}`);
    }
    if (badges.length >= 8) break;
  }
  return badges.slice(0, 8);
}

export default function PaperWorkbench() {
  const searchParams = useSearchParams();
  const { showToast } = useToast();

  const externalIdParam = searchParams?.get("external_id")?.trim() || "";
  const queryParam = searchParams?.get("query")?.trim() || "";
  const projectParam = Number(searchParams?.get("project_id") || "");

  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | "">("");
  const [query, setQuery] = useState(queryParam);
  const [results, setResults] = useState<PaperCandidate[]>([]);
  const [selectedPaper, setSelectedPaper] = useState<PaperCandidate | null>(null);
  const [resolvedPaper, setResolvedPaper] = useState<PaperCandidate | null>(null);
  const [searchStatus, setSearchStatus] = useState("Search OpenAlex-backed papers or open a known external id.");
  const [readerStatus, setReaderStatus] = useState("");
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [loadingReader, setLoadingReader] = useState(false);
  const [addingPaper, setAddingPaper] = useState(false);
  const [needsLogin, setNeedsLogin] = useState(false);

  useEffect(() => {
    const rememberedProjectId = Number.isFinite(projectParam) ? projectParam : getLastProjectId();
    if (rememberedProjectId) {
      setSelectedProjectId(rememberedProjectId);
    }
  }, [projectParam]);

  useEffect(() => {
    setLoadingProjects(true);
    apiFetch<ProjectOption[]>("/projects")
      .then((data) => {
        setProjects(data);
        if (!selectedProjectId && data.length === 1) {
          setSelectedProjectId(data[0].id);
          setLastProjectId(data[0].id);
        }
      })
      .catch((error) => {
        if (isApiError(error) && error.status === 401) {
          setNeedsLogin(true);
          return;
        }
        showToast({ tone: "error", title: "Could not load projects", message: getApiErrorMessage(error, "Failed to load projects") });
      })
      .finally(() => setLoadingProjects(false));
  }, []);

  useEffect(() => {
    if (!externalIdParam) return;
    void readPaperByExternalId(externalIdParam);
  }, [externalIdParam]);

  async function runSearch(requestQuery = query.trim()) {
    if (!requestQuery) {
      setSearchStatus("Enter a topic before searching.");
      setResults([]);
      return;
    }

    setLoadingSearch(true);
    setSearchStatus("Searching paper index...");
    try {
      const data = await apiFetch<PaperCandidate[]>("/papers/search", {
        method: "POST",
        body: JSON.stringify({ query: requestQuery, limit: 8 }),
      });
      setResults(data);
      setSearchStatus(data.length ? `Found ${data.length} papers.` : "No papers matched this query yet.");
    } catch (error) {
      const message = getApiErrorMessage(error, "Search failed");
      if (isApiError(error) && error.status === 401) {
        setNeedsLogin(true);
      }
      setSearchStatus(message);
      showToast({ tone: "error", title: "Search failed", message });
    } finally {
      setLoadingSearch(false);
    }
  }

  async function readPaperByExternalId(externalId: string, fallbackPaper?: PaperCandidate) {
    if (!externalId) return;
    setSelectedPaper(fallbackPaper || null);
    setResolvedPaper(fallbackPaper || null);
    setLoadingReader(true);
    setReaderStatus("Loading paper detail...");
    try {
      const paper = await apiFetch<PaperCandidate>("/papers/read", {
        method: "POST",
        body: JSON.stringify({ external_id: externalId }),
      });
      setSelectedPaper(fallbackPaper || paper);
      setResolvedPaper(paper);
      setReaderStatus("");
    } catch (error) {
      const message = getApiErrorMessage(error, "Could not read this paper");
      if (isApiError(error) && error.status === 401) {
        setNeedsLogin(true);
      }
      if (fallbackPaper) {
        setSelectedPaper(fallbackPaper);
        setResolvedPaper(fallbackPaper);
        setReaderStatus(`Showing search metadata only. ${message}`);
      } else {
        setResolvedPaper(null);
        setReaderStatus(message);
      }
      showToast({ tone: "error", title: "Reader unavailable", message });
    } finally {
      setLoadingReader(false);
    }
  }

  async function addSelectedPaperToProject(paperOverride?: PaperCandidate) {
    const paper = paperOverride || resolvedPaper || selectedPaper;
    if (!paper) {
      setReaderStatus("Select a paper first.");
      return;
    }
    if (!selectedProjectId) {
      setReaderStatus("Choose a target project before adding this paper.");
      return;
    }

    setAddingPaper(true);
    setReaderStatus("Adding paper to project...");
    try {
      await apiFetch(`/papers/projects/${selectedProjectId}/add`, {
        method: "POST",
        body: JSON.stringify(paper),
      });
      setLastProjectId(selectedProjectId);
      const projectTitle = projects.find((project) => project.id === selectedProjectId)?.title || `project ${selectedProjectId}`;
      setReaderStatus(`Added to ${projectTitle}.`);
      showToast({ tone: "success", title: "Paper added", message: `${paper.title} is now part of ${projectTitle}.` });
    } catch (error) {
      const message = getApiErrorMessage(error, "Failed to add paper");
      if (isApiError(error) && error.status === 401) {
        setNeedsLogin(true);
      }
      setReaderStatus(message);
      showToast({ tone: "error", title: "Could not add paper", message });
    } finally {
      setAddingPaper(false);
    }
  }

  const activePaper = resolvedPaper || selectedPaper;
  const readerText = useMemo(() => getPaperReaderText(activePaper), [activePaper]);
  const abstractText = useMemo(() => getPaperAbstractText(activePaper), [activePaper]);
  const badges = useMemo(() => metadataBadges(activePaper), [activePaper]);
  const pdfMetadata = useMemo(() => getPdfMetadata(activePaper), [activePaper]);

  if (needsLogin) {
    return (
      <section className="card">
        <p className="text-xs font-medium uppercase tracking-[0.24em] text-stone-500">Paper workspace</p>
        <h1 className="mt-2 text-4xl font-semibold">Log in to search and read papers</h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
          This workspace uses the same authenticated backend as your projects, so it needs the existing browser token.
        </p>
        <div className="mt-5 flex gap-3">
          <Link className="btn-primary" href="/login">Login</Link>
          <Link className="btn-secondary" href="/projects">Open projects</Link>
        </div>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <section className="card">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-medium uppercase tracking-[0.24em] text-stone-500">Dedicated paper workspace</p>
            <h1 className="mt-2 text-4xl font-semibold">Paper search and reader</h1>
            <p className="mt-4 text-sm leading-7 text-slate-600">
              Search papers, resolve exact metadata through the unified backend reader, and add promising sources into any research project when they are worth keeping.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="btn-secondary" href="/projects">Project library</Link>
            {selectedProjectId ? <Link className="btn-secondary" href={`/projects/${selectedProjectId}`}>Open selected project</Link> : null}
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-6">
          <section className="card space-y-4">
            <div>
              <h2 className="text-xl font-semibold">Search papers</h2>
              <p className="text-sm text-slate-600">The backend currently searches with OpenAlex and the reader can resolve cached, OpenAlex, and arXiv ids.</p>
            </div>
            <div className="flex gap-2">
              <input
                className="input"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    void runSearch();
                  }
                }}
                placeholder="e.g. graph rag, multimodal retrieval benchmark"
              />
              <button className="btn-primary" disabled={loadingSearch} onClick={() => void runSearch()} type="button">
                {loadingSearch ? <LoadingSpinner /> : null}
                {loadingSearch ? "Searching..." : "Search"}
              </button>
            </div>
            <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
              <label className="space-y-2">
                <span className="label">Target project for add action</span>
                <select
                  className="input"
                  value={selectedProjectId}
                  onChange={(event) => {
                    const nextValue = Number(event.target.value || "");
                    if (Number.isFinite(nextValue) && nextValue > 0) {
                      setSelectedProjectId(nextValue);
                      setLastProjectId(nextValue);
                    } else {
                      setSelectedProjectId("");
                    }
                  }}
                >
                  <option value="">Choose a project</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>{project.title}</option>
                  ))}
                </select>
              </label>
              <div className="text-xs text-slate-500">
                {loadingProjects ? "Loading projects..." : `${projects.length} projects available`}
              </div>
            </div>
            {searchStatus ? <p className="text-sm text-slate-500">{searchStatus}</p> : null}
          </section>

          <section className="card">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">Results</h2>
                <p className="text-sm text-slate-600">Read in app before deciding whether to keep a source.</p>
              </div>
              <div className="rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-700">
                {results.length} results
              </div>
            </div>
            <div className="space-y-3">
              {results.length === 0 ? <p className="text-sm text-slate-500">No search results loaded yet.</p> : null}
              {results.map((paper) => {
                const isActive = activePaper?.external_id === paper.external_id;
                return (
                  <div
                    key={paper.external_id}
                    className={`rounded-2xl border p-4 transition ${isActive ? "border-stone-900 bg-stone-50" : "border-stone-200 bg-stone-50/60"}`}
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div className="space-y-2">
                        <h3 className="font-medium text-slate-900">{paper.title}</h3>
                        <p className="text-sm text-slate-600">
                          {getPaperAuthorsLabel(paper.authors)} • {paper.year || "Unknown year"} • {paper.source}
                        </p>
                        <p className="text-sm leading-6 text-slate-500">{abstractText && isActive ? getPaperAbstractText(activePaper) : getPaperAbstractText(paper) || "No abstract available."}</p>
                      </div>
                      <div className="flex shrink-0 flex-col gap-2">
                        <button className="btn-secondary" onClick={() => void readPaperByExternalId(paper.external_id, paper)} type="button">
                          Read in app
                        </button>
                        <button
                          className="btn-secondary"
                          disabled={addingPaper || !selectedProjectId}
                          onClick={() => {
                            setSelectedPaper(paper);
                            setResolvedPaper(paper);
                            void addSelectedPaperToProject(paper);
                          }}
                          type="button"
                        >
                          {addingPaper && activePaper?.external_id === paper.external_id ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                          Add to project
                        </button>
                        {paper.url ? (
                          <a className="btn-secondary" href={paper.url} rel="noreferrer" target="_blank">
                            Open original
                          </a>
                        ) : null}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>

        <section className="card">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h2 className="text-xl font-semibold">Reader</h2>
              <p className="text-sm text-slate-600">Exact metadata resolution, cached uploads, and provider-normalized paper payloads all land here.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className="btn-primary" disabled={addingPaper || !activePaper} onClick={() => void addSelectedPaperToProject()} type="button">
                {addingPaper ? <LoadingSpinner /> : null}
                {addingPaper ? "Adding..." : "Add to project"}
              </button>
              {activePaper?.url ? (
                <a className="btn-secondary" href={activePaper.url} rel="noreferrer" target="_blank">
                  Open original
                </a>
              ) : null}
            </div>
          </div>

          {loadingReader ? (
            <div className="mt-6 flex items-center gap-3 text-sm text-slate-500">
              <LoadingSpinner />
              Loading paper detail...
            </div>
          ) : null}

          {!loadingReader && !activePaper ? (
            <div className="mt-6 rounded-2xl border border-dashed border-stone-300 bg-stone-50 p-5 text-sm leading-7 text-slate-600">
              Pick a result from the left, or open this page with `?external_id=...` to land directly on one paper.
            </div>
          ) : null}

          {activePaper ? (
            <div className="mt-6 space-y-5">
              <div>
                <div className="flex flex-wrap gap-2">
                  {badges.map((badge) => (
                    <span key={badge} className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-700">
                      {badge}
                    </span>
                  ))}
                </div>
                <h3 className="mt-4 text-2xl font-semibold text-slate-900">{activePaper.title}</h3>
                <p className="mt-2 text-sm text-slate-600">
                  {getPaperAuthorsLabel(activePaper.authors)} • {activePaper.year || "Unknown year"}
                </p>
              </div>

              {readerStatus ? <p className="text-sm text-slate-500">{readerStatus}</p> : null}

              <div className="rounded-2xl bg-stone-50 p-4">
                <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">Abstract</p>
                <p className="mt-3 text-sm leading-7 text-slate-700">{abstractText || "No abstract available."}</p>
              </div>

              {pdfMetadata ? (
                <div className="rounded-2xl bg-stone-50 p-4">
                  <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">PDF structure</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-stone-700">
                    {pdfMetadata.parser ? <span className="rounded-full bg-white px-2 py-1">{pdfMetadata.parser}</span> : null}
                    {pdfMetadata.page_count ? <span className="rounded-full bg-white px-2 py-1">{pdfMetadata.page_count} pages</span> : null}
                    {pdfMetadata.extracted_page_count ? <span className="rounded-full bg-white px-2 py-1">{pdfMetadata.extracted_page_count} extracted pages</span> : null}
                    {pdfMetadata.section_count ? <span className="rounded-full bg-white px-2 py-1">{pdfMetadata.section_count} sections</span> : null}
                  </div>
                  {pdfMetadata.detected_sections.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {pdfMetadata.detected_sections.map((section) => (
                        <span key={`${activePaper.external_id}-${section}`} className="rounded-full bg-white px-2 py-1 text-xs text-stone-700">
                          {section}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {pdfMetadata.pages.length ? (
                    <details className="mt-4 rounded-2xl border border-stone-200 bg-white px-3 py-3">
                      <summary className="cursor-pointer text-sm font-medium text-slate-700">Page previews</summary>
                      <div className="mt-3 space-y-3">
                        {pdfMetadata.pages.slice(0, 8).map((page) => (
                          <div key={`${activePaper.external_id}-page-${page.page_number}`} className="rounded-xl bg-stone-50 px-3 py-3">
                            <div className="flex flex-wrap gap-2">
                              <span className="text-xs font-medium uppercase tracking-[0.18em] text-stone-500">Page {page.page_number}</span>
                              {page.section_titles.map((section) => (
                                <span key={`${activePaper.external_id}-page-${page.page_number}-${section}`} className="rounded-full bg-white px-2 py-1 text-xs text-stone-700">
                                  {section}
                                </span>
                              ))}
                            </div>
                            {page.preview ? <p className="mt-2 text-sm leading-6 text-slate-600">{page.preview}</p> : null}
                          </div>
                        ))}
                        {pdfMetadata.pages.length > 8 ? (
                          <p className="text-xs text-slate-500">Showing the first 8 pages of {pdfMetadata.pages.length}.</p>
                        ) : null}
                      </div>
                    </details>
                  ) : null}
                </div>
              ) : null}

              <div className="rounded-2xl bg-stone-50 p-4">
                <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">Reader text</p>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">
                  {readerText || "No reader text available for this source yet."}
                </p>
              </div>

              {activePaper.extraction_error ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                  {activePaper.extraction_error}
                </div>
              ) : null}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
