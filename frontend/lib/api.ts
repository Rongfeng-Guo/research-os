const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;
  body: string;

  constructor(status: number, detail: string, body: string) {
    super(detail || `Request failed: ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail || `Request failed: ${status}`;
    this.body = body;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("research_os_token");
}

export function setToken(token: string) {
  localStorage.setItem("research_os_token", token);
}

export function clearToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("research_os_token");
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function getApiErrorMessage(error: unknown, fallback = "Request failed"): string {
  if (isApiError(error)) return error.detail;
  if (error instanceof Error) return error.message;
  return fallback;
}

function parseApiError(status: number, body: string): ApiError {
  if (!body) {
    return new ApiError(status, `Request failed: ${status}`, body);
  }
  try {
    const parsed = JSON.parse(body) as { detail?: string };
    if (parsed.detail) {
      return new ApiError(status, parsed.detail, body);
    }
  } catch {
    // Fall back to plain text below.
  }
  return new ApiError(status, body, body);
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, cache: "no-store" });
  const text = await res.text();

  if (!res.ok) {
    throw parseApiError(res.status, text);
  }

  if (!text) {
    return null as T;
  }
  return JSON.parse(text) as T;
}

export async function apiFetchOrNull<T>(path: string, options: RequestInit = {}): Promise<T | null> {
  try {
    return await apiFetch<T>(path, options);
  } catch (error) {
    if (isApiError(error) && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function apiFetchBlob(path: string, options: RequestInit = {}): Promise<{ blob: Blob; filename: string | null; contentType: string | null }> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw parseApiError(res.status, text);
  }

  const blob = await res.blob();
  const contentDisposition = res.headers.get("content-disposition");
  const filenameMatch = contentDisposition?.match(/filename=\"?([^"]+)\"?/i);
  return {
    blob,
    filename: filenameMatch?.[1] || null,
    contentType: res.headers.get("content-type"),
  };
}
