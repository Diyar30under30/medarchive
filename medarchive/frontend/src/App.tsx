import { useEffect, useState } from "react";
import { apiGet, type Health } from "./lib/api";

// A0 placeholder shell. Proves the frontend boots and reaches the API.
// Real Search / Service / Partner / Admin surfaces land in A7 (ui-ux-pro-max).
export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Health>("/health").then(setHealth).catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex items-center justify-center p-6">
      <div className="max-w-lg w-full bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <h1 className="text-2xl font-semibold tracking-tight">MedArchive</h1>
        <p className="mt-1 text-slate-500 text-sm">
          Каталог медицинских услуг партнёров · normalized price archive
        </p>

        <div className="mt-6 rounded-xl bg-slate-50 border border-slate-200 p-4 text-sm">
          <div className="font-medium text-slate-700 mb-2">Состояние API</div>
          {error && <div className="text-red-600">API недоступен: {error}</div>}
          {!error && !health && <div className="text-slate-400">Подключение…</div>}
          {health && (
            <dl className="grid grid-cols-2 gap-y-1">
              <dt className="text-slate-500">status</dt>
              <dd className="text-emerald-600 font-medium">{health.status}</dd>
              <dt className="text-slate-500">version</dt>
              <dd>{health.version}</dd>
              <dt className="text-slate-500">database</dt>
              <dd>{health.database}</dd>
              <dt className="text-slate-500">embeddings</dt>
              <dd>{String(health.embeddings)}</dd>
              <dt className="text-slate-500">ocr</dt>
              <dd>{String(health.ocr)}</dd>
            </dl>
          )}
        </div>

        <p className="mt-6 text-xs text-slate-400">
          Phase A0 · scaffold. Next: reference directory → fixtures → extractors →
          matching engine.
        </p>
      </div>
    </div>
  );
}
