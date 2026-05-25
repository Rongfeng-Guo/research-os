"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch, getApiErrorMessage, isApiError } from "@/lib/api";
import { dismissProjectTour, isProjectTourDismissed, setLastProjectId } from "@/lib/local-state";
import { useToast } from "@/components/ToastProvider";
import LoadingSpinner from "@/components/LoadingSpinner";
import ProjectOnboarding from "@/components/ProjectOnboarding";
import PaperSearchPanel from "@/components/PaperSearchPanel";
import EvidenceList, { EvidenceCard } from "@/components/EvidenceList";
import NotePanel, { NoteSection } from "@/components/NotePanel";
import PapersPanel from "@/components/PapersPanel";
import UploadSourceForm from "@/components/UploadSourceForm";
import UpdateHistoryPanel from "@/components/UpdateHistoryPanel";
import SuggestionPanel from "@/components/SuggestionPanel";
import type { ProjectPaper } from "@/lib/papers";

type UpdateRun = {
  id: number;
  status: string;
  run_type: string;
  trigger_type: string;
  provider: string;
  summary: string;
  error_message: string;
  current_step: string;
  progress_message: string;
  total_steps: number;
  completed_steps: number;
  created_at: string;
  started_at: string;
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
  current_text: string;
  proposed_text: string;
  rationale: string;
  supporting_evidence_ids?: number[];
  supporting_sources: string[];
  diff?: { blocks?: Array<{ kind: string; before: string; after: string }>; summary?: Record<string, number> };
  status: string;
  created_at: string;
  applied_at?: string | null;
  applied_by?: string;
};

type NoteVersion = {
  id: number;
  version_number: number;
  created_at: string;
  version_kind: string;
  source_suggestion_ids?: number[];
  update_run_id?: number | null;
  metadata?: { generation_mode?: string; source_count?: number; evidence_count?: number };
};

type TopicNote = {
  markdown: string;
  sections: NoteSection[];
  updated_at: string;
  metadata: {
    source_count?: number;
    evidence_count?: number;
    provider_used?: string;
    generation_mode?: string;
    blocked_locked_suggestion_count?: number;
  };
};

type ProjectDetail = {
  project: {
    id: number;
    title: string;
    topic: string;
    description: string;
    auto_refresh_enabled?: boolean;
    refresh_cadence?: string;
    digest_enabled?: boolean;
    last_refreshed_at?: string | null;
    next_refresh_due_at?: string | null;
    updated_at: string;
  };
  health?: {
    freshness_status: string;
    freshness_reason: string;
    pending_review_count: number;
    locked_attention_count: number;
    stale_note: boolean;
    last_activity_at?: string | null;
    evidence_growth_week: number;
    note_version_count: number;
    latest_note_update_at?: string | null;
  } | null;
  papers: ProjectPaper[];
  evidence_cards: EvidenceCard[];
  topic_note?: TopicNote | null;
  update_runs: UpdateRun[];
  note_update_suggestions: Suggestion[];
  note_versions: NoteVersion[];
};

const generationModes = [
  { value: "accepted_only", label: "Accepted only" },
  { value: "all_non_rejected", label: "All non-rejected" },
  { value: "accepted_plus_pinned_priority", label: "Accepted + pinned priority" },
  { value: "pinned_only", label: "Pinned only" },
];

function ActionButton({
  label,
  loadingLabel,
  busy,
  onClick,
  tone = "secondary",
}: {
  label: string;
  loadingLabel: string;
  busy: boolean;
  onClick: () => void | Promise<void>;
  tone?: "primary" | "secondary";
}) {
  return (
    <button className={tone === "primary" ? "btn-primary" : "btn-secondary"} disabled={busy} onClick={() => void onClick()} type="button">
      {busy ? <LoadingSpinner /> : null}
      {busy ? loadingLabel : label}
    </button>
  );
}

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const projectId = Number(params.id);
  const searchParams = useSearchParams();
  const { showToast } = useToast();

  const [data, setData] = useState<ProjectDetail | null>(null);
  const [status, setStatus] = useState<string>("Loading project workspace...");
  const [generationMode, setGenerationMode] = useState("accepted_only");
  const [refreshCadence, setRefreshCadence] = useState("manual_only");
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);
  const [digestEnabled, setDigestEnabled] = useState(true);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [activeRun, setActiveRun] = useState<UpdateRun | null>(null);

  async function refresh(showStatus = true) {
    if (showStatus) {
      setStatus((previous) => previous || "Loading project workspace...");
    }
    const res = await apiFetch<ProjectDetail>(`/projects/${projectId}`);
    setData(res);
    setGenerationMode(res.topic_note?.metadata?.generation_mode || "accepted_only");
    setRefreshCadence(res.project.refresh_cadence || "manual_only");
    setAutoRefreshEnabled(Boolean(res.project.auto_refresh_enabled));
    setDigestEnabled(res.project.digest_enabled ?? true);
    setLastProjectId(projectId);
    setStatus("");
  }

  useEffect(() => {
    refresh().catch((error) => {
      if (isApiError(error) && error.status === 401) {
        setNeedsLogin(true);
        setStatus("");
        return;
      }
      setStatus(getApiErrorMessage(error, "Failed to load project"));
    });
  }, [projectId]);

  useEffect(() => {
    if (!data) return;
    const shouldShowWelcome =
      searchParams?.get("welcome") === "1" ||
      (!isProjectTourDismissed() && data.papers.length === 0 && data.evidence_cards.length === 0 && !data.topic_note);
    setShowOnboarding(shouldShowWelcome);
  }, [data, searchParams]);

  function updateProjectData(updater: (current: ProjectDetail) => ProjectDetail) {
    setData((current) => (current ? updater(current) : current));
  }

  async function runAction(
    key: string,
    message: string,
    action: () => Promise<void>,
    successTitle: string,
    successMessage?: string,
  ) {
    setBusyAction(key);
    setStatus(message);
    try {
      await action();
      await refresh(false);
      setStatus(successMessage || "");
      showToast({ tone: "success", title: successTitle, message: successMessage });
    } catch (error) {
      const errorMessage = getApiErrorMessage(error, "Request failed");
      setStatus(errorMessage);
      showToast({ tone: "error", title: "Something went wrong", message: errorMessage });
    } finally {
      setBusyAction(null);
    }
  }

  async function pollRunUntilFinished(run: UpdateRun, actionKey: string) {
    setActiveRun(run);
    setBusyAction(actionKey);
    setStatus(run.progress_message || run.summary || "Job started");
    try {
      let currentRun = run;
      while (currentRun.status === "running" || currentRun.status === "pending") {
        await new Promise((resolve) => window.setTimeout(resolve, 1200));
        currentRun = await apiFetch<UpdateRun>(`/projects/${projectId}/runs/${currentRun.id}`);
        setActiveRun(currentRun);
        setStatus(
          [
            currentRun.summary,
            currentRun.current_step ? `Step: ${currentRun.current_step}` : "",
            currentRun.progress_message,
            currentRun.total_steps > 0 ? `${currentRun.completed_steps}/${currentRun.total_steps} steps` : "",
          ]
            .filter(Boolean)
            .join(" • "),
        );
      }
      await refresh(false);
      if (currentRun.status === "failed") {
        throw new Error(currentRun.error_message || currentRun.summary || "Run failed");
      }
      const successTitle = currentRun.run_type === "extraction" ? "Evidence extraction finished" : "Topic refresh finished";
      const successMessage =
        currentRun.run_type === "extraction"
          ? `Created ${currentRun.evidence_created} evidence cards.`
          : `Added ${currentRun.papers_added} papers and generated ${currentRun.affected_sections_count} updated sections.`;
      setStatus(currentRun.summary || successMessage);
      showToast({ tone: "success", title: successTitle, message: successMessage });
    } catch (error) {
      const errorMessage = getApiErrorMessage(error, "Run failed");
      setStatus(errorMessage);
      showToast({ tone: "error", title: "Something went wrong", message: errorMessage });
    } finally {
      setBusyAction(null);
      setActiveRun(null);
    }
  }

  async function runExtraction() {
    setBusyAction("extract");
    setStatus("Starting extraction job...");
    try {
      const run = await apiFetch<UpdateRun>(`/papers/projects/${projectId}/extract/start`, { method: "POST" });
      await pollRunUntilFinished(run, "extract");
    } catch (error) {
      const errorMessage = getApiErrorMessage(error, "Failed to start extraction");
      setBusyAction(null);
      setStatus(errorMessage);
      showToast({ tone: "error", title: "Could not start extraction", message: errorMessage });
    }
  }

  async function generateNote() {
    await runAction(
      "generate-note",
      "Generating topic note from your current evidence...",
      () => apiFetch(`/notes/projects/${projectId}/generate?generation_mode=${generationMode}`, { method: "POST" }).then(() => undefined),
      "Topic note updated",
      "The note was regenerated with the selected evidence mode.",
    );
  }

  async function refreshTopic() {
    setBusyAction("refresh-topic");
    setStatus("Starting refresh job...");
    try {
      const run = await apiFetch<UpdateRun>(`/projects/${projectId}/refresh/start`, { method: "POST" });
      await pollRunUntilFinished(run, "refresh-topic");
    } catch (error) {
      const errorMessage = getApiErrorMessage(error, "Failed to start refresh");
      setBusyAction(null);
      setStatus(errorMessage);
      showToast({ tone: "error", title: "Could not start refresh", message: errorMessage });
    }
  }

  async function applyAcceptedSuggestions() {
    await runAction(
      "apply-accepted",
      "Applying accepted suggestions to the note...",
      () =>
        apiFetch(`/notes/projects/${projectId}/apply-suggestions`, {
          method: "POST",
          body: JSON.stringify({ generation_mode: generationMode }),
        }).then(() => undefined),
      "Accepted suggestions applied",
      "The note was updated and a new version was saved.",
    );
  }

  async function applySelectedSuggestions(suggestionIds: number[]) {
    if (!suggestionIds.length) {
      return;
    }
    await runAction(
      "apply-selected",
      "Applying selected suggestions to the note...",
      () =>
        apiFetch(`/notes/projects/${projectId}/apply-suggestions`, {
          method: "POST",
          body: JSON.stringify({ generation_mode: generationMode, suggestion_ids: suggestionIds }),
        }).then(() => undefined),
      "Selected suggestions applied",
      "Only the chosen suggestions were merged into the note.",
    );
  }

  async function applySuggestion(suggestionId: number) {
    await runAction(
      `apply-suggestion-${suggestionId}`,
      "Applying this suggestion...",
      () =>
        apiFetch(`/notes/suggestions/${suggestionId}/apply`, {
          method: "POST",
          body: JSON.stringify({ generation_mode: generationMode }),
        }).then(() => undefined),
      "Suggestion applied",
      "A new note version was created from the selected suggestion.",
    );
  }

  async function applySectionSuggestions(sectionSlug: string, suggestionIds: number[] = []) {
    await runAction(
      `apply-section-${sectionSlug}`,
      suggestionIds.length ? `Applying selected suggestions for ${sectionSlug}...` : `Applying accepted suggestions for ${sectionSlug}...`,
      () =>
        apiFetch(`/notes/projects/${projectId}/sections/${sectionSlug}/apply-suggestions`, {
          method: "POST",
          body: JSON.stringify({ generation_mode: generationMode, suggestion_ids: suggestionIds }),
        }).then(() => undefined),
      suggestionIds.length ? "Selected section suggestions applied" : "Section suggestions applied",
      suggestionIds.length ? "Only the chosen suggestions for this section were merged into the note." : "Accepted suggestions for this section were merged into the note.",
    );
  }

  async function updateReviewStatus(cardId: number, reviewStatus: string) {
    try {
      const updatedCard = await apiFetch<EvidenceCard>(`/evidence/${cardId}`, {
        method: "PATCH",
        body: JSON.stringify({ review_status: reviewStatus }),
      });
      updateProjectData((current) => ({
        ...current,
        evidence_cards: current.evidence_cards.map((card) => (card.id === cardId ? updatedCard : card)),
      }));
    } catch (error) {
      throw error;
    }
  }

  async function saveEvidenceCard(cardId: number, payload: Partial<EvidenceCard>) {
    try {
      const updatedCard = await apiFetch<EvidenceCard>(`/evidence/${cardId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      updateProjectData((current) => ({
        ...current,
        evidence_cards: current.evidence_cards.map((card) => (card.id === cardId ? updatedCard : card)),
      }));
    } catch (error) {
      throw error;
    }
  }

  async function updateSuggestionStatus(suggestionId: number, suggestionStatus: string) {
    try {
      const updatedSuggestion = await apiFetch<Suggestion>(`/notes/suggestions/${suggestionId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: suggestionStatus }),
      });
      updateProjectData((current) => ({
        ...current,
        note_update_suggestions: current.note_update_suggestions.map((suggestion) =>
          suggestion.id === suggestionId ? updatedSuggestion : suggestion,
        ),
      }));
      showToast({ tone: "success", title: "Suggestion updated", message: `Suggestion marked as ${suggestionStatus}.` });
    } catch (error) {
      showToast({ tone: "error", title: "Could not update suggestion", message: getApiErrorMessage(error, "Failed to update suggestion") });
      throw error;
    }
  }

  async function saveSection(slug: string, content: string) {
    try {
      const updatedNote = await apiFetch<TopicNote>(`/notes/projects/${projectId}/sections/${slug}`, {
        method: "PATCH",
        body: JSON.stringify({ content }),
      });
      updateProjectData((current) => ({ ...current, topic_note: updatedNote }));
      showToast({ tone: "success", title: "Section saved", message: "Your manual note edit was saved." });
    } catch (error) {
      showToast({ tone: "error", title: "Could not save section", message: getApiErrorMessage(error, "Failed to save section") });
      throw error;
    }
  }

  async function toggleSectionLock(slug: string, isLocked: boolean) {
    try {
      const updatedNote = await apiFetch<TopicNote>(`/notes/projects/${projectId}/sections/${slug}`, {
        method: "PATCH",
        body: JSON.stringify({
          is_locked: isLocked,
          lock_reason: isLocked ? "Locked from project workspace" : "",
        }),
      });
      updateProjectData((current) => ({ ...current, topic_note: updatedNote }));
      showToast({
        tone: "success",
        title: isLocked ? "Section locked" : "Section unlocked",
        message: isLocked ? "Future automation will only suggest changes for this section." : "This section can now be updated through suggestions.",
      });
    } catch (error) {
      showToast({ tone: "error", title: "Could not update section lock", message: getApiErrorMessage(error, "Failed to update lock") });
      throw error;
    }
  }

  async function exportProjectSnapshot() {
    setBusyAction("export");
    setStatus("Preparing project snapshot...");
    try {
      const snapshot = await apiFetch<Record<string, unknown>>(`/projects/${projectId}/export`);
      const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `project-${projectId}-snapshot.json`;
      link.click();
      URL.revokeObjectURL(url);
      setStatus("Project snapshot exported.");
      showToast({ tone: "success", title: "Project snapshot exported", message: "A local backup of your project data was downloaded." });
    } catch (error) {
      const message = getApiErrorMessage(error, "Export failed");
      setStatus(message);
      showToast({ tone: "error", title: "Could not export project", message });
    } finally {
      setBusyAction(null);
    }
  }

  async function savePreferences() {
    setBusyAction("save-preferences");
    setStatus("Saving refresh preferences...");
    try {
      const updatedProject = await apiFetch<ProjectDetail["project"]>(`/projects/${projectId}/preferences`, {
        method: "PATCH",
        body: JSON.stringify({
          refresh_cadence: refreshCadence,
          auto_refresh_enabled: autoRefreshEnabled,
          digest_enabled: digestEnabled,
        }),
      });
      updateProjectData((current) => ({ ...current, project: updatedProject }));
      setStatus("Refresh preferences saved.");
      showToast({ tone: "success", title: "Preferences saved", message: "Refresh cadence and digest settings were updated." });
    } catch (error) {
      const message = getApiErrorMessage(error, "Failed to save preferences");
      setStatus(message);
      showToast({ tone: "error", title: "Could not save preferences", message });
    } finally {
      setBusyAction(null);
    }
  }

  const derived = useMemo(() => {
    if (!data) return null;
    const acceptedEvidence = data.evidence_cards.filter((card) => card.review_status === "accepted").length;
    const pinnedEvidence = data.evidence_cards.filter((card) => card.is_pinned).length;
    const pendingSuggestions = data.note_update_suggestions.filter((item) => item.status === "suggested").length;
    const acceptedSuggestions = data.note_update_suggestions.filter((item) => item.status === "accepted").length;
    const lockedSections = data.topic_note?.sections.filter((section) => section.is_locked).length || 0;
    const noteStatus = !data.topic_note
      ? "No note yet"
      : new Date(data.topic_note.updated_at).getTime() < new Date(data.project.updated_at).getTime()
        ? "Needs refresh"
        : "Current";
    const isEmptyProject = data.papers.length === 0 && data.evidence_cards.length === 0 && !data.topic_note;
    return { acceptedEvidence, pinnedEvidence, pendingSuggestions, acceptedSuggestions, lockedSections, noteStatus, isEmptyProject };
  }, [data]);

  if (needsLogin) {
    return (
      <div className="card">
        <p className="text-xs font-medium uppercase tracking-[0.24em] text-stone-500">Project workspace</p>
        <h1 className="mt-2 text-4xl font-semibold">Please log in to open this project</h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
          Your token is missing or expired. Log in again and then reopen the project workspace.
        </p>
        <div className="mt-5 flex gap-3">
          <Link className="btn-primary" href="/login">Login</Link>
          <Link className="btn-secondary" href="/projects">Project library</Link>
        </div>
      </div>
    );
  }

  if (!data || !derived) {
    return <div className="card text-slate-600">{status || "Loading project..."}</div>;
  }

  return (
    <div className="space-y-6">
      {showOnboarding ? (
        <ProjectOnboarding
          projectId={projectId}
          onDismiss={() => {
            dismissProjectTour();
            setShowOnboarding(false);
          }}
        />
      ) : null}

      <section className="card">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-medium uppercase tracking-[0.24em] text-stone-500">Project workspace</p>
            <h1 className="mt-2 text-4xl font-semibold">{data.project.title}</h1>
            <p className="mt-4 text-sm leading-7 text-slate-700">{data.project.topic}</p>
            <p className="mt-3 text-sm text-slate-500">{data.project.description || "No project description yet."}</p>
            <div className="mt-5 flex flex-wrap gap-2 text-xs">
              <span className="rounded-full bg-stone-100 px-3 py-1 text-stone-700">{data.papers.length} sources</span>
              <span className="rounded-full bg-stone-100 px-3 py-1 text-stone-700">{data.evidence_cards.length} evidence cards</span>
              <span className="rounded-full bg-stone-100 px-3 py-1 text-stone-700">{derived.acceptedEvidence} accepted evidence</span>
              <span className="rounded-full bg-stone-100 px-3 py-1 text-stone-700">{derived.pinnedEvidence} pinned evidence</span>
              <span className="rounded-full bg-stone-100 px-3 py-1 text-stone-700">{derived.pendingSuggestions} pending suggestions</span>
              <span className="rounded-full bg-stone-100 px-3 py-1 text-stone-700">{derived.acceptedSuggestions} accepted suggestions</span>
              <span className="rounded-full bg-stone-100 px-3 py-1 text-stone-700">{derived.lockedSections} locked sections</span>
              <span className="rounded-full bg-stone-100 px-3 py-1 text-stone-700">Note: {derived.noteStatus}</span>
              {data.health ? <span className="rounded-full bg-stone-100 px-3 py-1 text-stone-700">Freshness: {data.health.freshness_status}</span> : null}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="btn-secondary" href={`/projects/${projectId}/evidence`}>Evidence</Link>
            <Link className="btn-secondary" href={`/projects/${projectId}/note`}>Read note</Link>
            <Link className="btn-secondary" href={`/projects/${projectId}/history`}>History</Link>
            <Link className="btn-secondary" href={`/papers?project_id=${projectId}`}>Paper workspace</Link>
            <ActionButton label="Export snapshot" loadingLabel="Exporting..." busy={busyAction === "export"} onClick={exportProjectSnapshot} />
            <ActionButton label="Refresh topic" loadingLabel="Refreshing..." busy={busyAction === "refresh-topic"} onClick={refreshTopic} />
            <ActionButton label="Run extraction" loadingLabel="Extracting..." busy={busyAction === "extract"} onClick={runExtraction} />
            <ActionButton label="Update note" loadingLabel="Generating..." busy={busyAction === "generate-note"} onClick={generateNote} tone="primary" />
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label className="text-sm text-slate-600">Generation mode</label>
          <select className="input w-auto min-w-[240px]" value={generationMode} onChange={(e) => setGenerationMode(e.target.value)}>
            {generationModes.map((mode) => (
              <option key={mode.value} value={mode.value}>{mode.label}</option>
            ))}
          </select>
          {busyAction ? (
            <span className="inline-flex items-center gap-2 rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-700">
              <LoadingSpinner className="h-3.5 w-3.5" />
              Working
            </span>
          ) : null}
        </div>
        {status ? <p className="mt-4 text-sm text-slate-500">{status}</p> : null}
        {activeRun ? (
          <div className="mt-4 rounded-2xl bg-stone-50 p-4">
            <div className="flex flex-wrap items-center gap-2 text-xs text-stone-700">
              <span className="rounded-full bg-white px-2 py-1">{activeRun.run_type.replaceAll("_", " ")}</span>
              <span className="rounded-full bg-white px-2 py-1">{activeRun.status}</span>
              {activeRun.current_step ? <span className="rounded-full bg-white px-2 py-1">{activeRun.current_step}</span> : null}
            </div>
            {activeRun.total_steps > 0 ? (
              <>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-stone-200">
                  <div
                    className="h-full rounded-full bg-stone-700 transition-all"
                    style={{ width: `${Math.min(100, Math.round((activeRun.completed_steps / activeRun.total_steps) * 100))}%` }}
                  />
                </div>
                <p className="mt-2 text-xs text-slate-500">{activeRun.completed_steps}/{activeRun.total_steps} steps</p>
              </>
            ) : null}
          </div>
        ) : null}
      </section>

      {derived.isEmptyProject ? (
        <section className="card">
          <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">Start here</p>
          <h2 className="mt-2 text-2xl font-semibold">This project is empty. Add one source and the rest of the workflow will unlock.</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl bg-stone-50 p-4 text-sm text-slate-700">1. Search for a paper or upload source text.</div>
            <div className="rounded-2xl bg-stone-50 p-4 text-sm text-slate-700">2. Run extraction to create your first evidence cards.</div>
            <div className="rounded-2xl bg-stone-50 p-4 text-sm text-slate-700">3. Generate a note and then refine sections manually.</div>
          </div>
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="card">
          <h2 className="text-xl font-semibold">Status summary</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl bg-stone-50 p-4">
              <p className="text-xs uppercase tracking-wide text-stone-500">Last refresh</p>
              <p className="mt-2 text-sm text-slate-700">{data.project.last_refreshed_at ? new Date(data.project.last_refreshed_at).toLocaleString() : "No refresh yet"}</p>
            </div>
            <div className="rounded-2xl bg-stone-50 p-4">
              <p className="text-xs uppercase tracking-wide text-stone-500">Next refresh due</p>
              <p className="mt-2 text-sm text-slate-700">{data.project.next_refresh_due_at ? new Date(data.project.next_refresh_due_at).toLocaleString() : "Manual only"}</p>
            </div>
            <div className="rounded-2xl bg-stone-50 p-4">
              <p className="text-xs uppercase tracking-wide text-stone-500">Freshness</p>
              <p className="mt-2 text-sm text-slate-700">{data.health?.freshness_reason || "No health signal yet"}</p>
            </div>
            <div className="rounded-2xl bg-stone-50 p-4">
              <p className="text-xs uppercase tracking-wide text-stone-500">Latest note update</p>
              <p className="mt-2 text-sm text-slate-700">{data.health?.latest_note_update_at ? new Date(data.health.latest_note_update_at).toLocaleString() : "No note yet"}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">Refresh preferences</h2>
              <p className="text-sm text-slate-600">Manual-first now, but ready for future scheduled refreshes and digest generation.</p>
            </div>
            <ActionButton label="Save preferences" loadingLabel="Saving..." busy={busyAction === "save-preferences"} onClick={savePreferences} />
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <label className="rounded-2xl bg-stone-50 p-4 text-sm text-slate-700">
              <span className="mb-2 block text-xs uppercase tracking-wide text-stone-500">Cadence</span>
              <select className="input" value={refreshCadence} onChange={(e) => setRefreshCadence(e.target.value)}>
                <option value="manual_only">manual_only</option>
                <option value="daily">daily</option>
                <option value="weekly">weekly</option>
                <option value="custom">custom</option>
              </select>
            </label>
            <label className="rounded-2xl bg-stone-50 p-4 text-sm text-slate-700">
              <span className="mb-2 block text-xs uppercase tracking-wide text-stone-500">Auto refresh</span>
              <input checked={autoRefreshEnabled} onChange={(e) => setAutoRefreshEnabled(e.target.checked)} type="checkbox" />
            </label>
            <label className="rounded-2xl bg-stone-50 p-4 text-sm text-slate-700">
              <span className="mb-2 block text-xs uppercase tracking-wide text-stone-500">Weekly digest</span>
              <input checked={digestEnabled} onChange={(e) => setDigestEnabled(e.target.checked)} type="checkbox" />
            </label>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <PaperSearchPanel onPaperAdded={() => refresh(false)} projectId={projectId} />
        <UploadSourceForm onUploaded={() => refresh(false)} projectId={projectId} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <PapersPanel papers={data.papers} projectId={projectId} />
        <UpdateHistoryPanel runs={data.update_runs} />
      </div>

      <SuggestionPanel
        suggestions={data.note_update_suggestions}
        onStatusChange={updateSuggestionStatus}
        onApplyAccepted={applyAcceptedSuggestions}
        onApplySelected={applySelectedSuggestions}
        onApplySuggestion={applySuggestion}
        onApplySection={applySectionSuggestions}
      />

      <EvidenceList cards={data.evidence_cards} onReviewStatusChange={updateReviewStatus} onSaveCard={saveEvidenceCard} />
      <NotePanel
        markdown={data.topic_note?.markdown || undefined}
        metadata={data.topic_note?.metadata}
        sections={data.topic_note?.sections}
        editable
        onSaveSection={saveSection}
        onToggleLock={toggleSectionLock}
      />

      <section className="card">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Note versions</h2>
            <p className="text-sm text-slate-600">Every refresh, apply flow, and manual section edit can leave behind a note snapshot.</p>
          </div>
          <Link className="btn-secondary" href={`/projects/${projectId}/history`}>Open history</Link>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {data.note_versions.length === 0 ? <p className="text-sm text-slate-500">No versions yet.</p> : null}
          {data.note_versions.slice(0, 6).map((version) => (
            <span key={version.id} className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-700">
              {`v${version.version_number} • ${version.version_kind} • ${new Date(version.created_at).toLocaleDateString()}`}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}
