"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, getApiErrorMessage } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function NewProjectPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [title, setTitle] = useState("Weekly literature review");
  const [topic, setTopic] = useState("Track a focused research topic, review new papers, extract reusable evidence, and maintain a living note.");
  const [description, setDescription] = useState("Personal workspace for recurring reading, evidence review, and note updates.");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const project = await apiFetch<{ id: number }>("/projects", {
        method: "POST",
        body: JSON.stringify({ title, topic, description }),
      });
      showToast({
        tone: "success",
        title: "Project created",
        message: "Next, add a source or run extraction to start building the note.",
      });
      router.push(`/projects/${project.id}?welcome=1`);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to create project"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <section className="card">
        <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">New project</p>
        <h1 className="mt-2 text-3xl font-semibold">Create a personal research workspace</h1>
        <p className="mt-3 text-sm leading-7 text-slate-600">
          Use one project per topic you expect to revisit. The project becomes the home for sources, evidence cards, notes, and update history.
        </p>
      </section>
      <div className="card">
        <form className="space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="label">Project title</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Multimodal Retrieval Review" />
          </div>
          <div>
            <label className="label">Research topic</label>
            <textarea className="input min-h-32" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="What are you trying to track or understand?" />
          </div>
          <div>
            <label className="label">Working description</label>
            <textarea className="input min-h-28" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Why this topic matters and how you will use the note." />
          </div>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <button className="btn-primary" disabled={loading} type="submit">
            {loading ? <LoadingSpinner /> : null}
            {loading ? "Creating..." : "Create project"}
          </button>
        </form>
      </div>
    </div>
  );
}
