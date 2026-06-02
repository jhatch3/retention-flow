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

export interface Predictions {
  scored: boolean;
  total?: number;
  predicted_churn?: number;
  avg_probability?: number;
  model_version?: string;
  scored_at?: string | null;
  risk_histogram?: { bucket: number; count: number }[];
  top_at_risk?: {
    customer_unique_id: string;
    display_name?: string;
    churn_probability: number;
  }[];
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
  emails?: {
    generated: number;
    failed: number;
    top_n_requested: number;
    elapsed_seconds: number;
    model: string;
    concurrency?: number;
  };
  total_seconds: number;
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
  judge_score: number;
  judge_ms: number;
  pass_threshold: number;
  passed: boolean;
  reasoning: string;
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

export interface GeneratedEmail {
  id: number;
  customer_unique_id: string;
  display_name: string;
  subject: string;
  preview: string;
  model: string | null;
  status: string;
  generated_at: string | null;
  churn_probability: number | null;
  risk_tier: RiskTier;
  judge_score: number | null;
  judge_passed: boolean | null;
}

export interface GeneratedEmails {
  emails: GeneratedEmail[];
  total: number;
}

export interface JudgeInsights {
  available: boolean;
  total: number;
  avg_score?: number;
  min_score?: number;
  max_score?: number;
  stddev_score?: number;
  avg_certainty?: number;
  pass_rate?: number;
  latest_at?: string | null;
  judge_model?: string | null;
  score_histogram?: { bucket: number; count: number }[];
  clause_verdicts?: {
    met: number;
    partially_met: number;
    not_met: number;
    not_assessable: number;
  };
  top_clauses_partial?: { clause: string; count: number }[];
  top_clauses_not_met?: { clause: string; count: number }[];
  top_weakness_phrases?: { phrase: string; count: number }[];
  weakness_samples?: string[];
}

export interface ClauseEvaluated {
  clause: string;
  verdict: "met" | "partially_met" | "not_met" | "not_assessable" | string;
  evidence?: string;
}

export interface JudgeGrade {
  grade_id: number;
  email_id: number;
  customer_unique_id: string | null;
  display_name: string;
  subject: string;
  body: string;
  generator_model: string | null;
  judge_model: string | null;
  overall_score: number | null;
  certainty: number | null;
  passed: boolean | null;
  reasoning: string;
  weaknesses: string[];
  clauses_evaluated: ClauseEvaluated[];
  churn_probability: number | null;
  risk_tier: RiskTier;
  graded_at: string | null;
  latency_ms: number | null;
}

export interface JudgeGrades {
  grades: JudgeGrade[];
  total: number;
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
  predictions: () => request<Predictions>("/api/predictions"),
  shap: () => request<ShapData>("/api/shap"),
  runs: () => request<Runs>("/api/runs"),
  emails: (limit = 20) => request<GeneratedEmails>(`/api/emails?limit=${limit}`),
  judgeInsights: () => request<JudgeInsights>("/api/eval/insights"),
  judgeGrades: (limit = 50) => request<JudgeGrades>(`/api/eval/grades?limit=${limit}`),
  inbox: {
    customers: (filter: FilterKey = "all") =>
      request<InboxCustomerList>(`/api/inbox/customers?filter=${filter}`),
    customer: (id: string) =>
      request<InboxCustomerDetail>(
        `/api/inbox/customers/${encodeURIComponent(id)}`,
      ),
  },
};
