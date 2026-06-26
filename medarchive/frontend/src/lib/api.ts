// Single place the frontend talks to the backend. Base URL is build-time
// injected so the same bundle runs on host and in Docker.
export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return (await res.json()) as T;
}

export interface Health {
  status: string;
  version: string;
  database: string;
  embeddings: boolean;
  ocr: boolean;
}
