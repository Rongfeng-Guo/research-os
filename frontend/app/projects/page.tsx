"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiFetch, getApiErrorMessage, isApiError } from "@/lib/api";
import ProjectCard, { Project } from "@/components/ProjectCard";
import { useToast } from "@/components/ToastProvider";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { showToast } = useToast();

  async function loadProjects() {
    setError(null);
    setNeedsLogin(false);
    const data = await apiFetch<Project[]>("/projects");
    setProjects(data);
  }

  useEffect(() => {
    loadProjects()
      .catch((error) => {
        if (isApiError(error) && error.status === 401) {
          setNeedsLogin(true);
          setError(null);
          return;
        }
        setError(getApiErrorMessage(error, "Failed to load projects"));
      });
  }, []);

  async function importSnapshot(file: File) {
    setBusy(true);
    setError(null);
    try {
      const text = await file.text();
      const snapshot = JSON.parse(text) as Record<string, unknown>;
      const importedProject = await apiFetch<Project>("/projects/import", {
        method: "POST",
        body: JSON.stringify({ snapshot }),
      });
      await loadProjects();
      showToast({
        tone: "success",
        title: "Project restored",
        message: `Imported ${importedProject.title}.`,
      });
    } catch (error) {
      const message = getApiErrorMessage(error, "Failed to import snapshot");
      setError(message);
      showToast({ tone: "error", title: "Could not import snapshot", message });
    } finally {
      setBusy(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  return (
    <div className="space-y-6">
      <section className="card">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.22em] text-stone-500">Project library</p>
            <h1 className="mt-2 text-4xl font-semibold">All research projects</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Keep each topic as a reusable working area for sources, evidence review, note generation, and future updates.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <input
              ref={fileInputRef}
              accept=".json,application/json"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  void importSnapshot(file);
                }
              }}
              type="file"
            />
            <button className="btn-secondary" disabled={busy} onClick={() => fileInputRef.current?.click()} type="button">
              {busy ? "Importing..." : "Import snapshot"}
            </button>
            <Link href="/projects/new" className="btn-primary">New project</Link>
          </div>
        </div>
        <p className="mt-4 text-sm text-slate-500">You can restore a previously exported project snapshot into a new workspace without overwriting current projects.</p>
      </section>

      {needsLogin ? (
        <div className="card text-slate-600">
          Please <Link href="/login" className="underline underline-offset-4">log in</Link> to open your project library.
        </div>
      ) : null}
      {error ? <div className="card text-red-600">{error}</div> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {projects.length === 0 ? (
          <div className="card text-slate-500">
            No projects yet. Create your first recurring literature review workspace.
          </div>
        ) : null}
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </div>
  );
}
