"use client";

import { useState } from "react";
import LoadingSpinner from "@/components/LoadingSpinner";

type DiffBlock = {
  kind: string;
  before: string;
  after: string;
};

type Suggestion = {
  id: number;
  target_section: string;
  target_section_title?: string;
  target_section_locked?: boolean;
  suggestion_type: string;
  current_text: string;
  proposed_text: string;
  rationale: string;
  supporting_evidence_ids?: number[];
  supporting_sources: string[];
  diff?: { blocks?: DiffBlock[]; summary?: Record<string, number> };
  status: string;
  created_at: string;
  applied_at?: string | null;
  applied_by?: string;
};

function DiffView({ blocks }: { blocks?: DiffBlock[] }) {
  if (!blocks || blocks.length === 0) {
    return <p className="text-sm text-slate-500">No diff blocks available.</p>;
  }

  return (
    <div className="space-y-3">
      {blocks.map((block, index) => (
        <div key={`${block.kind}-${index}`} className="grid gap-3 xl:grid-cols-2">
          <div className={`rounded-2xl p-3 text-sm ${block.kind === "added" ? "bg-stone-50 text-slate-400" : block.kind === "removed" ? "bg-rose-50 text-rose-700" : block.kind === "changed" ? "bg-amber-50 text-amber-900" : "bg-white text-slate-600"}`}>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-stone-500">Before</p>
            <p className="whitespace-pre-wrap">{block.before || "No previous content."}</p>
          </div>
          <div className={`rounded-2xl p-3 text-sm ${block.kind === "removed" ? "bg-stone-50 text-slate-400" : block.kind === "added" ? "bg-emerald-50 text-emerald-800" : block.kind === "changed" ? "bg-sky-50 text-sky-900" : "bg-white text-slate-700"}`}>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-stone-500">After</p>
            <p className="whitespace-pre-wrap">{block.after || "No replacement content."}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function SuggestionPanel({
  suggestions,
  onStatusChange,
  onApplyAccepted,
  onApplySuggestion,
  onApplySection,
  onApplySelected,
}: {
  suggestions: Suggestion[];
  onStatusChange?: (suggestionId: number, status: string) => Promise<void> | void;
  onApplyAccepted?: () => Promise<void> | void;
  onApplySuggestion?: (suggestionId: number) => Promise<void> | void;
  onApplySection?: (sectionSlug: string, suggestionIds?: number[]) => Promise<void> | void;
  onApplySelected?: (suggestionIds: number[]) => Promise<void> | void;
}) {
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const pendingCount = suggestions.filter((item) => item.status === "suggested").length;
  const acceptedCount = suggestions.filter((item) => item.status === "accepted").length;
  const acceptedSelectableIds = suggestions.filter((item) => item.status === "accepted" && !item.applied_at).map((item) => item.id);
  const selectedAcceptedIds = selectedIds.filter((id) => acceptedSelectableIds.includes(id));

  function toggleSelectedSuggestion(suggestionId: number) {
    setSelectedIds((current) => (current.includes(suggestionId) ? current.filter((id) => id !== suggestionId) : [...current, suggestionId]));
  }

  function clearSelection() {
    setSelectedIds([]);
  }

  function getSelectedIdsForSection(sectionSlug: string) {
    return selectedAcceptedIds.filter((id) => suggestions.some((item) => item.id === id && item.target_section === sectionSlug));
  }

  async function runAction(key: string, action: () => Promise<void> | void) {
    try {
      setBusyKey(key);
      await action();
      if (key.startsWith("apply")) {
        clearSelection();
      }
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="card">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-xl font-semibold">Suggested note updates</h2>
          <p className="text-sm text-slate-600">Review deterministic section diffs, inspect rationale, and apply only the changes you actually want.</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-stone-100 px-3 py-1 text-stone-700">{pendingCount} pending</span>
          <span className="rounded-full bg-stone-100 px-3 py-1 text-stone-700">{acceptedCount} accepted</span>
          {selectedAcceptedIds.length ? <span className="rounded-full bg-amber-100 px-3 py-1 text-amber-800">{selectedAcceptedIds.length} selected</span> : null}
          {onApplySelected && selectedAcceptedIds.length ? (
            <button
              className="btn-secondary"
              disabled={busyKey === "apply-selected"}
              onClick={() => void runAction("apply-selected", () => onApplySelected(selectedAcceptedIds))}
              type="button"
            >
              {busyKey === "apply-selected" ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
              Apply selected
            </button>
          ) : null}
          {selectedIds.length ? (
            <button className="btn-secondary" disabled={Boolean(busyKey)} onClick={clearSelection} type="button">
              Clear selection
            </button>
          ) : null}
          {onApplyAccepted ? (
            <button
              className="btn-primary"
              disabled={busyKey === "apply-accepted"}
              onClick={() => void runAction("apply-accepted", onApplyAccepted)}
              type="button"
            >
              {busyKey === "apply-accepted" ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
              Apply accepted
            </button>
          ) : null}
        </div>
      </div>
      <div className="space-y-3">
        {suggestions.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-stone-300 bg-stone-50 px-4 py-5 text-sm text-slate-500">
            No update suggestions yet. Run a topic refresh after new evidence arrives.
          </div>
        ) : null}
        {suggestions.map((suggestion) => (
          <div key={suggestion.id} className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {suggestion.status === "accepted" && !suggestion.applied_at ? (
                <label className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-2 py-1 text-amber-900">
                  <input
                    checked={selectedIds.includes(suggestion.id)}
                    disabled={Boolean(busyKey)}
                    onChange={() => toggleSelectedSuggestion(suggestion.id)}
                    type="checkbox"
                  />
                  Select
                </label>
              ) : null}
              <span className="rounded-full bg-white px-2 py-1 text-slate-600">{suggestion.target_section_title || suggestion.target_section}</span>
              <span className="rounded-full bg-white px-2 py-1 text-slate-600">{suggestion.suggestion_type}</span>
              <span className="rounded-full bg-white px-2 py-1 text-slate-600">{suggestion.status}</span>
              {suggestion.target_section_locked ? (
                <span className="rounded-full bg-rose-100 px-2 py-1 text-rose-700">Locked section: review only unless manually applied</span>
              ) : null}
              {suggestion.applied_at ? (
                <span className="rounded-full bg-emerald-100 px-2 py-1 text-emerald-700">Applied {new Date(suggestion.applied_at).toLocaleDateString()}</span>
              ) : null}
            </div>
            <p className="mt-3 text-sm text-slate-700">{suggestion.rationale}</p>
            {suggestion.diff?.summary ? (
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-white px-2 py-1 text-slate-600">+ {suggestion.diff.summary.added || 0}</span>
                <span className="rounded-full bg-white px-2 py-1 text-slate-600">~ {suggestion.diff.summary.changed || 0}</span>
                <span className="rounded-full bg-white px-2 py-1 text-slate-600">- {suggestion.diff.summary.removed || 0}</span>
              </div>
            ) : null}
            <div className="mt-4">
              <DiffView blocks={suggestion.diff?.blocks} />
            </div>
            {suggestion.supporting_sources.length ? (
              <p className="mt-3 text-xs text-slate-500">Sources: {suggestion.supporting_sources.join(", ")}</p>
            ) : null}
            {suggestion.supporting_evidence_ids?.length ? (
              <p className="mt-2 text-xs text-slate-500">Evidence IDs: {suggestion.supporting_evidence_ids.join(", ")}</p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              {onStatusChange ? (
                <>
                  <button
                    className="btn-secondary"
                    disabled={busyKey === `status-${suggestion.id}`}
                    onClick={() => void runAction(`status-${suggestion.id}`, () => onStatusChange(suggestion.id, "accepted"))}
                    type="button"
                  >
                    {busyKey === `status-${suggestion.id}` ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                    Accept
                  </button>
                  <button
                    className="btn-secondary"
                    disabled={busyKey === `status-${suggestion.id}`}
                    onClick={() => void runAction(`status-${suggestion.id}`, () => onStatusChange(suggestion.id, "rejected"))}
                    type="button"
                  >
                    {busyKey === `status-${suggestion.id}` ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                    Reject
                  </button>
                  <button
                    className="btn-secondary"
                    disabled={busyKey === `status-${suggestion.id}`}
                    onClick={() => void runAction(`status-${suggestion.id}`, () => onStatusChange(suggestion.id, "suggested"))}
                    type="button"
                  >
                    {busyKey === `status-${suggestion.id}` ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                    Defer
                  </button>
                </>
              ) : null}
              {onApplySuggestion ? (
                <button
                  className="btn-secondary"
                  disabled={busyKey === `apply-${suggestion.id}`}
                  onClick={() => void runAction(`apply-${suggestion.id}`, () => onApplySuggestion(suggestion.id))}
                  type="button"
                >
                  {busyKey === `apply-${suggestion.id}` ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                  Apply this suggestion
                </button>
              ) : null}
              {onApplySection ? (
                <button
                  className="btn-secondary"
                  disabled={busyKey === `section-${suggestion.target_section}`}
                  onClick={() =>
                    void runAction(`section-${suggestion.target_section}`, () =>
                      onApplySection(suggestion.target_section, getSelectedIdsForSection(suggestion.target_section)),
                    )
                  }
                  type="button"
                >
                  {busyKey === `section-${suggestion.target_section}` ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                  {getSelectedIdsForSection(suggestion.target_section).length ? "Apply selected in section" : "Apply accepted in section"}
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
