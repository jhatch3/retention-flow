// Chart components on Recharts — tuned palette + custom tooltip.
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { featureCategory } from "./lib";
import type { ChurnPoint } from "./lib";

const TICK = { fill: "var(--muted)", fontSize: 10 };

interface TipProps {
  active?: boolean;
  payload?: {
    value: number;
    name?: string;
    color?: string;
    dataKey?: string | number;
  }[];
  label?: string | number;
  valueFormat?: (v: number, k?: string | number) => string;
  labelFormat?: (l: string | number) => string;
}

export function ChartTooltip({
  active,
  payload,
  label,
  valueFormat = (v) => String(v),
  labelFormat,
}: TipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-[var(--line-strong)] bg-[var(--surface-strong)] px-3 py-2 shadow-xl backdrop-blur-md">
      {label !== undefined && (
        <div className="mb-1 text-[10.5px] font-medium uppercase tracking-wide text-[var(--muted)]">
          {labelFormat ? labelFormat(label) : label}
        </div>
      )}
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2 text-[12px]">
          <span className="h-2 w-2 rounded-sm" style={{ background: p.color }} />
          <span className="text-[var(--fg-soft)]">{p.name}</span>
          <span className="ml-auto font-mono font-semibold tabular-nums text-[var(--fg)]">
            {valueFormat(p.value, p.dataKey)}
          </span>
        </div>
      ))}
    </div>
  );
}

const tip =
  (extra: Omit<TipProps, "active" | "payload" | "label">) =>
  (props: unknown) =>
    <ChartTooltip {...(props as TipProps)} {...extra} />;

// ─── Hero churn-rate chart ───────────────────────────────────────────────
export function ChurnTimeSeries({
  data,
  height = 240,
}: {
  data: ChurnPoint[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 12, right: 8, left: -12, bottom: 0 }}>
        <defs>
          <linearGradient id="g-churn" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.4} />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--line)" strokeDasharray="2 4" vertical={false} />
        <XAxis
          dataKey="label"
          tick={TICK}
          tickLine={false}
          axisLine={false}
          interval={Math.floor(data.length / 6)}
        />
        <YAxis
          tick={TICK}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          domain={["dataMin - 0.005", "dataMax + 0.005"]}
        />
        <Tooltip
          content={tip({
            valueFormat: (v, k) =>
              k === "rate" ? `${(v * 100).toFixed(2)}%` : v.toLocaleString(),
          })}
          cursor={{ stroke: "var(--line-strong)", strokeWidth: 1 }}
        />
        <Area
          type="monotone"
          dataKey="rate"
          name="Churn rate"
          stroke="var(--accent)"
          strokeWidth={1.75}
          fill="url(#g-churn)"
          dot={false}
          activeDot={{ r: 4 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ─── Model performance over versions ─────────────────────────────────────
export function ModelPerfChart({
  data,
  height = 200,
}: {
  data: { v: string; roc_auc: number; pr_auc: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 12, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke="var(--line)" strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="v" tick={TICK} tickLine={false} axisLine={false} />
        <YAxis
          tick={TICK}
          tickLine={false}
          axisLine={false}
          domain={[0.7, 0.9]}
          tickFormatter={(v: number) => v.toFixed(2)}
        />
        <Tooltip
          content={tip({
            valueFormat: (v) => v.toFixed(3),
            labelFormat: (l) => `${l} · trained`,
          })}
          cursor={{ stroke: "var(--line-strong)" }}
        />
        <Line
          type="monotone"
          dataKey="roc_auc"
          name="ROC-AUC"
          stroke="var(--accent)"
          strokeWidth={1.75}
          dot={{ r: 2.5, fill: "var(--accent)" }}
          activeDot={{ r: 4 }}
        />
        <Line
          type="monotone"
          dataKey="pr_auc"
          name="PR-AUC"
          stroke="var(--accent-2)"
          strokeWidth={1.75}
          strokeDasharray="3 3"
          dot={{ r: 2.5, fill: "var(--accent-2)" }}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ─── Risk histogram ──────────────────────────────────────────────────────
export function RiskHistogram({
  data,
  threshold = 0.42,
  height = 180,
}: {
  data: { bucket: number; count: number }[];
  threshold?: number;
  height?: number;
}) {
  const cutoff = Math.ceil(threshold * 10) + 1;
  const enriched = data.map((d) => ({
    band: `${(d.bucket - 1) * 10}–${d.bucket * 10}`,
    count: d.count,
    high: d.bucket >= cutoff,
  }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={enriched} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
        <CartesianGrid stroke="var(--line)" strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="band" tick={TICK} tickLine={false} axisLine={false} />
        <YAxis
          tick={TICK}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v))}
        />
        <Tooltip
          content={tip({
            valueFormat: (v) => v.toLocaleString(),
            labelFormat: (l) => `${l}% churn probability`,
          })}
          cursor={{ fill: "rgba(255,255,255,0.03)" }}
        />
        <Bar dataKey="count" radius={[3, 3, 0, 0]}>
          {enriched.map((d, i) => (
            <Cell
              key={i}
              fill={
                d.high
                  ? "var(--accent)"
                  : "color-mix(in oklch, var(--accent) 30%, transparent)"
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── Feature importance bars (horizontal, custom-drawn) ──────────────────
const CAT_COLOR: Record<string, string> = {
  recency: "var(--accent)",
  frequency: "var(--accent-2)",
  monetary: "oklch(0.78 0.14 145)",
  sentiment: "oklch(0.76 0.13 60)",
  fulfillment: "oklch(0.7 0.16 30)",
  geographic: "oklch(0.68 0.06 250)",
};

export function FeatureImportanceList({
  features,
}: {
  features: { feature: string; importance: number }[];
}) {
  const max = Math.max(...features.map((f) => f.importance), 0.0001);
  return (
    <div className="space-y-2">
      {features.map((f) => {
        const category = featureCategory(f.feature);
        return (
          <div
            key={f.feature}
            className="grid grid-cols-[1fr_auto] items-center gap-3"
          >
            <div>
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="truncate font-mono text-[11.5px] text-[var(--fg-soft)]">
                  {f.feature}
                </span>
                <span className="font-mono text-[10.5px] uppercase tracking-wide text-[var(--muted)]">
                  {category}
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.04]">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${(f.importance / max) * 100}%`,
                    background: CAT_COLOR[category] ?? "var(--accent)",
                  }}
                />
              </div>
            </div>
            <span className="w-12 text-right font-mono text-[12px] tabular-nums text-[var(--fg)]">
              {f.importance.toFixed(3)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Segment churn rate (small horizontal bars) ──────────────────────────
export function SegmentChurn({
  segments,
}: {
  segments: { segment: string; rows: number; churn_rate: number }[];
}) {
  const max = Math.max(...segments.map((s) => s.churn_rate), 0.0001);
  return (
    <div className="space-y-3">
      {segments.map((s) => (
        <div key={s.segment}>
          <div className="mb-1.5 flex items-baseline justify-between gap-2">
            <div className="flex items-baseline gap-2">
              <span className="text-[12.5px] font-medium capitalize text-[var(--fg)]">
                {s.segment.replace("-", " ")}
              </span>
              <span className="font-mono text-[11px] tabular-nums text-[var(--muted)]">
                {s.rows.toLocaleString()}
              </span>
            </div>
            <span className="font-mono text-[12px] font-semibold tabular-nums text-[var(--fg)]">
              {(s.churn_rate * 100).toFixed(1)}%
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.04]">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${(s.churn_rate / max) * 100}%`,
                background:
                  s.churn_rate > 0.5
                    ? "oklch(0.7 0.16 30)"
                    : s.churn_rate > 0.35
                      ? "oklch(0.76 0.13 60)"
                      : "var(--accent)",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
