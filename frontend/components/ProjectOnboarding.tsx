"use client";

import Link from "next/link";

export default function ProjectOnboarding({
  projectId,
  onDismiss,
}: {
  projectId: number;
  onDismiss: () => void;
}) {
  return (
    <section className="card border-stone-900/10 bg-gradient-to-br from-amber-50 to-white">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">Quick start walkthrough</p>
          <h2 className="mt-2 text-2xl font-semibold">Your project is ready. Here is the fastest path to a useful note.</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl bg-white/80 p-4">
              <p className="text-xs uppercase tracking-wide text-stone-500">Step 1</p>
              <p className="mt-2 text-sm text-slate-700">Add a paper or paste source text so the project has something concrete to analyze.</p>
            </div>
            <div className="rounded-2xl bg-white/80 p-4">
              <p className="text-xs uppercase tracking-wide text-stone-500">Step 2</p>
              <p className="mt-2 text-sm text-slate-700">Run extraction to create evidence cards you can review, edit, accept, reject, or pin.</p>
            </div>
            <div className="rounded-2xl bg-white/80 p-4">
              <p className="text-xs uppercase tracking-wide text-stone-500">Step 3</p>
              <p className="mt-2 text-sm text-slate-700">Generate the first topic note, then refine sections and lock what you want to preserve.</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className="btn-secondary" href={`/projects/${projectId}/evidence`}>Review evidence later</Link>
            <Link className="btn-secondary" href={`/projects/${projectId}/note`}>Open note surface</Link>
          </div>
        </div>
        <button className="btn-secondary" onClick={onDismiss} type="button">
          Dismiss walkthrough
        </button>
      </div>
    </section>
  );
}
