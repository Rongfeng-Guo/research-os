"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import NotePanel, { NoteSection } from "@/components/NotePanel";
import { apiFetch, apiFetchOrNull, getApiErrorMessage, isApiError } from "@/lib/api";
import { setLastProjectId } from "@/lib/local-state";
import { useToast } from "@/components/ToastProvider";

type TopicNote = {
  markdown: string;
  title: string;
  sections: NoteSection[];
  metadata?: {
    generated_at?: string;
    provider_used?: string;
    source_count?: number;
    evidence_count?: number;
    generation_mode?: string;
    blocked_locked_suggestion_count?: number;
  };
};

export default function NotePage({ params }: { params: { id: string } }) {
  const projectId = Number(params.id);
  const { showToast } = useToast();
  const [note, setNote] = useState<TopicNote | null>(null);
  const [status, setStatus] = useState("Loading note...");
  const [needsGeneration, setNeedsGeneration] = useState(false);

  async function loadNote() {
    const data = await apiFetchOrNull<TopicNote>(`/notes/projects/${projectId}`);
    setLastProjectId(projectId);
    setNote(data);
    setNeedsGeneration(!data);
    setStatus(data ? "" : "No topic note yet. Generate one from evidence when you are ready.");
  }

  useEffect(() => {
    loadNote().catch((error) => {
      if (isApiError(error) && error.status === 401) {
        setStatus("Please log in again to load this note.");
        return;
      }
      setStatus(getApiErrorMessage(error, "Failed to load note"));
    });
  }, [projectId]);

  async function saveSection(slug: string, content: string) {
    setStatus("Saving section...");
    try {
      await apiFetch(`/notes/projects/${projectId}/sections/${slug}`, {
        method: "PATCH",
        body: JSON.stringify({ content }),
      });
      await loadNote();
      setStatus("Section updated.");
      showToast({ tone: "success", title: "Section updated", message: "Your note section was saved." });
    } catch (error) {
      const message = getApiErrorMessage(error, "Failed to save section");
      setStatus(message);
      showToast({ tone: "error", title: "Could not save section", message });
    }
  }

  async function toggleLock(slug: string, isLocked: boolean) {
    setStatus(isLocked ? "Locking section..." : "Unlocking section...");
    try {
      await apiFetch(`/notes/projects/${projectId}/sections/${slug}`, {
        method: "PATCH",
        body: JSON.stringify({ is_locked: isLocked, lock_reason: isLocked ? "Locked from note page" : "" }),
      });
      await loadNote();
      setStatus(isLocked ? "Section locked." : "Section unlocked.");
      showToast({
        tone: "success",
        title: isLocked ? "Section locked" : "Section unlocked",
        message: isLocked ? "Future updates will stay review-only for this section." : "This section can be updated again.",
      });
    } catch (error) {
      const message = getApiErrorMessage(error, "Failed to update lock");
      setStatus(message);
      showToast({ tone: "error", title: "Could not update section lock", message });
    }
  }

  return (
    <div className="space-y-6">
      <section className="card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <p className="text-xs font-medium uppercase tracking-[0.24em] text-stone-500">Primary reading surface</p>
            <h1 className="mt-2 text-4xl font-semibold">Topic note</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              This is the living note for the project. Review the evidence-backed sections, manually revise where needed, and lock the parts you do not want automated flows to overwrite.
            </p>
          </div>
          <div className="flex gap-2">
            <Link className="btn-secondary" href={`/projects/${projectId}/history`}>History</Link>
            <Link className="btn-secondary" href={`/projects/${projectId}`}>Back to project</Link>
          </div>
        </div>
        {note?.sections?.length ? (
          <div className="mt-5 flex flex-wrap gap-2">
            {note.sections.map((section) => (
              <span
                key={section.slug}
                className={`rounded-full px-3 py-1 text-xs font-medium ${section.is_locked ? "bg-rose-100 text-rose-700" : "bg-stone-100 text-stone-700"}`}
              >
                {section.title}
                {typeof section.evidence_count === "number" ? ` • ${section.evidence_count} evidence` : ""}
              </span>
            ))}
          </div>
        ) : null}
        {status ? <p className="mt-4 text-sm text-slate-500">{status}</p> : null}
        {needsGeneration ? (
          <div className="mt-5 rounded-2xl border border-dashed border-stone-300 bg-stone-50 p-4 text-sm text-slate-600">
            No topic note exists for this project yet. Go back to the project workspace, extract evidence, and generate the first note.
          </div>
        ) : null}
      </section>
      <NotePanel
        markdown={note?.markdown}
        metadata={note?.metadata}
        sections={note?.sections}
        editable
        onSaveSection={saveSection}
        onToggleLock={toggleLock}
      />
    </div>
  );
}
