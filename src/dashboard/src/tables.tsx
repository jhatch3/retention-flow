// At-risk customer table (with per-customer SHAP) + recent runs.
import { Fragment, useEffect, useState } from "react";
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
import { api } from "./api";
import type {
  GeneratedEmail,
  Predictions,
  RunRecord,
  ShapContribution,
  ShapCustomer,
} from "./api";
import { Button, Card, Pill, Skeleton } from "./ui";
import { cx, downloadCsv, openExternal } from "./lib";

function riskColor(p: number): string {
  if (p >= 0.95) return "var(--risk)";
  if (p >= 0.9) return "var(--warn)";
  return "var(--accent)";
}

// ─── Per-customer SHAP breakdown (expanded row) ──────────────────────────
function ShapBreakdown({ contributions }: { contributions: ShapContribution[] }) {
  const top = [...contributions].sort((a, b) => a.rank - b.rank).slice(0, 6);
  const max = Math.max(...top.map((c) => Math.abs(c.shap_value)), 0.0001);
  return (
    <div className="space-y-1.5 bg-[var(--surface-soft)] px-5 py-3.5">
      <div className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
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
            <div className="relative h-2 rounded-full bg-[var(--surface-mute)]">
              <div
                className="absolute bottom-0 top-0 w-px bg-[var(--line-strong)]"
                style={{ left: "50%" }}
              />
              <div
                className="absolute bottom-0 top-0 rounded-full"
                style={{
                  width: `${width}%`,
                  background: pos ? "var(--risk)" : "var(--accent-2)",
                  ...(pos ? { left: "50%" } : { right: "50%" }),
                }}
              />
            </div>
            <span
              className="text-right font-mono text-[11px] tabular-nums"
              style={{ color: pos ? "var(--risk)" : "var(--accent-2)" }}
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
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<Download size={12} />}
          onClick={() => downloadCsv("at-risk-customers.csv", rows)}
        >
          Export
        </Button>
      }
    >
      {rows.length === 0 ? (
        <div className="px-5 py-8 text-center text-[12.5px] text-[var(--muted)]">
          No predictions yet — run batch scoring.
        </div>
      ) : (
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-[10.5px] uppercase tracking-wide text-[var(--muted)]">
              <th className="px-5 py-2.5 text-left font-medium">Customer</th>
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
                      contributions && "cursor-pointer hover:bg-[var(--surface-soft)]",
                    )}
                  >
                    <td className="px-5 py-2.5">
                      <div className="flex items-center gap-2.5">
                        <div className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-[var(--surface-mute)] font-mono text-[10px] font-semibold text-[var(--fg-soft)]">
                          {(r.display_name ?? r.customer_unique_id)
                            .split(" ")
                            .slice(0, 2)
                            .map((s) => s[0])
                            .join("")
                            .slice(0, 2)
                            .toUpperCase()}
                        </div>
                        <div>
                          <div className="text-[12.5px] font-medium text-[var(--fg)]">
                            {r.display_name ?? `Customer ${r.customer_unique_id.slice(0, 8).toUpperCase()}`}
                          </div>
                          <div className="font-mono text-[10.5px] text-[var(--muted)]">
                            {r.customer_unique_id.slice(0, 14)}…
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="inline-flex items-center gap-2">
                        <div className="h-1 w-24 overflow-hidden rounded-full bg-[var(--surface-mute)]">
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
                      <td colSpan={3} className="p-0">
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
                className="border-t border-[var(--line)] hover:bg-[var(--surface-soft)]"
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
            className="flex flex-col gap-3 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 shadow-[0_1px_2px_rgba(28,26,23,0.04)] transition-colors hover:border-[var(--line-strong)]"
          >
            <div className="flex items-center gap-2.5">
              <span
                className={cx(
                  "grid h-8 w-8 shrink-0 place-items-center rounded-lg border",
                  ok
                    ? "border-[color-mix(in_oklch,var(--ok)_28%,transparent)] bg-[var(--ok-bg)] text-[var(--ok)]"
                    : "border-[color-mix(in_oklch,var(--risk)_28%,transparent)] bg-[var(--risk-bg)] text-[var(--risk)]",
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

function tierTone(tier: string) {
  return tier === "crit"
    ? "danger"
    : tier === "high"
      ? "warn"
      : tier === "med"
        ? "accent"
        : "neutral";
}

function emailRelTime(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const s = Math.max(0, (Date.now() - then) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export function EmailOutreachCard() {
  const [emails, setEmails] = useState<GeneratedEmail[]>();
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string>();

  useEffect(() => {
    api
      .emails(20)
      .then((d) => {
        setEmails(d.emails);
        setTotal(d.total);
      })
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <Card
      title="Email outreach"
      subtitle={
        total > 0
          ? `${total.toLocaleString()} retention emails generated · serving.generated_emails`
          : "LLM-drafted retention emails — populated by the pipeline's email step"
      }
      icon={<Mail size={14} />}
      pad={false}
    >
      {error ? (
        <div className="px-5 py-8 text-center text-[12.5px] text-[var(--risk)]">
          {error}
        </div>
      ) : !emails ? (
        <div className="p-5">
          <Skeleton className="h-32 w-full" />
        </div>
      ) : emails.length === 0 ? (
        <div className="py-10 text-center">
          <p className="mx-auto max-w-md text-[12.5px] leading-relaxed text-[var(--muted)]">
            No emails have been generated yet. Run the pipeline with{" "}
            <span className="font-medium text-[var(--fg-soft)]">
              Generate retention emails
            </span>{" "}
            enabled and drafts will land here.
          </p>
        </div>
      ) : (
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-[10.5px] uppercase tracking-wide text-[var(--muted)]">
              <th className="px-5 py-2.5 text-left font-medium">Customer</th>
              <th className="px-3 py-2.5 text-left font-medium">Risk</th>
              <th className="px-3 py-2.5 text-left font-medium">Subject</th>
              <th className="px-3 py-2.5 text-left font-medium">Model</th>
              <th className="px-3 py-2.5 text-left font-medium">Judge</th>
              <th className="px-5 py-2.5 text-right font-medium">Generated</th>
            </tr>
          </thead>
          <tbody>
            {emails.map((e) => (
              <tr
                key={e.id}
                className="border-t border-[var(--line)] hover:bg-[var(--surface-soft)]"
              >
                <td className="px-5 py-2.5">
                  <div className="text-[12px] font-medium text-[var(--fg)]">
                    {e.display_name}
                  </div>
                  <div className="font-mono text-[10.5px] text-[var(--muted)]">
                    {e.customer_unique_id?.slice(0, 12) ?? "—"}…
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <Pill tone={tierTone(e.risk_tier)}>
                    {e.churn_probability != null
                      ? `${(e.churn_probability * 100).toFixed(0)}%`
                      : e.risk_tier}
                  </Pill>
                </td>
                <td className="max-w-[320px] truncate px-3 py-2.5 text-[var(--fg-soft)]">
                  {e.subject || "—"}
                </td>
                <td className="px-3 py-2.5 font-mono text-[11px] text-[var(--muted)]">
                  {e.model ?? "—"}
                </td>
                <td className="px-3 py-2.5">
                  {e.judge_score != null ? (
                    <span
                      className={cx(
                        "font-mono text-[11.5px] font-semibold tabular-nums",
                        e.judge_passed
                          ? "text-[var(--ok)]"
                          : "text-[var(--warn)]",
                      )}
                    >
                      {e.judge_score.toFixed(1)} / 10
                    </span>
                  ) : (
                    <span className="font-mono text-[11px] text-[var(--muted)]">
                      not graded
                    </span>
                  )}
                </td>
                <td className="px-5 py-2.5 text-right font-mono text-[11px] text-[var(--muted)]">
                  {emailRelTime(e.generated_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
