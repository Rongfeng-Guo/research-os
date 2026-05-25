"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiFetch, getApiErrorMessage } from "@/lib/api";
import { setLastProjectId } from "@/lib/local-state";

type UpdateRun = {
  id: number;
  status: string;
  run_type: string;
  summary: string;
  created_at: string;
  finished_at?: string | null;
  papers_found: number;
  papers_added: number;
  evidence_created: number;
  affected_sections_count: number;
};

type Suggestion = {
  id: number;
  target_section: string;
  target_section_title?: string;
  target_section_locked?: boolean;
  suggestion_type: string;
  rationale: string;
  proposed_text: string;
  status: string;
  supporting_sources: string[];
  diff?: { blocks?: Array<{ kind: string; before: string; after: string }>; summary?: Record<string, number> };
  created_at: string;
};

type Version = {
  id: number;
  version_number: number;
  markdown: string;
  version_kind: string;
  source_suggestion_ids: number[];
  metadata?: { generation_mode?: string; source_count?: number; evidence_count?: number; last_update_source?: string };
  update_run_id?: number | null;
  created_at: string;
};

type VersionComparison = {
  base_version_id: number;
  compare_version_id: number;
  diff: { blocks?: Array<{ kind: string; before: string; after: string }>; summary?: Record<string, number> };
};

type ProjectDetail = {
  project: { title: string };
  update_runs: UpdateRun[];
  note_update_suggestions: Suggestion[];
  note_versions: Version[];
};

function VersionDiff({ comparison }: { comparison: VersionComparison | null }) {
  if (!comparison?.diff?.blocks?.length) {
    return <p className="text-sm text-slate-500">Select versions to compare.</p>;
  }
  return (
    <div className="space-y-3">
      {comparison.diff.blocks.map((block, index) => (
        <div key={`${block.kind}-${index}`} className="grid gap-3 xl:grid-cols-2">
          <div className="rounded-2xl bg-stone-50 p-3 text-sm text-slate-600">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-stone-500">Before</p>
            <p className="whitespace-pre-wrap">{block.before || "No previous content."}</p>
          </div>
          <div className={`rounded-2xl p-3 text-sm ${block.kind === "added" ? "bg-emerald-50 text-emerald-800" : block.kind === "removed" ? "bg-rose-50 text-rose-700" : block.kind === "changed" ? "bg-sky-50 text-sky-900" : "bg-white text-slate-700"}`}>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-stone-500">After</p>
            <p className="whitespace-pre-wrap">{block.after || "No replacement content."}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ProjectHistoryPage({ params }: { params: { id: string } }) {
  const projectId = Number(params.id);
  const [data, setData] = useState<ProjectDetail | null>(null);
  const [status, setStatus] = useState("Loading history...");
  const [baseVersionId, setBaseVersionId] = useState<number | null>(null);
  const [compareVersionId, setCompareVersionId] = useState<number | null>(null);
  const [comparison, setComparison] = useState<VersionComparison | null>(null);

  useEffect(() => {
    apiFetch<ProjectDetail>(`/projects/${projectId}`)
      .then((result) => {
        setData(result);
        setLastProjectId(projectId);
        setStatus("");
      })
      .catch((error) => setStatus(getApiErrorMessage(error, "Failed to load history")));
  }, [projectId]);

  useEffect(() => {
    if (!data?.note_versions.length) return;
    setBaseVersionId(data.note_versions[0].id);
    setCompareVersionId(data.note_versions[1]?.id || null);
  }, [data]);

  useEffect(() => {
    if (!baseVersionId || !compareVersionId) return;
    apiFetch<VersionComparison>(`/notes/projects/${projectId}/versions/${baseVersionId}/compare?against_version_id=${compareVersionId}`)
      .then(setComparison)
      .catch(() => setComparison(null));
  }, [baseVersionId, compareVersionId, projectId]);

  const versionOptions = useMemo(() => data?.note_versions || [], [data]);

  if (!data) {
    return <div className="card text-slate-600">{status}</div>;
  }

  return (
    <div className="space-y-6">
      <section className="card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.24em] text-stone-500">Living note maintenance</p>
            <h1 className="mt-2 text-4xl font-semibold">History and review</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Review note versions, update runs, and suggestion diffs for {data.project.title}.
            </p>
          </div>
          <Link className="btn-secondary" href={`/projects/${projectId}`}>Back to project</Link>
        </div>
      </section>

      <section className="card">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Version comparison</h2>
            <p className="text-sm text-slate-600">Compare two versions to see exactly what changed in the notebook.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <select className="input w-auto min-w-[220px]" value={baseVersionId || ""} onChange={(e) => setBaseVersionId(Number(e.target.value))}>
              {versionOptions.map((version) => (
                <option key={version.id} value={version.id}>Base v{version.version_number}</option>
              ))}
            </select>
            <select className="input w-auto min-w-[220px]" value={compareVersionId || ""} onChange={(e) => setCompareVersionId(Number(e.target.value))}>
              <option value="">Select version</option>
              {versionOptions.map((version) => (
                <option key={version.id} value={version.id}>Compare v{version.version_number}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-4">
          <VersionDiff comparison={comparison} />
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="card">
          <h2 className="text-xl font-semibold">Note versions</h2>
          <div className="mt-4 space-y-3">
            {data.note_versions.length === 0 ? <p className="text-sm text-slate-500">No note versions yet.</p> : null}
            {data.note_versions.map((version) => (
              <div key={version.id} className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="rounded-full bg-white px-2 py-1 text-slate-600">v{version.version_number}</span>
                  <span className="rounded-full bg-white px-2 py-1 text-slate-600">{version.version_kind}</span>
                  <span className="rounded-full bg-white px-2 py-1 text-slate-600">{version.metadata?.generation_mode || "default"}</span>
                </div>
                <p className="mt-3 text-xs text-slate-500">
                  {new Date(version.created_at).toLocaleString()} • sources {version.metadata?.source_count ?? 0} • evidence {version.metadata?.evidence_count ?? 0}
                </p>
                {version.source_suggestion_ids?.length ? (
                  <p className="mt-2 text-xs text-slate-500">Suggestions: {version.source_suggestion_ids.join(", ")}</p>
                ) : null}
                <pre className="mt-3 max-h-52 overflow-auto rounded-2xl bg-white p-3 text-xs leading-6 text-slate-600">{version.markdown}</pre>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <h2 className="text-xl font-semibold">Update runs</h2>
            <div className="mt-4 space-y-3">
              {data.update_runs.length === 0 ? <p className="text-sm text-slate-500">No update runs yet.</p> : null}
              {data.update_runs.map((run) => (
                <div key={run.id} className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="rounded-full bg-white px-2 py-1 text-slate-600">{run.run_type}</span>
                    <span className="rounded-full bg-white px-2 py-1 text-slate-600">{run.status}</span>
                  </div>
                  <p className="mt-3 text-sm text-slate-700">{run.summary}</p>
                  <p className="mt-2 text-xs text-slate-500">
                    {run.papers_found} found • {run.papers_added} added • {run.evidence_created} evidence • {run.affected_sections_count} affected sections
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h2 className="text-xl font-semibold">Pending and past suggestions</h2>
            <div className="mt-4 space-y-3">
              {data.note_update_suggestions.length === 0 ? <p className="text-sm text-slate-500">No suggestions yet.</p> : null}
              {data.note_update_suggestions.map((suggestion) => (
                <div key={suggestion.id} className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="rounded-full bg-white px-2 py-1 text-slate-600">{suggestion.target_section_title || suggestion.target_section}</span>
                    <span className="rounded-full bg-white px-2 py-1 text-slate-600">{suggestion.status}</span>
                    {suggestion.target_section_locked ? (
                      <span className="rounded-full bg-rose-100 px-2 py-1 text-rose-700">Locked section</span>
                    ) : null}
                  </div>
                  <p className="mt-3 text-sm text-slate-700">{suggestion.rationale}</p>
                  {suggestion.supporting_sources.length ? (
                    <p className="mt-2 text-xs text-slate-500">Sources: {suggestion.supporting_sources.join(", ")}</p>
                  ) : null}
                  {suggestion.diff?.blocks?.length ? (
                    <div className="mt-3 grid gap-3">
                      {suggestion.diff.blocks.slice(0, 2).map((block, index) => (
                        <div key={index} className="grid gap-3 xl:grid-cols-2">
                          <div className="whitespace-pre-wrap rounded-2xl bg-stone-100 p-3 text-xs text-slate-600">{block.before || "No previous content."}</div>
                          <div className="whitespace-pre-wrap rounded-2xl bg-white p-3 text-xs text-slate-700">{block.after || "No replacement content."}</div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
