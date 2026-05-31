"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch, getApiErrorMessage, isApiError } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";
import LoadingSpinner from "@/components/LoadingSpinner";

type Digest = {
  id: number;
  period_start: string;
  period_end: string;
  included_project_ids: number[];
  summary: {
    project_count?: number;
    projects_updated?: number;
    new_papers_found?: number;
    papers_added?: number;
    new_evidence_cards?: number;
    accepted_evidence_count?: number;
    rejected_evidence_count?: number;
    notes_updated?: number;
    pending_update_suggestions?: number;
    locked_sections_awaiting_review?: number;
    recommended_next_actions?: number;
    projects?: Array<{ project_id: number; project_title: string; freshness_status: string; pending_review_count: number; locked_attention_count: number }>;
  };
  markdown: string;
  metadata?: { days?: number; generated_from?: string };
  delivery_status?: string;
  delivery_target?: string;
  delivery_message?: string;
  delivered_at?: string | null;
  generated_at: string;
};

type DigestDeliveryResult = {
  digest_id: number;
  status: string;
  target: string;
  message: string;
  delivered_at?: string | null;
  payload?: { filename?: string; content_type?: string; content?: string; vault_relative_path?: string; [key: string]: unknown };
};

export default function DigestsPage() {
  const { showToast } = useToast();
  const [digests, setDigests] = useState<Digest[]>([]);
  const [activeDigest, setActiveDigest] = useState<Digest | null>(null);
  const [status, setStatus] = useState("Loading weekly digests...");
  const [needsLogin, setNeedsLogin] = useState(false);
  const [digestUnavailable, setDigestUnavailable] = useState(false);
  const [busyAction, setBusyAction] = useState<"generate" | "export" | "obsidian" | null>(null);

  async function loadDigests() {
    const result = await apiFetch<Digest[]>("/workspace/digests");
    setDigests(result);
    setActiveDigest((current) => result.find((item) => item.id === current?.id) || result[0] || null);
    setStatus(result.length ? "" : "No digests yet. Generate one to create a project summary for the current period.");
  }

  useEffect(() => {
    loadDigests().catch((error) => {
      if (isApiError(error) && error.status === 401) {
        setNeedsLogin(true);
        setStatus("");
        return;
      }
      if (isApiError(error) && error.status === 404) {
        setDigestUnavailable(true);
        setStatus("");
        return;
      }
      setStatus(getApiErrorMessage(error, "Failed to load digests"));
    });
  }, []);

  async function generateDigest() {
    setBusyAction("generate");
    setStatus("Generating weekly digest...");
    try {
      const digest = await apiFetch<Digest>("/workspace/digests/generate?days=7", { method: "POST" });
      await loadDigests();
      setActiveDigest(digest);
      setStatus("Weekly digest generated.");
      showToast({ tone: "success", title: "Digest generated", message: "Your weekly research brief is ready." });
    } catch (error) {
      const message = getApiErrorMessage(error, "Failed to generate digest");
      setStatus(message);
      showToast({ tone: "error", title: "Could not generate digest", message });
    } finally {
      setBusyAction(null);
    }
  }

  async function exportDigest() {
    if (!activeDigest) return;
    setBusyAction("export");
    try {
      const result = await apiFetch<DigestDeliveryResult>(`/workspace/digests/${activeDigest.id}/deliver`, {
        method: "POST",
        body: JSON.stringify({ target: "download_markdown" }),
      });
      await loadDigests();
      const markdown = result.payload?.content || activeDigest.markdown;
      const filename = result.payload?.filename || `weekly-digest-${activeDigest.id}.md`;
      const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
      showToast({ tone: "success", title: "Digest exported", message: "A markdown copy was downloaded to your machine." });
    } catch (error) {
      const message = getApiErrorMessage(error, "Failed to export digest");
      setStatus(message);
      showToast({ tone: "error", title: "Could not export digest", message });
    } finally {
      setBusyAction(null);
    }
  }

  async function exportObsidianMarkdown() {
    if (!activeDigest) return;
    setBusyAction("obsidian");
    setStatus("Writing Obsidian-ready digest export...");
    try {
      const result = await apiFetch<DigestDeliveryResult>(`/workspace/digests/${activeDigest.id}/deliver`, {
        method: "POST",
        body: JSON.stringify({ target: "obsidian_file" }),
      });
      await loadDigests();
      const vaultPath = result.payload?.vault_relative_path;
      const absolutePath = typeof result.payload?.absolute_path === "string" ? result.payload.absolute_path : null;
      setStatus(result.message || "Obsidian-ready markdown export prepared.");
      showToast({
        tone: "success",
        title: "Obsidian export written",
        message: absolutePath || vaultPath ? `Saved digest to ${absolutePath || vaultPath}.` : "Saved an Obsidian-ready digest markdown file.",
      });
    } catch (error) {
      const message = getApiErrorMessage(error, "Failed to deliver digest");
      setStatus(message);
      showToast({ tone: "error", title: "Could not write Obsidian export", message });
    } finally {
      setBusyAction(null);
    }
  }

  if (needsLogin) {
    return (
      <div className="card">
        <p className="text-xs font-medium uppercase tracking-[0.24em] text-stone-500">Weekly research brief</p>
        <h1 className="mt-2 text-4xl font-semibold">Research digests</h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
          Sign in to generate digests, inspect recent summaries, and jump into the projects that need attention.
        </p>
        <div className="mt-5 flex gap-3">
          <Link href="/login" className="btn-primary">Login</Link>
          <Link href="/" className="btn-secondary">Back to dashboard</Link>
        </div>
      </div>
    );
  }

  if (digestUnavailable) {
    return (
      <div className="card">
        <p className="text-xs font-medium uppercase tracking-[0.24em] text-stone-500">Weekly research brief</p>
        <h1 className="mt-2 text-4xl font-semibold">Digest routes are not available in this backend session.</h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
          If you recently updated the codebase, restart the backend so the workspace digest routes are registered. You can still continue from your projects in the meantime.
        </p>
        <div className="mt-5 flex gap-3">
          <Link href="/projects" className="btn-primary">Open projects</Link>
          <Link href="/" className="btn-secondary">Back to dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.24em] text-stone-500">Weekly research brief</p>
            <h1 className="mt-2 text-4xl font-semibold">Research digests</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
              Generate a period summary, inspect project-level changes, and move directly into the projects that need attention next.
            </p>
          </div>
          <div className="flex gap-2">
            <button className="btn-primary" disabled={busyAction === "generate"} onClick={() => void generateDigest()} type="button">
              {busyAction === "generate" ? <LoadingSpinner /> : null}
              {busyAction === "generate" ? "Generating..." : "Generate latest digest"}
            </button>
            <button className="btn-secondary" onClick={() => void exportDigest()} type="button" disabled={!activeDigest || busyAction === "export"}>
              {busyAction === "export" ? <LoadingSpinner /> : null}
              {busyAction === "export" ? "Exporting..." : "Export markdown"}
            </button>
            <button className="btn-secondary" onClick={() => void exportObsidianMarkdown()} type="button" disabled={!activeDigest || busyAction === "obsidian"}>
              {busyAction === "obsidian" ? <LoadingSpinner /> : null}
              {busyAction === "obsidian" ? "Preparing..." : "Export for Obsidian"}
            </button>
          </div>
        </div>
        {status ? <p className="mt-4 text-sm text-slate-500">{status}</p> : null}
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="card">
          <h2 className="text-2xl font-semibold">Recent digests</h2>
          <div className="mt-4 space-y-3">
            {digests.length === 0 ? <p className="text-sm text-slate-500">No digests yet. Generate one to create a project summary.</p> : null}
            {digests.map((digest) => (
              <button
                key={digest.id}
                className={`w-full rounded-2xl border p-4 text-left transition ${activeDigest?.id === digest.id ? "border-stone-900 bg-stone-100" : "border-stone-200 bg-stone-50/70 hover:border-stone-300"}`}
                onClick={() => setActiveDigest(digest)}
                type="button"
              >
                <p className="font-medium text-slate-800">{new Date(digest.generated_at).toLocaleString()}</p>
                <p className="mt-2 text-xs text-slate-500">
                  {new Date(digest.period_start).toLocaleDateString()} - {new Date(digest.period_end).toLocaleDateString()}
                </p>
              </button>
            ))}
          </div>
        </section>

        <section className="card">
          {!activeDigest ? (
            <p className="text-sm text-slate-500">Pick a digest to inspect its project-level summary and next actions.</p>
          ) : (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-semibold">Digest overview</h2>
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {[
                    ["Projects updated", activeDigest.summary.projects_updated ?? 0],
                    ["New papers found", activeDigest.summary.new_papers_found ?? 0],
                    ["Papers added", activeDigest.summary.papers_added ?? 0],
                    ["New evidence", activeDigest.summary.new_evidence_cards ?? 0],
                    ["Pending suggestions", activeDigest.summary.pending_update_suggestions ?? 0],
                    ["Locked attention", activeDigest.summary.locked_sections_awaiting_review ?? 0],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-2xl bg-stone-50 p-4">
                      <p className="text-xs uppercase tracking-wide text-stone-500">{label}</p>
                      <p className="mt-2 text-2xl font-semibold">{value}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 rounded-2xl bg-stone-50 p-4 text-sm text-slate-600">
                  <p>
                    Delivery status: <span className="font-medium text-slate-800">{activeDigest.delivery_status || "pending"}</span>
                  </p>
                  <p className="mt-1">
                    Target: <span className="font-medium text-slate-800">{activeDigest.delivery_target || "not set"}</span>
                  </p>
                  {activeDigest.delivery_target === "obsidian_placeholder" ? (
                    <p className="mt-1">Latest Obsidian export prepared a markdown file with frontmatter and a suggested vault-relative path.</p>
                  ) : null}
                  {activeDigest.delivery_target === "obsidian_file" ? (
                    <p className="mt-1">Latest Obsidian export wrote a markdown file into the configured vault root on the backend host.</p>
                  ) : null}
                  {activeDigest.delivery_message ? <p className="mt-1">{activeDigest.delivery_message}</p> : null}
                  {activeDigest.delivered_at ? (
                    <p className="mt-1">Last delivery update: {new Date(activeDigest.delivered_at).toLocaleString()}</p>
                  ) : null}
                </div>
              </div>

              <div>
                <h3 className="text-xl font-semibold">Projects in this digest</h3>
                <div className="mt-4 space-y-3">
                  {activeDigest.summary.projects?.length ? null : (
                    <p className="text-sm text-slate-500">No project activity in this digest window.</p>
                  )}
                  {activeDigest.summary.projects?.map((project) => (
                    <div key={project.project_id} className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-medium text-slate-800">{project.project_title}</p>
                          <p className="mt-2 text-xs text-slate-500">
                            {project.freshness_status} • {project.pending_review_count} pending • {project.locked_attention_count} locked attention
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Link className="btn-secondary" href={`/projects/${project.project_id}`}>Open project</Link>
                          <Link className="btn-secondary" href={`/projects/${project.project_id}/note`}>Open note</Link>
                          <Link className="btn-secondary" href={`/projects/${project.project_id}/history`}>Review updates</Link>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-xl font-semibold">Markdown brief</h3>
                <pre className="mt-4 max-h-[420px] overflow-auto rounded-2xl bg-stone-50 p-4 text-sm leading-7 text-slate-700">
                  {activeDigest.markdown}
                </pre>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
