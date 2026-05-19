// At-risk customer table (with per-customer SHAP) + recent runs.
import { Fragment, useState } from "react";
import {
  Activity,
  Bell,
  ChevronRight,
  Clock,
  Download,
  ExternalLink,
  GitBranch,
  Mail,
  Play,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Predictions, RunRecord, ShapContribution, ShapCustomer } from "./api";
import { Button, Card, Pill, Skeleton } from "./ui";
import { cx, downloadCsv, openExternal } from "./lib";

const SEGMENTS = ["all", "high-value", "mid-value", "low-value", "single-order"];

function riskColor(p: number): string {
  if (p >= 0.95) return "oklch(0.65 0.22 25)";
  if (p >= 0.9) return "oklch(0.78 0.14 60)";
  return "var(--accent)";
}

// ─── Per-customer SHAP breakdown (expanded row) ──────────────────────────
function ShapBreakdown({ contributions }: { contributions: ShapContribution[] }) {
  const top = [...contributions].sort((a, b) => a.rank - b.rank).slice(0, 6);
  const max = Math.max(...top.map((c) => Math.abs(c.shap_value)), 0.0001);
  return (
    <div className="space-y-1.5 bg-[var(--surface-deep)] px-5 py-3.5">
      <div className="mb-1.5 text-[10.5px] font-medium uppercase tracking-[0.1em] text-[var(--muted)]">
        Why at-risk — top SHAP drivers
      </div>
      {top.map((c) => {
        const pos = c.shap_value >= 0;
        const width = (Math.abs(c.shap_value) / max) * 50;
        return (
          <div
            key={c.feature}
            className="grid grid-cols-[160px_1fr_52px] items-center gap-3"
          >
            <span className="truncate font-mono text-[11px] text-[var(--fg-soft)]">
              {c.feature}
            </span>
            <div className="relative h-2 rounded-full bg-white/[0.04]">
              <div
                className="absolute bottom-0 top-0 w-px bg-[var(--line-strong)]"
                style={{ left: "50%" }}
              />
              <div
                className="absolute bottom-0 top-0 rounded-full"
                style={{
                  width: `${width}%`,
                  background: pos ? "oklch(0.7 0.16 30)" : "var(--accent-2)",
                  ...(pos ? { left: "50%" } : { right: "50%" }),
                }}
              />
            </div>
            <span
              className="text-right font-mono text-[11px] tabular-nums"
              style={{ color: pos ? "oklch(0.76 0.15 35)" : "var(--accent-2)" }}
            >
              {pos ? "+" : ""}
              {c.shap_value.toFixed(2)}
            </span>
          </div>
        );
      })}
      <div className="pt-1 text-[10px] text-[var(--muted)]">
        Warm bars push toward churn, cool bars away — log-odds contribution.
      </div>
    </div>
  );
}

export function AtRiskTable({
  predictions,
  threshold,
  shap,
}: {
  predictions?: Predictions;
  threshold: number;
  shap?: ShapCustomer[];
}) {
  const [filter, setFilter] = useState("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  if (!predictions) return <Skeleton className="h-72 w-full" />;

  const rows = predictions.top_at_risk ?? [];
  const flagged = predictions.predicted_churn ?? 0;
  const shapMap = new Map(
    (shap ?? []).map((c) => [c.customer_unique_id, c.contributions]),
  );

  return (
    <Card
      title="Highest-risk customers"
      subtitle={`${rows.length} of ${flagged.toLocaleString()} flagged · threshold ${threshold} · row → SHAP`}
      icon={<Bell size={14} />}
      pad={false}
      right={
        <>
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<Download size={12} />}
            onClick={() => downloadCsv("at-risk-customers.csv", rows)}
          >
            Export
          </Button>
          {/* AI / LLM connector — wired later */}
          <Button variant="primary" size="sm" leftIcon={<Mail size={12} />}>
            Generate emails
          </Button>
        </>
      }
    >
      <div className="flex flex-wrap gap-1.5 border-b border-[var(--line)] px-5 pb-3 pt-1">
        {SEGMENTS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={cx(
              "h-7 rounded-full border px-3 text-[11.5px] font-medium capitalize tracking-tight transition",
              filter === s
                ? "border-[var(--line-strong)] bg-white/[0.07] text-[var(--fg)]"
                : "border-[var(--line)] bg-transparent text-[var(--muted)] hover:text-[var(--fg-soft)]",
            )}
          >
            {s.replace("-", " ")}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <div className="px-5 py-8 text-center text-[12.5px] text-[var(--muted)]">
          No predictions yet — run batch scoring.
        </div>
      ) : (
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-[10.5px] uppercase tracking-wide text-[var(--muted)]">
              <th className="px-5 py-2.5 text-left font-medium">Customer</th>
              <th className="px-3 py-2.5 text-left font-medium">Segment</th>
              <th className="px-3 py-2.5 text-right font-medium">LTV</th>
              <th className="px-3 py-2.5 text-right font-medium">Last order</th>
              <th className="px-3 py-2.5 text-left font-medium">State</th>
              <th className="px-3 py-2.5 text-right font-medium">Risk</th>
              <th className="w-8 px-5 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const contributions = shapMap.get(r.customer_unique_id);
              const open = expanded === r.customer_unique_id;
              return (
                <Fragment key={r.customer_unique_id}>
                  <tr
                    onClick={() =>
                      contributions &&
                      setExpanded(open ? null : r.customer_unique_id)
                    }
                    className={cx(
                      "border-t border-[var(--line)]",
                      contributions && "cursor-pointer hover:bg-white/[0.02]",
                    )}
                  >
                    <td className="px-5 py-2.5">
                      <div className="flex items-center gap-2.5">
                        <div className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-gradient-to-br from-zinc-700 to-zinc-900 font-mono text-[10px] font-semibold text-zinc-300">
                          {r.customer_unique_id.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div className="font-mono text-[11.5px] text-[var(--fg)]">
                            {r.customer_unique_id.slice(0, 14)}…
                          </div>
                          <div className="font-mono text-[10.5px] text-[var(--muted)]">
                            Olist customer
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-2.5">
                      <Pill tone="neutral">—</Pill>
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono tabular-nums text-[var(--muted)]">
                      —
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono tabular-nums text-[var(--muted)]">
                      —
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[var(--muted)]">—</td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="inline-flex items-center gap-2">
                        <div className="h-1 w-14 overflow-hidden rounded-full bg-white/[0.05]">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${r.churn_probability * 100}%`,
                              background: riskColor(r.churn_probability),
                            }}
                          />
                        </div>
                        <span className="w-12 text-right font-mono font-semibold tabular-nums text-[var(--fg)]">
                          {(r.churn_probability * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-2.5 text-[var(--muted)]">
                      {contributions && (
                        <ChevronRight
                          size={14}
                          className={cx(
                            "transition-transform",
                            open && "rotate-90",
                          )}
                        />
                      )}
                    </td>
                  </tr>
                  {open && contributions && (
                    <tr>
                      <td colSpan={7} className="p-0">
                        <ShapBreakdown contributions={contributions} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      )}
    </Card>
  );
}

export function RecentRunsCard({ runs }: { runs?: RunRecord[] }) {
  return (
    <Card
      title="Recent runs"
      subtitle="Pipeline rebuilds & scoring runs"
      icon={<Clock size={14} />}
      pad={false}
      right={
        <Button
          variant="ghost"
          size="sm"
          rightIcon={<ExternalLink size={12} />}
          onClick={() => openExternal("http://localhost:3000")}
        >
          Dagster
        </Button>
      }
    >
      {!runs ? (
        <div className="p-5">
          <Skeleton className="h-32 w-full" />
        </div>
      ) : runs.length === 0 ? (
        <div className="px-5 py-10 text-center text-[12.5px] text-[var(--muted)]">
          No runs yet — trigger a rebuild or batch scoring.
        </div>
      ) : (
        <table className="w-full text-[12px]">
          <thead>
            <tr className="text-[10.5px] uppercase tracking-wide text-[var(--muted)]">
              <th className="px-5 py-2.5 text-left font-medium">Run</th>
              <th className="px-3 py-2.5 text-left font-medium">Kind</th>
              <th className="px-3 py-2.5 text-left font-medium">Started</th>
              <th className="px-3 py-2.5 text-right font-medium">Duration</th>
              <th className="px-5 py-2.5 text-left font-medium">Detail</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr
                key={r.id}
                className="border-t border-[var(--line)] hover:bg-white/[0.02]"
              >
                <td className="px-5 py-2.5">
                  <div className="flex items-center gap-2">
                    <Pill tone={r.status === "success" ? "success" : "danger"} dot>
                      {r.status}
                    </Pill>
                    <span className="font-mono text-[var(--fg)]">{r.id}</span>
                  </div>
                </td>
                <td className="px-3 py-2.5 font-mono capitalize text-[var(--fg-soft)]">
                  {r.kind}
                </td>
                <td className="px-3 py-2.5 font-mono text-[var(--fg-soft)]">
                  {r.started_at.slice(0, 16).replace("T", " ")}
                </td>
                <td className="px-3 py-2.5 text-right font-mono tabular-nums text-[var(--fg-soft)]">
                  {r.duration_s}s
                </td>
                <td className="px-5 py-2.5 text-[var(--muted)]">{r.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

// ─── Recent runs — dynamic card grid (Runs page) ─────────────────────────
const RUN_KINDS: Record<string, { label: string; icon: LucideIcon }> = {
  rebuild: { label: "dbt rebuild", icon: GitBranch },
  pipeline: { label: "Full pipeline", icon: Play },
  score: { label: "Batch scoring", icon: Zap },
};

// "2h ago" / "3d ago" — relative time from an ISO timestamp.
function relTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const s = Math.max(0, (Date.now() - then) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export function RunCardGrid({ runs }: { runs?: RunRecord[] }) {
  if (!runs)
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-36 w-full" />
        ))}
      </div>
    );

  if (runs.length === 0)
    return (
      <Card title="Recent runs" icon={<Clock size={14} />}>
        <div className="py-10 text-center text-[12.5px] text-[var(--muted)]">
          No runs yet — trigger a rebuild or batch scoring.
        </div>
      </Card>
    );

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {runs.map((r) => {
        const meta = RUN_KINDS[r.kind] ?? { label: r.kind, icon: Activity };
        const Icon = meta.icon;
        const ok = r.status === "success";
        return (
          <section
            key={r.id}
            className="flex flex-col gap-3 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 shadow-[0_1px_0_rgba(255,255,255,0.03)_inset,0_1px_2px_rgba(0,0,0,0.4)] transition-colors hover:border-[var(--line-strong)]"
          >
            <div className="flex items-center gap-2.5">
              <span
                className={cx(
                  "grid h-8 w-8 shrink-0 place-items-center rounded-lg border",
                  ok
                    ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                    : "border-rose-500/25 bg-rose-500/10 text-rose-300",
                )}
              >
                <Icon size={15} />
              </span>
              <div className="min-w-0">
                <div className="truncate text-[12.5px] font-semibold tracking-tight text-[var(--fg)]">
                  {meta.label}
                </div>
                <div className="text-[10.5px] text-[var(--muted)]">
                  {relTime(r.started_at)}
                </div>
              </div>
              <Pill tone={ok ? "success" : "danger"} dot className="ml-auto">
                {r.status}
              </Pill>
            </div>

            <p className="min-h-[34px] text-[12px] leading-relaxed text-[var(--fg-soft)]">
              {r.detail}
            </p>

            <div className="mt-auto flex items-center justify-between border-t border-[var(--line)] pt-2.5 text-[10.5px] text-[var(--muted)]">
              <span className="font-mono">{r.id}</span>
              <span className="font-mono tabular-nums">{r.duration_s}s</span>
            </div>
          </section>
        );
      })}
    </div>
  );
}

// Placeholder — recipient-level email history needs the LLM email pipeline,
// which isn't built yet (serving.generated_emails is empty).
export function EmailOutreachCard() {
  return (
    <Card
      title="Email outreach"
      subtitle="Recipients, generated emails, and eval grades — per retention run"
      icon={<Mail size={14} />}
      right={<Pill tone="neutral">Coming soon</Pill>}
    >
      <div className="py-8 text-center">
        <p className="mx-auto max-w-md text-[12.5px] leading-relaxed text-[var(--muted)]">
          Once the LLM email-generation pipeline ships, each run's outreach
          lands here — which at-risk customers were emailed, the generated
          email, and its eval grade. No emails have been generated yet.
        </p>
      </div>
    </Card>
  );
}
