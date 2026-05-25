type UpdateRun = {
  id: number;
  status: string;
  run_type: string;
  trigger_type: string;
  provider: string;
  summary: string;
  current_step?: string;
  progress_message?: string;
  total_steps?: number;
  completed_steps?: number;
  created_at: string;
  started_at?: string;
  finished_at?: string | null;
  error_message?: string;
  papers_found?: number;
  papers_added?: number;
  evidence_created?: number;
  affected_sections_count?: number;
};

function formatRunType(runType: string) {
  return runType.replaceAll("_", " ");
}

export default function UpdateHistoryPanel({ runs }: { runs: UpdateRun[] }) {
  return (
    <section className="card">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Update history</h2>
          <p className="text-sm text-slate-600">Recent extraction and note compilation runs for this project.</p>
        </div>
      </div>
      <div className="space-y-3">
        {runs.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-stone-300 bg-stone-50 px-4 py-5 text-sm text-slate-500">
            No project updates yet. The first extraction or note generation run will show up here.
          </div>
        ) : null}
        {runs.map((run) => (
          <div key={run.id} className="rounded-2xl border border-stone-200 bg-stone-50/60 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-white px-2 py-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                {formatRunType(run.run_type)}
              </span>
              <span className="rounded-full bg-white px-2 py-1 text-xs text-slate-600">{run.status}</span>
              {run.provider ? <span className="rounded-full bg-white px-2 py-1 text-xs text-slate-600">{run.provider}</span> : null}
            </div>
            <p className="mt-3 text-sm text-slate-700">{run.summary || "No summary available."}</p>
            {run.current_step ? <p className="mt-2 text-xs font-medium uppercase tracking-wide text-stone-500">{run.current_step}</p> : null}
            {run.progress_message ? <p className="mt-1 text-sm text-slate-600">{run.progress_message}</p> : null}
            {typeof run.total_steps === "number" && run.total_steps > 0 ? (
              <div className="mt-3">
                <div className="h-2 overflow-hidden rounded-full bg-stone-200">
                  <div
                    className="h-full rounded-full bg-stone-700 transition-all"
                    style={{ width: `${Math.min(100, Math.round(((run.completed_steps || 0) / run.total_steps) * 100))}%` }}
                  />
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  {run.completed_steps || 0}/{run.total_steps} steps
                  {run.papers_found ? ` • ${run.papers_found} found` : ""}
                  {run.papers_added ? ` • ${run.papers_added} added` : ""}
                  {run.evidence_created ? ` • ${run.evidence_created} evidence` : ""}
                  {run.affected_sections_count ? ` • ${run.affected_sections_count} sections` : ""}
                </p>
              </div>
            ) : null}
            <p className="mt-2 text-xs text-slate-500">
              Started {new Date(run.created_at).toLocaleString()}
              {run.finished_at ? ` • finished ${new Date(run.finished_at).toLocaleString()}` : ""}
            </p>
            {run.error_message ? <p className="mt-2 text-xs text-rose-600">{run.error_message}</p> : null}
          </div>
        ))}
      </div>
    </section>
  );
}
