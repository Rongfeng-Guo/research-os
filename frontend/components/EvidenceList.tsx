"use client";

import { useMemo, useState } from "react";
import { useToast } from "@/components/ToastProvider";
import LoadingSpinner from "@/components/LoadingSpinner";

export type EvidenceCard = {
  id: number;
  project_id?: number;
  card_type: string;
  title: string;
  content: string;
  source_title?: string;
  source_excerpt?: string;
  source_url?: string;
  source_chunk_id?: string;
  source_section?: string;
  confidence_score?: number;
  provider_name?: string;
  review_status?: string;
  is_pinned?: boolean;
  pinned_at?: string | null;
  user_note?: string;
  edited_at?: string | null;
  edited_by?: string;
};

type EditablePayload = {
  card_type: string;
  title: string;
  content: string;
  source_title: string;
  source_excerpt: string;
  source_section: string;
  confidence_score: string;
  user_note: string;
  is_pinned: boolean;
};

function emptyDraft(card: EvidenceCard): EditablePayload {
  return {
    card_type: card.card_type,
    title: card.title,
    content: card.content,
    source_title: card.source_title || "",
    source_excerpt: card.source_excerpt || "",
    source_section: card.source_section || "",
    confidence_score: typeof card.confidence_score === "number" ? String(card.confidence_score) : "0",
    user_note: card.user_note || "",
    is_pinned: Boolean(card.is_pinned),
  };
}

export default function EvidenceList({
  cards,
  onReviewStatusChange,
  onSaveCard,
}: {
  cards: EvidenceCard[];
  onReviewStatusChange?: (cardId: number, reviewStatus: string) => Promise<void> | void;
  onSaveCard?: (cardId: number, payload: Partial<EvidenceCard>) => Promise<void> | void;
}) {
  const { showToast } = useToast();
  const [activeType, setActiveType] = useState("all");
  const [activeStatus, setActiveStatus] = useState("all");
  const [activePinned, setActivePinned] = useState("all");
  const [activeSource, setActiveSource] = useState("all");
  const [busyCardId, setBusyCardId] = useState<number | null>(null);
  const [editingCardId, setEditingCardId] = useState<number | null>(null);
  const [draft, setDraft] = useState<EditablePayload | null>(null);

  const types = useMemo(() => ["all", ...Array.from(new Set(cards.map((card) => card.card_type)))], [cards]);
  const statuses = useMemo(() => ["all", ...Array.from(new Set(cards.map((card) => card.review_status || "suggested")))], [cards]);
  const sources = useMemo(
    () => ["all", ...Array.from(new Set(cards.map((card) => card.source_title || "Unknown source")))],
    [cards],
  );
  const visibleCards = cards.filter((card) => {
    const typeMatch = activeType === "all" || card.card_type === activeType;
    const statusMatch = activeStatus === "all" || (card.review_status || "suggested") === activeStatus;
    const pinnedMatch =
      activePinned === "all" ||
      (activePinned === "pinned" && card.is_pinned) ||
      (activePinned === "unpinned" && !card.is_pinned);
    const sourceMatch = activeSource === "all" || (card.source_title || "Unknown source") === activeSource;
    return typeMatch && statusMatch && pinnedMatch && sourceMatch;
  });

  async function updateStatus(cardId: number, reviewStatus: string) {
    if (!onReviewStatusChange) return;
    setBusyCardId(cardId);
    try {
      await onReviewStatusChange(cardId, reviewStatus);
      showToast({ tone: "success", title: "Evidence updated", message: `Card marked as ${reviewStatus}.` });
    } catch (error) {
      showToast({
        tone: "error",
        title: "Could not update evidence",
        message: error instanceof Error ? error.message : "Failed to update evidence",
      });
    } finally {
      setBusyCardId(null);
    }
  }

  async function saveCard(cardId: number) {
    if (!onSaveCard || !draft) return;
    setBusyCardId(cardId);
    try {
      await onSaveCard(cardId, {
        card_type: draft.card_type,
        title: draft.title,
        content: draft.content,
        source_title: draft.source_title,
        source_excerpt: draft.source_excerpt,
        source_section: draft.source_section,
        confidence_score: Number(draft.confidence_score || 0),
        user_note: draft.user_note,
        is_pinned: draft.is_pinned,
      });
      setEditingCardId(null);
      setDraft(null);
      showToast({ tone: "success", title: "Evidence saved", message: "Your manual edits were saved." });
    } catch (error) {
      showToast({
        tone: "error",
        title: "Could not save evidence",
        message: error instanceof Error ? error.message : "Failed to save evidence",
      });
    } finally {
      setBusyCardId(null);
    }
  }

  async function togglePinned(card: EvidenceCard) {
    if (!onSaveCard) return;
    setBusyCardId(card.id);
    try {
      await onSaveCard(card.id, { is_pinned: !card.is_pinned });
      showToast({
        tone: "success",
        title: card.is_pinned ? "Evidence unpinned" : "Evidence pinned",
        message: card.is_pinned ? "This card will no longer be prioritized visually." : "This card is now highlighted for future note work.",
      });
    } catch (error) {
      showToast({
        tone: "error",
        title: "Could not update pin",
        message: error instanceof Error ? error.message : "Failed to update pin state",
      });
    } finally {
      setBusyCardId(null);
    }
  }

  return (
    <div className="card">
      <div className="mb-4 flex flex-col gap-3">
        <div>
          <h2 className="text-xl font-semibold">Evidence cards</h2>
          <p className="text-sm text-slate-600">
            Review, edit, pin, and preserve the evidence you actually trust enough to keep in your notebook.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {types.map((type) => (
            <button
              key={type}
              className={type === activeType ? "btn-primary" : "btn-secondary"}
              onClick={() => setActiveType(type)}
              type="button"
            >
              {type === "all" ? "All types" : type.replace("_", " ")}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {statuses.map((status) => (
            <button
              key={status}
              className={status === activeStatus ? "btn-primary" : "btn-secondary"}
              onClick={() => setActiveStatus(status)}
              type="button"
            >
              {status === "all" ? "All statuses" : status}
            </button>
          ))}
          {["all", "pinned", "unpinned"].map((pinnedState) => (
            <button
              key={pinnedState}
              className={pinnedState === activePinned ? "btn-primary" : "btn-secondary"}
              onClick={() => setActivePinned(pinnedState)}
              type="button"
            >
              {pinnedState === "all" ? "All pins" : pinnedState}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {sources.map((source) => (
            <button
              key={source}
              className={source === activeSource ? "btn-primary" : "btn-secondary"}
              onClick={() => setActiveSource(source)}
              type="button"
            >
              {source === "all" ? "All sources" : source}
            </button>
          ))}
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {visibleCards.length === 0 ? (
          <p className="text-sm text-slate-500">No evidence cards match the current filters.</p>
        ) : null}
        {visibleCards.map((card) => {
          const isEditing = editingCardId === card.id && draft;
          return (
            <div
              key={card.id}
              className={`rounded-2xl border p-4 ${card.is_pinned ? "border-amber-300 bg-amber-50/60" : "border-stone-200 bg-stone-50/70"}`}
            >
              <div className="mb-2 flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                <span>{card.card_type}</span>
                <span className="rounded-full bg-white px-2 py-1 normal-case tracking-normal text-slate-600">
                  {card.review_status || "suggested"}
                </span>
                {card.is_pinned ? (
                  <span className="rounded-full bg-amber-100 px-2 py-1 normal-case tracking-normal text-amber-800">Pinned</span>
                ) : null}
                {card.provider_name ? (
                  <span className="rounded-full bg-white px-2 py-1 normal-case tracking-normal text-slate-600">{card.provider_name}</span>
                ) : null}
              </div>
              {isEditing ? (
                <div className="space-y-3">
                  <input className="input" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
                  <select className="input" value={draft.card_type} onChange={(e) => setDraft({ ...draft, card_type: e.target.value })}>
                    <option value="claim">claim</option>
                    <option value="method">method</option>
                    <option value="dataset">dataset</option>
                    <option value="limitation">limitation</option>
                    <option value="open_question">open_question</option>
                  </select>
                  <textarea className="input min-h-[110px]" value={draft.content} onChange={(e) => setDraft({ ...draft, content: e.target.value })} />
                  <input className="input" placeholder="Source title" value={draft.source_title} onChange={(e) => setDraft({ ...draft, source_title: e.target.value })} />
                  <input className="input" placeholder="Section label" value={draft.source_section} onChange={(e) => setDraft({ ...draft, source_section: e.target.value })} />
                  <textarea className="input min-h-[80px]" placeholder="Supporting snippet" value={draft.source_excerpt} onChange={(e) => setDraft({ ...draft, source_excerpt: e.target.value })} />
                  <input className="input" placeholder="Confidence 0-1" value={draft.confidence_score} onChange={(e) => setDraft({ ...draft, confidence_score: e.target.value })} />
                  <textarea className="input min-h-[70px]" placeholder="Your note about this evidence" value={draft.user_note} onChange={(e) => setDraft({ ...draft, user_note: e.target.value })} />
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    <input checked={draft.is_pinned} onChange={(e) => setDraft({ ...draft, is_pinned: e.target.checked })} type="checkbox" />
                    Pin this evidence
                  </label>
                </div>
              ) : (
                <>
                  <h3 className="font-medium">{card.title}</h3>
                  <p className="mt-2 text-sm text-slate-600">{card.content}</p>
                </>
              )}
              <div className="mt-3 space-y-2 rounded-xl bg-white px-3 py-3 text-xs leading-5 text-slate-500">
                <p><strong>Source:</strong> {isEditing ? draft.source_title : card.source_title || "Unknown source"}</p>
                {(isEditing ? draft.source_section : card.source_section) ? <p><strong>Section:</strong> {isEditing ? draft.source_section : card.source_section}</p> : null}
                {card.source_chunk_id ? <p><strong>Chunk:</strong> {card.source_chunk_id}</p> : null}
                <p><strong>Confidence:</strong> {isEditing ? Number(draft.confidence_score || 0).toFixed(2) : (card.confidence_score ?? 0).toFixed(2)}</p>
                {(isEditing ? draft.source_excerpt : card.source_excerpt) ? <p><strong>Snippet:</strong> {isEditing ? draft.source_excerpt : card.source_excerpt}</p> : null}
                {(isEditing ? draft.user_note : card.user_note) ? <p><strong>Note:</strong> {isEditing ? draft.user_note : card.user_note}</p> : null}
                {card.edited_at ? <p><strong>Edited:</strong> {new Date(card.edited_at).toLocaleString()} by {card.edited_by || "user"}</p> : null}
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {onReviewStatusChange ? (
                  <>
                    <button className="btn-secondary" disabled={busyCardId === card.id} onClick={() => updateStatus(card.id, "accepted")} type="button">
                      {busyCardId === card.id ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                      Accept
                    </button>
                    <button className="btn-secondary" disabled={busyCardId === card.id} onClick={() => updateStatus(card.id, "rejected")} type="button">
                      {busyCardId === card.id ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                      Reject
                    </button>
                    <button className="btn-secondary" disabled={busyCardId === card.id} onClick={() => updateStatus(card.id, "suggested")} type="button">
                      {busyCardId === card.id ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                      Reset
                    </button>
                  </>
                ) : null}
                {onSaveCard ? (
                  <>
                    {isEditing ? (
                      <>
                        <button className="btn-primary" disabled={busyCardId === card.id} onClick={() => saveCard(card.id)} type="button">
                          {busyCardId === card.id ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                          Save
                        </button>
                        <button className="btn-secondary" onClick={() => { setEditingCardId(null); setDraft(null); }} type="button">
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button className="btn-secondary" onClick={() => { setEditingCardId(card.id); setDraft(emptyDraft(card)); }} type="button">
                          Edit
                        </button>
                        <button
                          className="btn-secondary"
                          disabled={busyCardId === card.id}
                          onClick={() => void togglePinned(card)}
                          type="button"
                        >
                          {busyCardId === card.id ? <LoadingSpinner className="h-3.5 w-3.5" /> : null}
                          {card.is_pinned ? "Unpin" : "Pin"}
                        </button>
                      </>
                    )}
                  </>
                ) : null}
                {card.source_url ? (
                  <a
                    className="inline-flex text-sm font-medium text-slate-700 underline underline-offset-4"
                    href={card.source_url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    Open source
                  </a>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
