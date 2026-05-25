"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import EvidenceList, { EvidenceCard } from "@/components/EvidenceList";
import { apiFetch, getApiErrorMessage, isApiError } from "@/lib/api";
import { setLastProjectId } from "@/lib/local-state";

export default function EvidencePage({ params }: { params: { id: string } }) {
  const projectId = Number(params.id);
  const [cards, setCards] = useState<EvidenceCard[]>([]);
  const [status, setStatus] = useState("Loading evidence...");
  const [needsLogin, setNeedsLogin] = useState(false);

  function loadCards() {
    setStatus("Loading evidence...");
    apiFetch<EvidenceCard[]>(`/evidence/projects/${projectId}`)
      .then((data) => {
        setCards(data);
        setLastProjectId(projectId);
        setStatus(data.length ? "" : "No evidence cards yet. Run extraction or add a source to create the first set.");
      })
      .catch((error) => {
        if (isApiError(error) && error.status === 401) {
          setNeedsLogin(true);
          setStatus("");
          return;
        }
        setStatus(getApiErrorMessage(error, "Failed to load evidence"));
      });
  }

  useEffect(() => {
    loadCards();
  }, [projectId]);

  async function updateReviewStatus(cardId: number, reviewStatus: string) {
    const updatedCard = await apiFetch<EvidenceCard>(`/evidence/${cardId}`, {
      method: "PATCH",
      body: JSON.stringify({ review_status: reviewStatus }),
    });
    setCards((current) => current.map((card) => (card.id === cardId ? updatedCard : card)));
  }

  async function saveCard(cardId: number, payload: Partial<EvidenceCard>) {
    const updatedCard = await apiFetch<EvidenceCard>(`/evidence/${cardId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    setCards((current) => current.map((card) => (card.id === cardId ? updatedCard : card)));
  }

  return (
    <div className="space-y-6">
      <section className="card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-stone-500">Research workspace</p>
            <h1 className="mt-2 text-3xl font-semibold">Evidence cards</h1>
            <p className="mt-2 text-sm text-slate-600">Filter and review extracted evidence before regenerating your note.</p>
          </div>
          <Link className="btn-secondary" href={`/projects/${projectId}`}>Back to project</Link>
        </div>
        {needsLogin ? <p className="mt-4 text-sm text-slate-500">Please log in again to review evidence cards.</p> : null}
        {status ? <p className="mt-4 text-sm text-slate-500">{status}</p> : null}
      </section>
      <EvidenceList cards={cards} onReviewStatusChange={updateReviewStatus} onSaveCard={saveCard} />
    </div>
  );
}
