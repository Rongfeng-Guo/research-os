"use client";

import { FormEvent, useState } from "react";
import { apiFetch, getApiErrorMessage } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function UploadSourceForm({
  projectId,
  onUploaded,
}: {
  projectId: number;
  onUploaded?: () => Promise<void> | void;
}) {
  const { showToast } = useToast();
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [contentType, setContentType] = useState("text");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setStatus("");
    try {
      let response: { title: string };
      if (file) {
        const formData = new FormData();
        formData.append("file", file);
        response = await apiFetch<{ title: string }>(`/papers/projects/${projectId}/upload-file`, {
          method: "POST",
          body: formData,
        });
      } else {
        response = await apiFetch<{ title: string }>(`/papers/projects/${projectId}/upload-text`, {
          method: "POST",
          body: JSON.stringify({
            title: title || "Uploaded source",
            text,
            content_type: contentType,
          }),
        });
      }
      setTitle("");
      setText("");
      setContentType("text");
      setFile(null);
      setStatus(`Uploaded source: ${response.title}`);
      showToast({
        tone: "success",
        title: "Source uploaded",
        message: `${response.title} is now attached to this project.`,
      });
      await onUploaded?.();
    } catch (error) {
      const message = getApiErrorMessage(error, "Upload failed");
      setStatus(message);
      showToast({ tone: "error", title: "Could not upload source", message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Upload source material</h2>
        <p className="text-sm text-slate-600">
          Paste abstract/body text or upload `.txt`, `.md`, and text-based `.pdf` files. PDF uploads now preserve page anchors and common section headings when extractable. Scanned or image-only PDFs still fall back to a clear parsing error.
        </p>
      </div>
      <form className="space-y-3" onSubmit={onSubmit}>
        <div>
          <label className="label">Source title</label>
          <input
            className="input"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Survey notes on retrieval-augmented generation"
          />
        </div>
        <div>
          <label className="label">Source kind</label>
          <select className="input" value={contentType} onChange={(event) => setContentType(event.target.value)}>
            <option value="text">Plain text</option>
            <option value="markdown">Markdown</option>
            <option value="abstract">Abstract / body text</option>
          </select>
        </div>
        <div>
          <label className="label">Source text</label>
          <textarea
            className="input min-h-40"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Paste abstract, markdown, or cleaned text here..."
            required={!file}
          />
        </div>
        <div>
          <label className="label">Optional file upload</label>
          <input
            className="input"
            type="file"
            accept=".txt,.md,.markdown,.pdf"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <p className="mt-2 text-xs text-slate-500">
            If a file is selected, it will be uploaded instead of the pasted text.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-primary" disabled={loading} type="submit">
            {loading ? <LoadingSpinner /> : null}
            {loading ? "Uploading..." : "Add Source"}
          </button>
          {status ? <p className="text-sm text-slate-500">{status}</p> : null}
        </div>
      </form>
    </div>
  );
}
