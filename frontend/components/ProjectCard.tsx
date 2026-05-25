import Link from "next/link";

export type Project = {
  id: number;
  title: string;
  topic: string;
  description: string;
  auto_refresh_enabled?: boolean;
  refresh_cadence?: string;
  digest_enabled?: boolean;
  last_refreshed_at?: string | null;
  next_refresh_due_at?: string | null;
  updated_at?: string;
};

export default function ProjectCard({
  project,
  compact = false,
  health,
}: {
  project: Project;
  compact?: boolean;
  health?: {
    freshness_status?: string;
    pending_review_count?: number;
    locked_attention_count?: number;
  };
}) {
  return (
    <Link href={`/projects/${project.id}`} className="card block transition hover:-translate-y-0.5 hover:border-stone-300">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">Research project</p>
          <h3 className="mt-2 text-xl font-semibold">{project.title}</h3>
        </div>
        {project.updated_at ? (
          <span className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-700">
            {new Date(project.updated_at).toLocaleDateString()}
          </span>
        ) : null}
      </div>
      <p className="mt-4 line-clamp-3 text-sm leading-6 text-slate-600">{project.topic}</p>
      <p className="mt-4 text-sm text-slate-500">{project.description || "Living note, evidence, and source workspace."}</p>
      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        {health?.freshness_status ? (
          <span className="rounded-full bg-stone-100 px-2 py-1 text-stone-700">{health.freshness_status}</span>
        ) : null}
        {typeof health?.pending_review_count === "number" ? (
          <span className="rounded-full bg-stone-100 px-2 py-1 text-stone-700">{health.pending_review_count} pending</span>
        ) : null}
        {typeof health?.locked_attention_count === "number" ? (
          <span className="rounded-full bg-stone-100 px-2 py-1 text-stone-700">{health.locked_attention_count} locked</span>
        ) : null}
        {!compact && project.refresh_cadence ? (
          <span className="rounded-full bg-stone-100 px-2 py-1 text-stone-700">{project.refresh_cadence}</span>
        ) : null}
      </div>
    </Link>
  );
}
