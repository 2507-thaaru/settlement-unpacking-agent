import { queryOptions } from "@tanstack/react-query";

export type Summary = {
  passes_implemented: number;
  passes_total: number;
  total_exceptions_found: number;
  total_batches: number;
  total_orders: number;
  total_bank_credits: number;
};

export type PassInfo = {
  pass_name: string;
  status: string;
  exception_count: number;
  metrics: Record<string, unknown> | null;
  detail: string | null;
};

export type ForecastRow = {
  settlement_id: string;
  still_held: number;
  release_due_date: string;
};

export type Forecast = {
  total_reserve_held: number;
  total_reserve_released: number;
  total_still_held: number;
  batches_with_overdue_reserve: number;
  forecast_schedule: ForecastRow[];
};

export type ExceptionRow = {
  settlement_id: string | null;
  order_id: string | null;
  category: string;
  description: string;
  amount: number | null;
};

export type ExceptionsResponse = { count: number; exceptions: ExceptionRow[] };

export type DatasetMeta = { name: string; description: string; rows: number };

export type DatasetsResponse = { datasets: DatasetMeta[] };

export type DatasetResponse = {
  dataset: string;
  total_rows: number;
  offset: number;
  limit: number;
  records: Record<string, string | number | null>[];
};

async function api<T>(path: string): Promise<T> {
  const res = await fetch(`/api/proxy/${path}`, { headers: { accept: "application/json" } });
  if (!res.ok) throw new Error(`Pipeline API returned ${res.status}`);
  return (await res.json()) as T;
}

export const summaryQuery = () =>
  queryOptions({ queryKey: ["summary"], queryFn: () => api<Summary>("summary") });

export const passesQuery = () =>
  queryOptions({ queryKey: ["passes"], queryFn: () => api<PassInfo[]>("passes") });

export const forecastQuery = () =>
  queryOptions({ queryKey: ["forecast"], queryFn: () => api<Forecast>("forecast") });

export const exceptionsQuery = () =>
  queryOptions({
    queryKey: ["exceptions"],
    queryFn: () => api<ExceptionsResponse>("exceptions"),
  });

export type GraphNode = {
  id: string;
  label: string;
  category: "source_data" | "pass" | "exception_type" | "orchestration" | "report" | string;
  status?: string | null;
  rows?: number | null;
  count?: number | null;
  exception_count?: number | null;
  color?: string | null;
  borderColor?: string | null;
  fontColor?: string | null;
  shape?: string | null;
};

export type GraphEdge = { from: string; to: string; label?: string | null };

export type GraphResponse = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes?: number;
  total_edges?: number;
};

export const graphQuery = () =>
  queryOptions({ queryKey: ["graph"], queryFn: () => api<GraphResponse>("graph") });

export const datasetsQuery = () =>
  queryOptions({ queryKey: ["datasets"], queryFn: () => api<DatasetsResponse>("data") });

export const datasetQuery = (name: string, limit = 100) =>
  queryOptions({
    queryKey: ["dataset", name, limit],
    queryFn: () => api<DatasetResponse>(`data/${name}?limit=${limit}`),
  });

export async function triggerRun() {
  const res = await fetch("/api/proxy/run", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{}",
  });
  if (!res.ok) throw new Error(`Re-run failed (${res.status})`);
  return res.json();
}

export const PASS_LABELS: Record<string, string> = {
  pass1_batch_match: "Batch match",
  pass2_order_validation: "Order validation",
  pass3_reserve_forecast: "Reserve forecast",
  pass4_gst_itc: "GST ITC check",
  pass5_cross_period: "Cross-period flag",
};

export function formatINR(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value);
}
