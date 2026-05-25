"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiFetch, getApiErrorMessage, isApiError } from "@/lib/api";
import { getLastProjectId } from "@/lib/local-state";
import ProjectCard, { Project } from "@/components/ProjectCard";
import { EvidenceCard } from "@/components/EvidenceList";

const isDevelopment = process.env.NODE_ENV !== "production";

type RecentNote = {
  project_id: number;
  project_title: string;
  title: string;
  updated_at: string;
  metadata?: { source_count?: number; evidence_count?: number };
};

type DashboardSource = {
  project_id: number;
  project_title: string;
  paper_id: number;
  title: string;
  extraction_status: string;
  ingestion_status: string;
  updated_hint: string;
};

type DashboardSummary = {
  recent_projects: Project[];
  recent_notes: RecentNote[];
  recent_evidence: EvidenceCard[];
  pending_sources: DashboardSource[];
  stale_projects: Project[];
  pending_suggestions: Array<{ id: number; project_id: number; project_title: string; target_section: string; status: string; created_at: string }>;
  locked_attention: Array<{ suggestion_id: number; project_id: number; project_title: string; target_section: string; status: string }>;
  recent_versions: Array<{ id: number; project_id: number; project_title: string; version_number: number; version_kind: string; created_at: string }>;
  recommended_actions: Array<{ kind: string; project_id: number; project_title: string; label: string; href: string }>;
  project_health: Array<{ project_id: number; freshness_status: string; freshness_reason: string; pending_review_count: number; locked_attention_count: number; stale_note: boolean; evidence_growth_week: number }>;
  counts: {
    project_count: number;
    note_count: number;
    evidence_count: number;
    pending_source_count: number;
    stale_project_count: number;
    pending_suggestion_count: number;
    locked_attention_count: number;
  };
};

function EmptyDashboard({ lastProjectId }: { lastProjectId: number | null }) {
  return (
    <div className="space-y-6">
      <section className="card">
        <p className="text-xs font-medium uppercase tracking-[0.28em] text-stone-500">Weekly research dashboard</p>
        <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-tight text-slate-900">
          Your workspace is ready. The dashboard will become more useful as soon as a project starts moving.
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600">
          Start a project, add one source, and the system will begin tracking evidence, notes, freshness, and review work for you.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/projects/new" className="btn-primary">Create first project</Link>
          {lastProjectId ? <Link href={`/projects/${lastProjectId}`} className="btn-secondary">Resume last project</Link> : null}
          <Link href="/projects" className="btn-secondary">Open project library</Link>
        </div>
      </section>
      <section className="grid gap-4 md:grid-cols-3">
        <div className="card text-sm text-slate-600">1. Create a project around one topic you revisit weekly.</div>
        <div className="card text-sm text-slate-600">2. Add papers or upload cleaned text to build your source library.</div>
        <div className="card text-sm text-slate-600">3. Extract evidence, review it, and compile your living note.</div>
      </section>
    </div>
  );
}

export default function HomePage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [status, setStatus] = useState("Loading your weekly dashboard...");
  const [needsLogin, setNeedsLogin] = useState(false);
  const [dashboardUnavailable, setDashboardUnavailable] = useState(false);
  const [lastProjectId, setStoredLastProjectId] = useState<number | null>(null);

  useEffect(() => {
    setStoredLastProjectId(getLastProjectId());
    apiFetch<DashboardSummary>("/workspace/summary")
      .then((response) => {
        setData(response);
        setStatus("");
      })
      .catch((error) => {
        if (isApiError(error) && error.status === 401) {
          setNeedsLogin(true);
          setStatus("");
          return;
        }
        if (isApiError(error) && error.status === 404) {
          setDashboardUnavailable(true);
          setStatus("");
          return;
        }
        setStatus(getApiErrorMessage(error, "Failed to load workspace"));
      });
  }, []);

  const healthMap = useMemo(() => {
    const map = new Map<number, DashboardSummary["project_health"][number]>();
    data?.project_health.forEach((item) => map.set(item.project_id, item));
    return map;
  }, [data]);

  if (needsLogin) {
    return (
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <section className="card">
          <p className="text-xs font-medium uppercase tracking-[0.28em] text-stone-500">Personal research workspace</p>
          <h1 className="mt-3 text-4xl font-semibold leading-tight">Open your research workspace and continue your project notes.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600">
            Sign in to review stale projects, pending suggestions, locked sections, and your latest living notes.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/login" className="btn-primary">Login</Link>
            <Link href="/projects" className="btn-secondary">Go to projects</Link>
          </div>
        </section>
        {isDevelopment ? (
          <section className="card">
            <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">Development demo account</p>
            <p className="mt-3 text-sm text-slate-700">test@example.com</p>
            <p className="text-sm text-slate-700">password123</p>
          </section>
        ) : (
          <section className="card">
            <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">Account access</p>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Use an existing account or register through the API before publishing a shared deployment.
            </p>
          </section>
        )}
      </div>
    );
  }

  if (dashboardUnavailable) {
    return (
      <div className="space-y-6">
        <section className="card">
          <p className="text-xs font-medium uppercase tracking-[0.28em] text-stone-500">Dashboard unavailable</p>
          <h1 className="mt-3 text-4xl font-semibold leading-tight">This backend session does not expose the workspace dashboard yet.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600">
            You can still work normally from the project library. If you just updated the codebase, restart the backend and the dashboard routes should appear.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/projects" className="btn-primary">Open projects</Link>
            <Link href="/digests" className="btn-secondary">Try digests</Link>
          </div>
        </section>
      </div>
    );
  }

  if (!data) {
    return <div className="card text-slate-600">{status}</div>;
  }

  if (data.counts.project_count === 0) {
    return <EmptyDashboard lastProjectId={lastProjectId} />;
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="card">
          <p className="text-xs font-medium uppercase tracking-[0.28em] text-stone-500">Weekly research dashboard</p>
          <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-tight text-slate-900">
            See what changed, what is stale, and what deserves your attention in under 30 seconds.
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600">
            Review recent project activity, pending work, locked sections, and the next actions worth taking.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/projects/new" className="btn-primary">Create project</Link>
            {lastProjectId ? <Link href={`/projects/${lastProjectId}`} className="btn-secondary">Resume last project</Link> : null}
            <Link href="/digests" className="btn-secondary">Open digests</Link>
            <Link href="/projects" className="btn-secondary">Project library</Link>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-2">
          {[
            ["Projects", data.counts.project_count],
            ["Pending suggestions", data.counts.pending_suggestion_count],
            ["Stale projects", data.counts.stale_project_count],
            ["Locked attention", data.counts.locked_attention_count],
          ].map(([label, value]) => (
            <div key={label} className="card">
              <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">{label}</p>
              <p className="mt-3 text-3xl font-semibold">{value}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold">Recommended next actions</h2>
              <p className="text-sm text-slate-600">Deterministic suggestions based on staleness, pending review work, and locked sections.</p>
            </div>
            <Link href="/digests" className="btn-secondary">Weekly digest</Link>
          </div>
          <div className="space-y-3">
            {data.recommended_actions.length === 0 ? <p className="text-sm text-slate-500">No urgent actions. Your workspace looks steady.</p> : null}
            {data.recommended_actions.map((action, index) => (
              <Link key={`${action.kind}-${index}`} href={action.href} className="block rounded-2xl border border-stone-200 bg-stone-50/70 p-4 transition hover:border-stone-300">
                <p className="text-sm font-medium text-slate-800">{action.label}</p>
                <p className="mt-2 text-xs text-slate-500">{action.project_title}</p>
              </Link>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold">Projects needing attention</h2>
              <p className="text-sm text-slate-600">Freshness and review signals that suggest where to spend the next hour.</p>
            </div>
          </div>
          <div className="space-y-3">
            {data.stale_projects.length === 0 ? <p className="text-sm text-slate-500">No stale projects right now.</p> : null}
            {data.stale_projects.map((project) => {
              const health = healthMap.get(project.id);
              return (
                <Link key={project.id} href={`/projects/${project.id}`} className="block rounded-2xl border border-stone-200 bg-stone-50/70 p-4 transition hover:border-stone-300">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="font-medium">{project.title}</h3>
                    <span className="rounded-full bg-white px-2 py-1 text-xs text-slate-600">{health?.freshness_status || "stale"}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{health?.freshness_reason}</p>
                  <p className="mt-2 text-xs text-slate-500">
                    {health?.pending_review_count ?? 0} pending suggestions, {health?.locked_attention_count ?? 0} locked attention
                  </p>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr_1fr]">
        <div className="card">
          <h2 className="text-2xl font-semibold">Recent projects</h2>
          <div className="mt-4 grid gap-4">
            {data.recent_projects.length === 0 ? <p className="text-sm text-slate-500">No projects yet.</p> : null}
            {data.recent_projects.map((project) => (
              <ProjectCard key={project.id} project={project} compact health={healthMap.get(project.id)} />
            ))}
          </div>
        </div>

        <div className="card">
          <h2 className="text-2xl font-semibold">Pending review work</h2>
          <div className="mt-4 space-y-3">
            {data.pending_suggestions.length === 0 ? <p className="text-sm text-slate-500">No pending suggestions yet.</p> : null}
            {data.pending_suggestions.map((item) => (
              <Link key={item.id} href={`/projects/${item.project_id}/history`} className="block rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
                <p className="font-medium text-slate-800">{item.project_title}</p>
                <p className="mt-2 text-sm text-slate-600">Review section: {item.target_section}</p>
              </Link>
            ))}
            {data.locked_attention.length ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50/60 p-4">
                <p className="text-sm font-medium text-rose-800">Locked sections waiting for review</p>
                <p className="mt-2 text-xs text-rose-700">{data.locked_attention.length} suggestions are blocked by locks and need manual attention.</p>
              </div>
            ) : null}
          </div>
        </div>

        <div className="card">
          <h2 className="text-2xl font-semibold">This week</h2>
          <div className="mt-4 space-y-3">
            {data.recent_versions.map((version) => (
              <Link key={version.id} href={`/projects/${version.project_id}/history`} className="block rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
                <p className="font-medium text-slate-800">{version.project_title}</p>
                <p className="mt-2 text-sm text-slate-600">{`Version ${version.version_number} • ${version.version_kind}`}</p>
              </Link>
            ))}
            {data.recent_evidence.slice(0, 2).map((card) => (
              <Link key={card.id} href={`/projects/${card.project_id}/evidence`} className="block rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
                <p className="text-xs uppercase tracking-wide text-stone-500">{card.card_type}</p>
                <p className="mt-2 text-sm text-slate-700 line-clamp-3">{card.content}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
