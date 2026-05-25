"use client";

import Link from "next/link";
import { useState } from "react";
import { apiFetch, getApiErrorMessage } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";
import LoadingSpinner from "@/components/LoadingSpinner";
import type { PaperCandidate } from "@/lib/papers";

export default function PaperSearchPanel({
  projectId,
  onPaperAdded,
}: {
  projectId: number;
  onPaperAdded?: () => Promise<void> | void;
}) {
  const { showToast } = useToast();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PaperCandidate[]>([]);
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [addingPaperId, setAddingPaperId] = useState<string | null>(null);

  async function search() {
    if (!query.trim()) {
      setStatus("Enter a topic or query before searching.");
      setResults([]);
      return;
    }

    setLoading(true);
    setStatus("Searching...");
    try {
      const data = await apiFetch<PaperCandidate[]>("/papers/search", {
        method: "POST",
        body: JSON.stringify({ query: query.trim() }),
      });
      setResults(data);
      setStatus(
        data.length
          ? `Found ${data.length} candidate sources from ${data[0]?.source || "the selected provider"}.`
          : "No papers matched this query yet. Try a broader topic or refresh wording.",
      );
    } catch (error) {
      const message = getApiErrorMessage(error, "Search failed");
      setStatus(message);
      showToast({ tone: "error", title: "Search failed", message });
    } finally {
      setLoading(false);
    }
  }

  async function addPaper(paper: PaperCandidate) {
    setAddingPaperId(paper.external_id);
    setStatus(`Adding ${paper.title}...`);
    try {
      await apiFetch(`/papers/projects/${projectId}/add`, {
        method: "POST",
        body: JSON.stringify(paper),
      });
      await onPaperAdded?.();
      setStatus(`Added: ${paper.title}`);
      showToast({ tone: "success", title: "Paper added", message: `${paper.title} is now part of this project.` });
    } catch (error) {
      const message = getApiErrorMessage(error, "Failed to add paper");
      setStatus(message);
      showToast({ tone: "error", title: "Could not add paper", message });
    } finally {
      setAddingPaperId(null);
    }
  }

  return (
    <div className="card space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Search candidate papers</h2>
        <p className="text-sm text-slate-600">
          Search the active provider set by the backend environment. Mock stays available as the local fallback.
        </p>
      </div>
      <div className="flex gap-2">
        <input
          className="input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. multimodal retrieval benchmark"
        />
        <button className="btn-primary" disabled={loading} onClick={search} type="button">
          {loading ? <LoadingSpinner /> : null}
          {loading ? "Searching..." : "Search"}
        </button>
      </div>
      {status ? <p className="text-sm text-slate-500">{status}</p> : null}
      <div className="space-y-3">
        {results.map((paper) => (
          <div key={paper.external_id} className="rounded-2xl border border-stone-200 bg-stone-50/60 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-medium">{paper.title}</h3>
                <p className="mt-1 text-sm text-slate-600">
                  {paper.authors || "Unknown authors"} • {paper.year || "Unknown year"} • {paper.source}
                </p>
                <p className="mt-2 text-sm text-slate-500">{paper.abstract || "No abstract available."}</p>
              </div>
              <div className="flex shrink-0 flex-col gap-2">
                <button className="btn-secondary" disabled={addingPaperId === paper.external_id} onClick={() => addPaper(paper)} type="button">
                  {addingPaperId === paper.external_id ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                  {addingPaperId === paper.external_id ? "Adding..." : "Add"}
                </button>
                <Link
                  className="btn-secondary"
                  href={`/papers?external_id=${encodeURIComponent(paper.external_id)}&project_id=${projectId}&query=${encodeURIComponent(query.trim())}`}
                >
                  Read
                </Link>
                {paper.url ? (
                  <a className="btn-secondary" href={paper.url} rel="noreferrer" target="_blank">
                    Open
                  </a>
                ) : null}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
