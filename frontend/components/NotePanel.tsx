"use client";

import { useMemo, useState } from "react";
import { marked } from "marked";
import LoadingSpinner from "@/components/LoadingSpinner";

type NoteMeta = {
  generated_at?: string;
  provider_used?: string;
  source_count?: number;
  evidence_count?: number;
  generation_mode?: string;
  blocked_locked_suggestion_count?: number;
};

export type NoteSection = {
  slug: string;
  title: string;
  content: string;
  evidence_count?: number;
  is_locked?: boolean;
  locked_at?: string | null;
  lock_reason?: string;
  edited_at?: string | null;
  edited_by?: string;
  last_manual_edit_at?: string | null;
};

export default function NotePanel({
  markdown,
  metadata,
  sections,
  editable = false,
  onSaveSection,
  onToggleLock,
}: {
  markdown?: string;
  metadata?: NoteMeta;
  sections?: NoteSection[];
  editable?: boolean;
  onSaveSection?: (slug: string, content: string) => Promise<void> | void;
  onToggleLock?: (slug: string, isLocked: boolean) => Promise<void> | void;
}) {
  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [draftContent, setDraftContent] = useState("");
  const [savingSlug, setSavingSlug] = useState<string | null>(null);
  const [lockingSlug, setLockingSlug] = useState<string | null>(null);
  const renderedSections = useMemo(() => sections || [], [sections]);

  function downloadMarkdown() {
    if (!markdown) return;
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "research-note.md";
    link.click();
    URL.revokeObjectURL(url);
  }

  if (!markdown && renderedSections.length === 0) {
    return (
      <div className="card">
        <h2 className="text-xl font-semibold">Topic note</h2>
        <p className="mt-2 text-sm text-slate-500">No generated note yet. Extract evidence first, then compile the note.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">Living topic note</p>
          <h2 className="mt-2 text-2xl font-semibold">Readable project note</h2>
        </div>
        <button className="btn-secondary" onClick={downloadMarkdown} type="button">
          Export Markdown
        </button>
      </div>
      {metadata ? (
        <div className="mb-6 grid gap-3 rounded-2xl bg-stone-50 p-4 text-sm text-slate-600 md:grid-cols-2 xl:grid-cols-3">
          <p>Provider: {metadata.provider_used || "note compiler"}</p>
          <p>Mode: {metadata.generation_mode || "accepted_only"}</p>
          <p>Sources: {metadata.source_count ?? 0}</p>
          <p>Evidence: {metadata.evidence_count ?? 0}</p>
          {metadata.generated_at ? <p>Generated: {new Date(metadata.generated_at).toLocaleString()}</p> : null}
          {typeof metadata.blocked_locked_suggestion_count === "number" ? <p>Blocked by locks: {metadata.blocked_locked_suggestion_count}</p> : null}
        </div>
      ) : null}
      {renderedSections.length ? (
        <div className="space-y-5">
          {renderedSections.map((section) => {
            const isEditing = editingSlug === section.slug;
            return (
              <section key={section.slug} className={`rounded-2xl border p-4 ${section.is_locked ? "border-rose-300 bg-rose-50/40" : "border-stone-200 bg-white"}`}>
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold">{section.title}</h3>
                      <span className="rounded-full bg-stone-100 px-2 py-1 text-xs text-stone-700">
                        {typeof section.evidence_count === "number" ? `${section.evidence_count} evidence` : "section"}
                      </span>
                      {section.is_locked ? <span className="rounded-full bg-rose-100 px-2 py-1 text-xs text-rose-700">Locked</span> : null}
                      {section.edited_by ? <span className="rounded-full bg-stone-100 px-2 py-1 text-xs text-stone-700">Edited by {section.edited_by}</span> : null}
                    </div>
                    {section.lock_reason ? <p className="mt-2 text-xs text-rose-700">Lock reason: {section.lock_reason}</p> : null}
                    {section.last_manual_edit_at ? <p className="mt-2 text-xs text-slate-500">Manual edit: {new Date(section.last_manual_edit_at).toLocaleString()}</p> : null}
                  </div>
                  {editable ? (
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="btn-secondary"
                        onClick={() => {
                          setEditingSlug(section.slug);
                          setDraftContent(section.content || "");
                        }}
                        type="button"
                      >
                        Edit section
                      </button>
                      {onToggleLock ? (
                        <button
                          className="btn-secondary"
                          disabled={lockingSlug === section.slug}
                          onClick={async () => {
                            try {
                              setLockingSlug(section.slug);
                              await onToggleLock(section.slug, !section.is_locked);
                            } finally {
                              setLockingSlug(null);
                            }
                          }}
                          type="button"
                        >
                          {lockingSlug === section.slug ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                          {section.is_locked ? "Unlock" : "Lock"}
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
                {isEditing ? (
                  <div className="mt-4 space-y-3">
                    <textarea className="input min-h-[220px]" value={draftContent} onChange={(e) => setDraftContent(e.target.value)} />
                    <div className="flex flex-wrap gap-2">
                      {onSaveSection ? (
                        <button
                          className="btn-primary"
                          onClick={async () => {
                            try {
                              setSavingSlug(section.slug);
                              await onSaveSection(section.slug, draftContent);
                              setEditingSlug(null);
                            } finally {
                              setSavingSlug(null);
                            }
                          }}
                          disabled={savingSlug === section.slug}
                          type="button"
                        >
                          {savingSlug === section.slug ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                          {savingSlug === section.slug ? "Saving..." : "Save section"}
                        </button>
                      ) : null}
                      <button className="btn-secondary" onClick={() => setEditingSlug(null)} type="button">
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <article
                    className="note-prose mt-4"
                    dangerouslySetInnerHTML={{ __html: marked.parse(section.content || "No content yet.") as string }}
                  />
                )}
              </section>
            );
          })}
        </div>
      ) : markdown ? (
        <article className="note-prose" dangerouslySetInnerHTML={{ __html: marked.parse(markdown) as string }} />
      ) : null}
    </div>
  );
}
