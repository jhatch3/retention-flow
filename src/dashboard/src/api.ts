// Typed client for the RetentionFlow dashboard API (FastAPI on :8000,
// proxied via Vite at /api).

export interface DbtModel {
  name: string;
  status: string;
  execution_time: number;
}

export interface PipelineStatus {
  available: boolean;
  generated_at?: string;
  models?: DbtModel[];
  model_count?: number;
  models_ok?: number;
  tests?: Record<string, number>;
  tests_total?: number;
}

export interface Segment {
  segment: string;
  rows: number;
  churn_rate: number;
}

export interface WarehouseData {
  gold_rows: number;
  gold_churn_rate: number;
  splits: Record<string, number>;
  segments: Segment[];
  raw_orders: number;
  synthetic_orders: number;
}

export interface WarehouseColumn {
  name: string;
  type: string;
}

export interface WarehouseTable {
  schema: string;
  name: string;
  kind: "table" | "view";
  row_count: number;
  columns: WarehouseColumn[];
}

export interface WarehouseTableList {
  tables: WarehouseTable[];
}

export type WarehouseValue = string | number | boolean | null;

export interface WarehouseSample {
  schema: string;
  table: string;
  columns: string[];
  rows: WarehouseValue[][];
  row_limit: number;
  error?: string;
}

export interface ModelVersion {
  version: string;
  is_champion: boolean;
  decision_threshold: string | null;
  roc_auc: number | null;
  pr_auc: number | null;
  created_at: string;
}

export interface ModelRegistry {
  model_name: string;
  experiment: string;
  champion_version: string | null;
  champion_metrics: Record<string, number>;
  versions: ModelVersion[];
}

export interface FeatureImportance {
  features: { feature: string; importance: number }[];
}

export interface Predictions {
  scored: boolean;
  total?: number;
  predicted_churn?: number;
  avg_probability?: number;
  model_version?: string;
  scored_at?: string | null;
  risk_histogram?: { bucket: number; count: number }[];
  top_at_risk?: { customer_unique_id: string; churn_probability: number }[];
}

export interface ScoreResult {
  scored_count: number;
  predicted_churn: number;
  threshold: number;
  model_version: string;
}

export interface ScoreEvent {
  stage: string;
  message: string;
  progress: number;
  ts: string;
  done?: boolean;
  result?: ScoreResult;
}

export interface RebuildEvent {
  stage: string;
  message: string;
  progress: number;
  elapsed: number;
  ts: string;
  done?: boolean;
  error?: boolean;
  gold_rows?: number;
  total_seconds?: number;
}

export interface RunRecord {
  id: string;
  kind: string;
  status: string;
  started_at: string;
  duration_s: number;
  detail: string;
}

export interface Runs {
  runs: RunRecord[];
}

export interface ShapContribution {
  feature: string;
  shap_value: number;
  feature_value: number | null;
  rank: number;
}

export interface ShapCustomer {
  customer_unique_id: string;
  churn_probability: number;
  contributions: ShapContribution[];
}

export interface ShapData {
  available: boolean;
  global: {
    base_value: number | null;
    features: { feature: string; mean_abs_shap: number }[];
  };
  customers: ShapCustomer[];
}

export interface PipelineReport {
  dbt?: { gold_rows: number; seconds: number };
  model?: { version: string; roc_auc: number; pr_auc: number; threshold: number };
  scoring?: {
    scored_count: number;
    predicted_churn: number;
    threshold: number;
    model_version: string;
  };
  total_seconds: number;
}

export interface EvalModel {
  available: boolean;
  model_name: string;
  champion_version?: string;
  base_model?: string | null;
  n_train?: number | null;
  pass_threshold?: number;
  metrics?: {
    test_accuracy: number | null;
    test_f1_macro: number | null;
    test_mae_grades: number | null;
    validation_accuracy: number | null;
  };
  created_at?: string;
}

// ─── Triage Inbox ────────────────────────────────────────────────────────
export type RiskTier = "crit" | "high" | "med" | "low";
export type FilterKey = "all" | "crit" | "high" | "med";

export interface InboxCustomerSummary {
  customer_unique_id: string;
  display_name: string;
  city: string;
  ltv_brl: number;
  risk: number;
  tier: RiskTier;
  recency_days: number;
  reviews_avg: number;
  delivery_avg_days: number;
  orders_lifetime: number;
  joined_human: string;
  last_order_label: string;
  top_driver: string;
  status: "open" | "sent" | "snoozed";
  email_sent_at: string | null;
}

export interface InboxCustomerList {
  customers: InboxCustomerSummary[];
  totals: {
    all: number;
    crit: number;
    high: number;
    med: number;
    low: number;
    revenue_at_risk_brl: number;
  };
  scored_at: string;
  model_version: string;
  threshold: number;
}

export interface InboxDriver {
  feature: string;
  value: string;
  contrib: number;
  why: string;
}

export interface InboxEvent {
  ts: string;
  ts_human: string;
  title: string;
  note: string | null;
  tag: "risk" | "neutral" | "pos";
}

export interface InboxEmailDraft {
  generated_at: string;
  generated_by: string;
  persona: string;
  grounded_on: string;
  subject: string;
  body: string;
  to: string;
  from_name: string;
}

export interface InboxEval {
  distilbert_score: number;
  distilbert_ms: number;
  judge_score: number;
  judge_ms: number;
  pass_threshold: number;
  passed: boolean;
  agreement_delta: number;
}

export interface InboxPlay {
  id: string;
  name: string;
  active: boolean;
  save_rate_pct: number;
  sample_n: number;
}

export interface InboxCustomerDetail {
  summary: InboxCustomerSummary;
  drivers: InboxDriver[];
  history: InboxEvent[];
  email: InboxEmailDraft;
  eval: InboxEval;
  plays: InboxPlay[];
  cohort_label: string;
  cohort_save_rate_pct: number;
  cohort_n: number;
}

async function request<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  pipeline: () => request<PipelineStatus>("/api/pipeline"),
  data: () => request<WarehouseData>("/api/data"),
  warehouseTables: () => request<WarehouseTableList>("/api/warehouse/tables"),
  warehouseSample: (schema: string, table: string, limit = 25) =>
    request<WarehouseSample>(
      `/api/warehouse/sample?schema=${encodeURIComponent(schema)}` +
        `&table=${encodeURIComponent(table)}&limit=${limit}`,
    ),
  models: () => request<ModelRegistry>("/api/models"),
  featureImportance: () => request<FeatureImportance>("/api/feature-importance"),
  predictions: () => request<Predictions>("/api/predictions"),
  shap: () => request<ShapData>("/api/shap"),
  runs: () => request<Runs>("/api/runs"),
  evalModel: () => request<EvalModel>("/api/eval/model"),
  inbox: {
    customers: (filter: FilterKey = "all") =>
      request<InboxCustomerList>(`/api/inbox/customers?filter=${filter}`),
    customer: (id: string) =>
      request<InboxCustomerDetail>(
        `/api/inbox/customers/${encodeURIComponent(id)}`,
      ),
  },
};
