"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, getApiErrorMessage, setToken } from "@/lib/api";
import { getLastProjectId } from "@/lib/local-state";
import { useToast } from "@/components/ToastProvider";
import LoadingSpinner from "@/components/LoadingSpinner";

const isDevelopment = process.env.NODE_ENV !== "production";

export default function LoginPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [email, setEmail] = useState(isDevelopment ? "test@example.com" : "");
  const [password, setPassword] = useState(isDevelopment ? "password123" : "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setToken(data.access_token);
      const lastProjectId = getLastProjectId();
      showToast({
        tone: "success",
        title: "Logged in",
        message: lastProjectId ? "Returning you to the last project you were working on." : "Opening your research dashboard.",
      });
      router.push(lastProjectId ? `/projects/${lastProjectId}` : "/");
    } catch (err) {
      setError(getApiErrorMessage(err, "Login failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md card">
      <h1 className="mb-5 text-2xl font-semibold">Login</h1>
      {isDevelopment ? (
        <p className="mb-5 text-sm text-slate-600">
          Development mode pre-fills the local demo account for faster testing.
        </p>
      ) : null}
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="label">Email</label>
          <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label className="label">Password</label>
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <button className="btn-primary w-full" type="submit" disabled={loading}>
          {loading ? <LoadingSpinner /> : null}
          {loading ? "Logging in..." : "Login"}
        </button>
      </form>
    </div>
  );
}
