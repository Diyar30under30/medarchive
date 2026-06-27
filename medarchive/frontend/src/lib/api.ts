// Single typed gateway to the MedArchive backend.
export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) throw new Error(`${init?.method ?? "GET"} ${path} → ${res.status}`);
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const apiGet = <T>(p: string) => req<T>(p);

// ── Types (mirror app/schemas/schemas.py) ────────────────────────────────────
export interface Service {
  service_id: string;
  service_name: string;
  category: string;
  source_code?: string | null;
  tariff_code?: string | null;
  synonyms: string[];
  icd_code?: string | null;
  is_active: boolean;
}
export interface ServiceList { total: number; items: Service[]; }

export interface Partner {
  partner_id: string;
  name: string;
  city?: string | null;
  address?: string | null;
  bin?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  is_active: boolean;
}

export interface PartnerPrice {
  partner_id: string;
  partner_name: string;
  city?: string | null;
  address?: string | null;
  price_resident_kzt?: number | null;
  price_nonresident_kzt?: number | null;
  currency_original: string;
  price_original?: number | null;
  effective_date?: string | null;
  is_verified: boolean;
}

export interface PriceItem {
  item_id: string;
  service_name_raw: string;
  service_id?: string | null;
  service_name?: string | null;
  match_confidence?: number | null;
  match_method: string;
  price_resident_kzt?: number | null;
  price_nonresident_kzt?: number | null;
  price_original?: number | null;
  currency_original: string;
  is_verified: boolean;
  effective_date?: string | null;
  is_active: boolean;
}

export interface SearchResult { services: Service[]; partners: Partner[]; }

export interface Candidate {
  service_id: string;
  service_name: string;
  category: string;
  score: number;
  method: string;
  lexical: number;
  semantic: number;
}
export interface ReviewItem {
  review_id: string;
  item_id: string;
  service_name_raw: string;
  source_fragment?: string | null;
  partner_name?: string | null;
  price_resident_kzt?: number | null;
  price_nonresident_kzt?: number | null;
  candidates: Candidate[];
  specialty_hint?: string | null;
  status: string;
}

export interface Job {
  job_id: string;
  archive_name?: string | null;
  status: string;
  total_files: number;
  processed_files: number;
  error_count: number;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface Anomaly {
  item_id: string;
  kind: string;
  note: string;
  service_name_raw: string;
  service_name?: string | null;
  service_id?: string | null;
  partner_name: string;
  city?: string | null;
  price_resident_kzt?: number | null;
  price_nonresident_kzt?: number | null;
  effective_date?: string | null;
}

export interface Metrics {
  services_in_directory: number;
  synonyms_learned: number;
  documents_total: number;
  documents_by_status: Record<string, number>;
  documents_errored: number;
  positions_total: number;
  auto_matched: number;
  matched_any: number;
  unmatched: number;
  review_queue_open: number;
  auto_normalization_rate: number;
  anomalies_flagged: number;
  matches_by_method: Record<string, number>;
  per_format_success: Record<string, { total: number; ok: number; success_rate: number }>;
  generated_at: string;
}

export interface PriceHistory {
  service_id: string;
  service_name: string;
  entries: {
    item_id: string;
    partner_id: string;
    partner_name?: string | null;
    price_resident_kzt?: number | null;
    price_nonresident_kzt?: number | null;
    effective_date?: string | null;
    is_active: boolean;
    superseded_by?: string | null;
  }[];
}

// ── Endpoints ─────────────────────────────────────────────────────────────────
export const api = {
  services: (q?: string, category?: string, limit = 50) =>
    apiGet<ServiceList>(
      `/services?limit=${limit}` +
        (q ? `&q=${encodeURIComponent(q)}` : "") +
        (category ? `&category=${encodeURIComponent(category)}` : "")
    ),
  servicePartners: (id: string, sort: "price" | "date" = "price") =>
    apiGet<PartnerPrice[]>(`/services/${id}/partners?sort=${sort}`),
  priceHistory: (id: string) => apiGet<PriceHistory>(`/services/${id}/price-history`),
  partners: (city?: string, q?: string) =>
    apiGet<Partner[]>(
      `/partners?` + (city ? `city=${encodeURIComponent(city)}&` : "") + (q ? `q=${encodeURIComponent(q)}` : "")
    ),
  partnerServices: (id: string) => apiGet<PriceItem[]>(`/partners/${id}/services`),
  search: (q: string) => apiGet<SearchResult>(`/search?q=${encodeURIComponent(q)}`),
  unmatched: (status = "open") => apiGet<ReviewItem[]>(`/unmatched?status=${status}`),
  batchConfirm: (threshold = 0.85) =>
    req<{ confirmed: number; synonyms_learned: number }>(
      `/admin/batch-confirm?threshold=${threshold}`,
      { method: "POST" }
    ),
  match: (body: {
    item_id: string;
    service_id?: string;
    new_service_name?: string;
    new_service_category?: string;
    reject?: boolean;
    note?: string;
  }) =>
    req<{ message: string; is_verified: boolean; learned_synonym?: string | null }>(`/match`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  ingest: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<Job>(`/admin/ingest`, { method: "POST", body: fd });
  },
  job: (id: string) => apiGet<Job>(`/admin/jobs/${id}`),
  jobs: () => apiGet<Job[]>(`/admin/jobs`),
  metrics: () => apiGet<Metrics>(`/metrics`),
  anomalies: () => apiGet<Anomaly[]>(`/anomalies`),
  exportCsvUrl: () => `${API_BASE}/export.csv`,
  exportXlsxUrl: () => `${API_BASE}/export.xlsx`,
};

export const kzt = (v?: number | null) =>
  v == null ? "—" : new Intl.NumberFormat("ru-RU").format(Math.round(v)) + " ₸";
