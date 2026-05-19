// Overview cards: KPI row, churn hero, pipeline, warehouse, model registry,
// feature importance.
import { useMemo, useState } from "react";
import { Boxes, Database, ExternalLink, GitBranch, Sparkles } from "lucide-react";
import type {
  FeatureImportance,
  ModelRegistry,
  PipelineStatus,
  Predictions,
  ShapData,
  WarehouseData,
} from "./api";
import { Button, Card, Delta, Kpi, MetricCell, Pill, Skeleton, Stat2 } from "./ui";
import {
  ChurnTimeSeries,
  FeatureImportanceList,
  ModelPerfChart,
  SegmentChurn,
} from "./charts";
import { churnSeries, cx, openExternal, sparkline } from "./lib";

const m3 = (x?: number | null) => (x != null ? x.toFixed(3) : "—");

// ─── KPI row ─────────────────────────────────────────────────────────────
export function KpiRow({
  data,
  models,
  pipeline,
}: {
  data?: WarehouseData;
  models?: ModelRegistry;
  pipeline?: PipelineStatus;
}) {
  const cm = models?.champion_metrics;
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Kpi
        label="Customers in gold"
        value={data ? data.gold_rows.toLocaleString() : "—"}
        delta={2.1}
        sparkData={sparkline(1, 1.5)}
        footnote="analytics.customer_features"
      />
      <Kpi
        label="Churn rate (180d)"
        value={data ? `${(data.gold_churn_rate * 100).toFixed(1)}%` : "—"}
        delta={-1.4}
        positiveIsGood={false}
        sparkData={sparkline(2, -1)}
        sparkColor="oklch(0.78 0.14 60)"
        footnote="vs. 30d trailing baseline"
      />
      <Kpi
        label="Champion ROC-AUC"
        value={m3(cm?.roc_auc)}
        delta={0.7}
        sparkData={sparkline(3, 1)}
        sparkColor="oklch(0.78 0.14 145)"
        footnote={
          models?.champion_version
            ? `churn-xgboost · v${models.champion_version}`
            : "no champion"
        }
      />
      <Kpi
        label="dbt tests"
        value={
          pipeline?.available
            ? `${pipeline.tests?.pass ?? 0}/${pipeline.tests_total}`
            : "—"
        }
        delta={0}
        deltaSuffix=""
        sparkData={sparkline(4, 0.5)}
        sparkColor="oklch(0.78 0.14 145)"
        footnote={`${pipeline?.tests?.warn ?? 0} warning · 0 failing`}
      />
    </div>
  );
}

// ─── Hero churn chart ────────────────────────────────────────────────────
const RANGES: Record<string, number> = { "7d": -7, "30d": -30, "90d": -90, "12m": -90 };

export function ChurnHero({
  data,
  models,
  predictions,
}: {
  data?: WarehouseData;
  models?: ModelRegistry;
  predictions?: Predictions;
}) {
  const [range, setRange] = useState("30d");
  const full = useMemo(
    () => (data ? churnSeries(data.gold_churn_rate, data.gold_rows) : []),
    [data],
  );
  if (!data) return <Skeleton className="h-[420px] w-full" />;

  const series = full.slice(RANGES[range]);
  const latest = series[series.length - 1];
  const first = series[0];
  const delta = first ? ((latest.rate - first.rate) / first.rate) * 100 : 0;
  const champion = models?.versions.find((v) => v.is_champion);
  const threshold = champion?.decision_threshold ?? "—";

  return (
    <Card
      title="Customer churn"
      subtitle="180-day observation horizon · scored nightly"
      className="h-full"
      pad={false}
      right={
        <div className="flex items-center gap-1 rounded-lg border border-[var(--line)] bg-white/[0.02] p-0.5">
          {Object.keys(RANGES).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={cx(
                "rounded-md px-2 py-0.5 font-mono text-[11px] transition",
                range === r
                  ? "bg-white/[0.07] text-[var(--fg)]"
                  : "text-[var(--muted)] hover:text-[var(--fg-soft)]",
              )}
            >
              {r}
            </button>
          ))}
        </div>
      }
    >
      <div className="flex flex-wrap items-end gap-8 px-5 pt-4">
        <div>
          <div className="text-[10.5px] font-medium uppercase tracking-[0.1em] text-[var(--muted)]">
            Current
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-[32px] font-semibold leading-none tracking-tight tabular-nums text-[var(--fg)]">
              {(latest.rate * 100).toFixed(1)}
              <span className="text-[var(--muted)]">%</span>
            </span>
            <Delta value={delta} positiveIsGood={false} />
          </div>
          <div className="mt-1 font-mono text-[11px] text-[var(--muted)]">
            {latest.predicted_churn.toLocaleString()} predicted churners of{" "}
            {latest.scored.toLocaleString()}
          </div>
        </div>
        <div className="h-10 w-px bg-[var(--line)]" />
        <Stat2
          label="Predicted churn"
          value={
            predictions?.scored
              ? (predictions.predicted_churn ?? 0).toLocaleString()
              : "—"
          }
        />
        <Stat2
          label="Avg probability"
          value={
            predictions?.scored
              ? (predictions.avg_probability ?? 0).toFixed(3)
              : "—"
          }
          mono
        />
        <Stat2 label="Threshold" value={String(threshold)} mono />
        <Stat2
          label="Last scored"
          value={predictions?.scored ? "recent" : "never"}
          muted
        />
      </div>
      <div className="px-2 pb-4 pt-4">
        <ChurnTimeSeries data={series} />
      </div>
    </Card>
  );
}

// ─── Pipeline card ───────────────────────────────────────────────────────
const LAYER_LABEL: Record<string, string> = {
  staging: "Staging",
  intermediate: "Intermediate",
  mart: "Mart · gold",
};

export function PipelineCard({ pipeline }: { pipeline?: PipelineStatus }) {
  if (!pipeline) return <Skeleton className="h-[440px] w-full" />;

  const grouped: Record<string, PipelineStatus["models"]> = {
    staging: [],
    intermediate: [],
    mart: [],
  };
  for (const m of pipeline.models ?? []) {
    const layer = m.name.startsWith("stg_")
      ? "staging"
      : m.name.startsWith("int_")
        ? "intermediate"
        : "mart";
    grouped[layer]!.push(m);
  }
  const ok = pipeline.available;

  return (
    <Card
      title="Pipeline"
      subtitle="dbt · medallion build"
      className="h-full"
      icon={<GitBranch size={14} />}
      right={
        <>
          <Pill tone={ok ? "success" : "neutral"} dot>
            {ok ? "healthy" : "no run"}
          </Pill>
        </>
      }
    >
      <div className="mb-4 flex flex-wrap gap-6 border-b border-[var(--line)] pb-4">
        <Stat2
          label="Models built"
          value={ok ? `${pipeline.models_ok}/${pipeline.model_count}` : "—"}
        />
        <Stat2
          label="Tests passed"
          value={ok ? `${pipeline.tests?.pass ?? 0}/${pipeline.tests_total}` : "—"}
        />
        <Stat2 label="Warnings" value={String(pipeline.tests?.warn ?? 0)} />
        <Stat2 label="Failures" value={String(pipeline.tests?.fail ?? 0)} />
      </div>

      <div className="space-y-4">
        {Object.entries(grouped).map(([layer, items]) => (
          <div key={layer}>
            <div className="mb-1.5 flex items-baseline justify-between">
              <span className="text-[10.5px] font-medium uppercase tracking-[0.1em] text-[var(--muted)]">
                {LAYER_LABEL[layer]}
              </span>
              <span className="font-mono text-[10.5px] text-[var(--muted)]">
                {items!.length} models
              </span>
            </div>
            <div className="space-y-0.5">
              {items!.map((m) => (
                <div
                  key={m.name}
                  className="flex items-center gap-2 rounded-md px-2 py-1 hover:bg-white/[0.025]"
                >
                  <span
                    className={cx(
                      "h-1.5 w-1.5 shrink-0 rounded-full",
                      m.status === "success"
                        ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.4)]"
                        : m.status === "warning"
                          ? "bg-amber-400"
                          : "bg-rose-400",
                    )}
                  />
                  <span className="flex-1 truncate font-mono text-[11.5px] text-[var(--fg-soft)]">
                    {m.name}
                  </span>
                  <span className="font-mono text-[10.5px] tabular-nums text-[var(--muted)]">
                    {m.execution_time.toFixed(1)}s
                  </span>
                </div>
              ))}
              {items!.length === 0 && (
                <div className="px-2 py-1 text-[11px] text-[var(--muted)]">—</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ─── Warehouse card ──────────────────────────────────────────────────────
const SPLIT_COLORS = ["var(--accent)", "var(--accent-2)", "oklch(0.5 0.04 260)"];

export function WarehouseCard({ data }: { data?: WarehouseData }) {
  if (!data) return <Skeleton className="h-[440px] w-full" />;
  const splits = Object.entries(data.splits);
  const total = splits.reduce((a, [, v]) => a + v, 0) || 1;

  return (
    <Card
      title="Warehouse"
      subtitle="Postgres · analytics schema"
      icon={<Database size={14} />}
      right={<span className="font-mono">analytics.customer_features</span>}
    >
      <div className="mb-5 flex flex-wrap gap-6 border-b border-[var(--line)] pb-5">
        <Stat2 label="Gold rows" value={data.gold_rows.toLocaleString()} />
        <Stat2 label="Raw orders" value={data.raw_orders.toLocaleString()} />
        <Stat2 label="Synthetic" value={data.synthetic_orders.toLocaleString()} />
      </div>

      <div className="mb-5">
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-[10.5px] font-medium uppercase tracking-[0.1em] text-[var(--muted)]">
            Train · test · validation split
          </span>
          <span className="font-mono text-[10.5px] text-[var(--muted)]">70 / 15 / 15</span>
        </div>
        <div className="flex h-2.5 w-full overflow-hidden rounded-full border border-[var(--line)] bg-white/[0.02]">
          {splits.map(([name, v], i) => (
            <div
              key={name}
              title={`${name}: ${v.toLocaleString()}`}
              style={{ width: `${(v / total) * 100}%`, background: SPLIT_COLORS[i] }}
            />
          ))}
        </div>
        <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 font-mono text-[11px]">
          {splits.map(([name, v], i) => (
            <div key={name} className="flex items-center gap-1.5">
              <span
                className="h-2 w-2 rounded-sm"
                style={{ background: SPLIT_COLORS[i] }}
              />
              <span className="text-[var(--fg-soft)]">{name}</span>
              <span className="tabular-nums text-[var(--muted)]">
                {v.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-3 text-[10.5px] font-medium uppercase tracking-[0.1em] text-[var(--muted)]">
          Churn rate by segment
        </div>
        <SegmentChurn segments={data.segments} />
      </div>
    </Card>
  );
}

// ─── Model registry card ─────────────────────────────────────────────────
export function ModelRegistryCard({ models }: { models?: ModelRegistry }) {
  if (!models) return <Skeleton className="h-[440px] w-full" />;
  const cm = models.champion_metrics;
  const perf = [...models.versions]
    .reverse()
    .map((v) => ({
      v: `v${v.version}`,
      roc_auc: v.roc_auc ?? 0,
      pr_auc: v.pr_auc ?? 0,
    }));

  return (
    <Card
      title="Model registry"
      subtitle={`MLflow · ${models.experiment}`}
      icon={<Boxes size={14} />}
      right={
        <Button
          variant="ghost"
          size="sm"
          rightIcon={<ExternalLink size={12} />}
          onClick={() => openExternal("http://localhost:5000")}
        >
          MLflow
        </Button>
      }
    >
      <div className="mb-5 grid grid-cols-3 gap-4 border-b border-[var(--line)] pb-5 md:grid-cols-6">
        <MetricCell label="ROC-AUC" value={m3(cm.roc_auc)} primary />
        <MetricCell label="PR-AUC" value={m3(cm.pr_auc)} />
        <MetricCell label="Precision" value={m3(cm.precision)} />
        <MetricCell label="Recall" value={m3(cm.recall)} />
        <MetricCell label="F1" value={m3(cm.f1)} />
        <MetricCell label="Brier" value={m3(cm.brier)} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.05fr_1fr]">
        <div>
          <div className="mb-2 flex items-baseline justify-between">
            <span className="text-[10.5px] font-medium uppercase tracking-[0.1em] text-[var(--muted)]">
              Performance over versions
            </span>
            <div className="flex items-center gap-3 font-mono text-[10.5px]">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-sm bg-[var(--accent)]" /> ROC-AUC
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-sm bg-[var(--accent-2)]" /> PR-AUC
              </span>
            </div>
          </div>
          <ModelPerfChart data={perf} />
        </div>

        <div>
          <div className="mb-2 text-[10.5px] font-medium uppercase tracking-[0.1em] text-[var(--muted)]">
            Versions
          </div>
          <div className="overflow-hidden rounded-lg border border-[var(--line)]">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="bg-white/[0.02] text-[10.5px] uppercase tracking-wide text-[var(--muted)]">
                  <th className="px-3 py-2 text-left font-medium">Version</th>
                  <th className="px-3 py-2 text-right font-medium">ROC</th>
                  <th className="px-3 py-2 text-right font-medium">Thresh.</th>
                  <th className="px-3 py-2 text-right font-medium">Stage</th>
                </tr>
              </thead>
              <tbody>
                {models.versions.map((v) => (
                  <tr
                    key={v.version}
                    className="border-t border-[var(--line)] hover:bg-white/[0.02]"
                  >
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[var(--fg)]">v{v.version}</span>
                        {v.is_champion && (
                          <Pill tone="accent" dot>
                            champion
                          </Pill>
                        )}
                      </div>
                      <div className="mt-0.5 font-mono text-[10.5px] text-[var(--muted)]">
                        {v.created_at.slice(0, 10)}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-[var(--fg-soft)]">
                      {v.roc_auc?.toFixed(3) ?? "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-[var(--fg-soft)]">
                      {v.decision_threshold ?? "—"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span
                        className={cx(
                          "font-mono text-[11px]",
                          v.is_champion ? "text-emerald-300" : "text-[var(--muted)]",
                        )}
                      >
                        {v.is_champion ? "Production" : "Archived"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ─── Feature importance card ─────────────────────────────────────────────
export function ShapCard({ shap }: { shap?: ShapData }) {
  return (
    <Card
      title="SHAP attribution"
      subtitle="Champion · mean |SHAP| over the scored gold table"
      icon={<Sparkles size={14} />}
    >
      {!shap ? (
        <Skeleton className="h-72 w-full" />
      ) : !shap.available ? (
        <p className="text-sm text-[var(--muted)]">
          No SHAP yet — run batch scoring to compute attributions.
        </p>
      ) : (
        <FeatureImportanceList
          features={shap.global.features.map((f) => ({
            feature: f.feature,
            importance: f.mean_abs_shap,
          }))}
        />
      )}
    </Card>
  );
}

export function FeatureImportanceCard({
  fi,
  championVersion,
}: {
  fi?: FeatureImportance;
  championVersion?: string | null;
}) {
  return (
    <Card
      title="Feature importance"
      subtitle={`Champion · v${championVersion ?? "—"} · gain`}
      icon={<Sparkles size={14} />}
    >
      {fi ? (
        <FeatureImportanceList features={fi.features} />
      ) : (
        <Skeleton className="h-72 w-full" />
      )}
    </Card>
  );
}
