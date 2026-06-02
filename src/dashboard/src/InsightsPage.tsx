// Judge Insights — what the adversarial LLM-as-judge thought about every
// retention email. Aggregate at the top (score histogram, clause verdicts,
// recurring weaknesses), per-email grade cards below.
import { useEffect, useMemo, useState } from "react";
import { Gavel, Search } from "lucide-react";
import { api } from "./api";
import type {
  ClauseEvaluated,
  JudgeGrade,
  JudgeInsights as JudgeInsightsT,
} from "./api";
import { PageHeader } from "./shell";
import { Card, MetricCell, Pill, Skeleton, Stat2 } from "./ui";
import { cx } from "./lib";

const VERDICT_TONE: Record<string, "success" | "warn" | "danger" | "neutral"> = {
  met: "success",
  partially_met: "warn",
  not_met: "danger",
  not_assessable: "neutral",
};

const VERDICT_COLOR: Record<string, string> = {
  met: "var(--ok)",
  partially_met: "var(--warn)",
  not_met: "var(--risk)",
  not_assessable: "var(--muted)",
};

const VERDICT_LABEL: Record<string, string> = {
  met: "Met",
  partially_met: "Partial",
  not_met: "Not met",
  not_assessable: "N/A",
};

export function InsightsPage() {
  const [insights, setInsights] = useState<JudgeInsightsT>();
  const [grades, setGrades] = useState<JudgeGrade[]>();
  const [error, setError] = useState<string>();
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    api.judgeInsights().then(setInsights).catch((e) => setError(String(e)));
    api
      .judgeGrades(100)
      .then((d) => setGrades(d.grades))
      .catch((e) => setError(String(e)));
  }, []);

  const filtered = useMemo(() => {
    if (!grades) return [];
    const q = search.trim().toLowerCase();
    if (!q) return grades;
    return grades.filter(
      (g) =>
        g.display_name.toLowerCase().includes(q) ||
        g.subject.toLowerCase().includes(q) ||
        g.reasoning.toLowerCase().includes(q) ||
        g.weaknesses.some((w) => w.toLowerCase().includes(q)),
    );
  }, [grades, search]);

  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Judge insights"
        description="What the adversarial LLM-as-judge thought about every retention email — scores, clause verdicts, recurring weaknesses, and per-email reasoning."
        meta={
          insights?.latest_at && (
            <span className="font-mono text-[11px] text-[var(--muted)]">
              graded {new Date(insights.latest_at).toLocaleString()}
            </span>
          )
        }
      />

      {error && (
        <div className="mb-6 rounded-lg border border-[color-mix(in_oklch,var(--risk)_30%,transparent)] bg-[var(--risk-bg)] px-4 py-3 text-[12.5px] text-[var(--risk)]">
          {error}
        </div>
      )}

      {!insights ? (
        <Skeleton className="mb-6 h-[260px] w-full" />
      ) : !insights.available ? (
        <Card title="No grades yet" icon={<Gavel size={14} />}>
          <div className="py-10 text-center">
            <p className="mx-auto max-w-md text-[12.5px] leading-relaxed text-[var(--muted)]">
              The LLM-as-judge hasn&apos;t scored any emails yet. Run the pipeline
              with{" "}
              <span className="font-medium text-[var(--fg-soft)]">
                Generate retention emails
              </span>{" "}
              enabled — every draft is graded by the adversarial judge, and the
              results land here.
            </p>
          </div>
        </Card>
      ) : (
        <div className="space-y-6">
          <KpiStrip insights={insights} />

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.05fr_1fr]">
            <ScoreHistogram insights={insights} />
            <ClauseVerdicts insights={insights} />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <TopClauses
              title="Most-missed clauses"
              subtitle="What the judge marked as 'not met'"
              items={insights.top_clauses_not_met ?? []}
              tone="danger"
            />
            <TopClauses
              title="Partially-met clauses"
              subtitle="Judge marked these as partially met"
              items={insights.top_clauses_partial ?? []}
              tone="warn"
            />
          </div>

          <WeaknessCluster insights={insights} />
        </div>
      )}

      {/* Per-email grades */}
      <div className="mt-8">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
              Per-email grades
            </div>
            <h3 className="mt-0.5 text-[16px] font-semibold tracking-tight text-[var(--fg)]">
              Reasoning behind each judge call
            </h3>
          </div>
          <label className="flex h-8 items-center gap-2 rounded-md border border-[var(--line)] bg-[var(--surface)] px-2.5">
            <Search size={13} className="text-[var(--muted)]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search reasoning, name, subject…"
              className="w-[260px] bg-transparent text-[12.5px] text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none"
            />
          </label>
        </div>

        {!grades ? (
          <div className="space-y-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : filtered.length === 0 ? (
          <Card title="No matching grades">
            <div className="py-6 text-center text-[12.5px] text-[var(--muted)]">
              {search
                ? "No grades match this search."
                : "No emails have been graded yet."}
            </div>
          </Card>
        ) : (
          <div className="space-y-3">
            {filtered.map((g) => (
              <GradeCard
                key={g.grade_id}
                grade={g}
                expanded={expanded === g.grade_id}
                onToggle={() =>
                  setExpanded((prev) => (prev === g.grade_id ? null : g.grade_id))
                }
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

export default InsightsPage;

// ── KPI strip ───────────────────────────────────────────────────────────────
function KpiStrip({ insights }: { insights: JudgeInsightsT }) {
  const total = insights.total ?? 0;
  const avgScore = insights.avg_score ?? 0;
  const passRate = (insights.pass_rate ?? 0) * 100;
  const certainty = (insights.avg_certainty ?? 0) * 100;
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Card pad>
        <div className="font-mono text-[10px] uppercase tracking-[0.1em] text-[var(--muted)]">
          Emails graded
        </div>
        <div className="mt-2 text-[28px] font-semibold leading-none tracking-tight tabular-nums text-[var(--fg)]">
          {total.toLocaleString()}
        </div>
        <div className="mt-1.5 text-[11px] text-[var(--muted)]">
          judge · {insights.judge_model ?? "—"}
        </div>
      </Card>
      <Card pad>
        <div className="font-mono text-[10px] uppercase tracking-[0.1em] text-[var(--muted)]">
          Mean score
        </div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-[28px] font-semibold leading-none tracking-tight tabular-nums text-[var(--fg)]">
            {avgScore.toFixed(2)}
          </span>
          <span className="text-[12px] font-mono text-[var(--muted)]">/ 10</span>
        </div>
        <div className="mt-1.5 text-[11px] text-[var(--muted)]">
          range {insights.min_score?.toFixed(1)} – {insights.max_score?.toFixed(1)} ·
          σ {insights.stddev_score?.toFixed(2)}
        </div>
      </Card>
      <Card pad>
        <div className="font-mono text-[10px] uppercase tracking-[0.1em] text-[var(--muted)]">
          Pass rate (≥ 7)
        </div>
        <div className="mt-2 text-[28px] font-semibold leading-none tracking-tight tabular-nums text-[var(--fg)]">
          {passRate.toFixed(0)}%
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface-mute)]">
          <div
            className="h-full rounded-full bg-[var(--ok)]"
            style={{ width: `${passRate}%` }}
          />
        </div>
      </Card>
      <Card pad>
        <div className="font-mono text-[10px] uppercase tracking-[0.1em] text-[var(--muted)]">
          Mean certainty
        </div>
        <div className="mt-2 text-[28px] font-semibold leading-none tracking-tight tabular-nums text-[var(--fg)]">
          {certainty.toFixed(0)}%
        </div>
        <div className="mt-1.5 text-[11px] text-[var(--muted)]">
          how confident the judge was
        </div>
      </Card>
    </div>
  );
}

// ── Score histogram ─────────────────────────────────────────────────────────
function ScoreHistogram({ insights }: { insights: JudgeInsightsT }) {
  const hist = insights.score_histogram ?? [];
  const max = Math.max(...hist.map((h) => h.count), 1);
  // Pad to a full 1–10 range so empty buckets render as a baseline.
  const buckets = Array.from({ length: 10 }, (_, i) => {
    const idx = i + 1;
    const row = hist.find((h) => h.bucket === idx);
    return { bucket: idx, count: row?.count ?? 0 };
  });

  return (
    <Card title="Score distribution" subtitle="1 — 10, the judge's score per email">
      <div className="flex h-[200px] items-end gap-2">
        {buckets.map((b) => {
          const h = (b.count / max) * 100;
          const isPass = b.bucket >= 7;
          return (
            <div key={b.bucket} className="flex flex-1 flex-col items-center gap-1.5">
              <div className="font-mono text-[10.5px] tabular-nums text-[var(--muted)]">
                {b.count > 0 ? b.count : ""}
              </div>
              <div
                className="w-full rounded-md transition-all"
                style={{
                  height: `${Math.max(h, b.count > 0 ? 3 : 1)}%`,
                  background: isPass
                    ? "color-mix(in oklch, var(--ok) 80%, transparent)"
                    : "color-mix(in oklch, var(--accent) 70%, transparent)",
                }}
                title={`${b.bucket}–${b.bucket + 1}: ${b.count}`}
              />
              <div className="font-mono text-[10.5px] tabular-nums text-[var(--fg-soft)]">
                {b.bucket}
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-3 flex items-center gap-4 border-t border-[var(--line)] pt-3 text-[10.5px] text-[var(--muted)]">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-sm bg-[var(--accent)]" /> below pass (1–6)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-sm bg-[var(--ok)]" /> pass (7–10)
        </span>
      </div>
    </Card>
  );
}

// ── Clause verdicts donut/bar ──────────────────────────────────────────────
function ClauseVerdicts({ insights }: { insights: JudgeInsightsT }) {
  const v = insights.clause_verdicts ?? {
    met: 0,
    partially_met: 0,
    not_met: 0,
    not_assessable: 0,
  };
  const total = Math.max(
    v.met + v.partially_met + v.not_met + v.not_assessable,
    1,
  );
  const rows: Array<keyof typeof v> = [
    "met",
    "partially_met",
    "not_met",
    "not_assessable",
  ];
  return (
    <Card
      title="Clause verdicts"
      subtitle="How every success criterion was rated"
    >
      <div className="mb-4 flex h-3 w-full overflow-hidden rounded-full border border-[var(--line)] bg-[var(--surface-soft)]">
        {rows.map((k) => {
          const w = (v[k] / total) * 100;
          if (w <= 0) return null;
          return (
            <div
              key={k}
              title={`${VERDICT_LABEL[k]}: ${v[k]}`}
              style={{ width: `${w}%`, background: VERDICT_COLOR[k] }}
            />
          );
        })}
      </div>
      <div className="space-y-2">
        {rows.map((k) => {
          const pct = (v[k] / total) * 100;
          return (
            <div key={k} className="flex items-center gap-3">
              <span
                className="h-2 w-2 rounded-sm"
                style={{ background: VERDICT_COLOR[k] }}
              />
              <span className="flex-1 text-[12.5px] text-[var(--fg-soft)]">
                {VERDICT_LABEL[k]}
              </span>
              <span className="w-12 text-right font-mono text-[11.5px] tabular-nums text-[var(--fg)]">
                {v[k].toLocaleString()}
              </span>
              <span className="w-12 text-right font-mono text-[11px] tabular-nums text-[var(--muted)]">
                {pct.toFixed(1)}%
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// ── Top clauses list (not-met / partially-met) ─────────────────────────────
function TopClauses({
  title,
  subtitle,
  items,
  tone,
}: {
  title: string;
  subtitle: string;
  items: { clause: string; count: number }[];
  tone: "danger" | "warn";
}) {
  return (
    <Card title={title} subtitle={subtitle}>
      {items.length === 0 ? (
        <div className="py-6 text-center text-[12.5px] text-[var(--muted)]">
          Nothing here — the judge marked nothing in this bucket.
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((it, i) => (
            <li
              key={`${it.clause}-${i}`}
              className="flex items-start gap-3 rounded-md border border-[var(--line)] bg-[var(--surface-soft)] px-3 py-2"
            >
              <Pill tone={tone}>{it.count}×</Pill>
              <span className="text-[12.5px] leading-snug text-[var(--fg-soft)]">
                {it.clause}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// ── Weakness cluster ───────────────────────────────────────────────────────
function WeaknessCluster({ insights }: { insights: JudgeInsightsT }) {
  const phrases = insights.top_weakness_phrases ?? [];
  const samples = insights.weakness_samples ?? [];
  if (phrases.length === 0 && samples.length === 0) return null;
  const maxCount = Math.max(...phrases.map((p) => p.count), 1);
  return (
    <Card
      title="Recurring weaknesses"
      subtitle="Phrases the judge keeps surfacing across emails"
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
            Cluster (n-grams)
          </div>
          {phrases.length === 0 ? (
            <p className="text-[12.5px] text-[var(--muted)]">
              Not enough graded emails yet to cluster.
            </p>
          ) : (
            <ul className="space-y-2">
              {phrases.map((p) => (
                <li key={p.phrase} className="flex items-center gap-3">
                  <span className="w-[200px] truncate font-mono text-[11.5px] text-[var(--fg-soft)]">
                    {p.phrase}
                  </span>
                  <div className="flex-1">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface-mute)]">
                      <div
                        className="h-full rounded-full bg-[var(--accent)]"
                        style={{ width: `${(p.count / maxCount) * 100}%` }}
                      />
                    </div>
                  </div>
                  <span className="w-8 text-right font-mono text-[11px] tabular-nums text-[var(--fg)]">
                    {p.count}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
            Sample weaknesses
          </div>
          {samples.length === 0 ? (
            <p className="text-[12.5px] text-[var(--muted)]">
              No weakness samples yet.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {samples.slice(0, 10).map((s, i) => (
                <li
                  key={i}
                  className="rounded-md border border-[var(--line)] bg-[var(--surface-soft)] px-3 py-1.5 text-[12px] leading-snug text-[var(--fg-soft)]"
                >
                  {s}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Card>
  );
}

// ── Per-email grade card ───────────────────────────────────────────────────
function GradeCard({
  grade,
  expanded,
  onToggle,
}: {
  grade: JudgeGrade;
  expanded: boolean;
  onToggle: () => void;
}) {
  const score = grade.overall_score ?? 0;
  const certainty = (grade.certainty ?? 0) * 100;
  const tone =
    score >= 8
      ? "success"
      : score >= 7
        ? "info"
        : score >= 5
          ? "warn"
          : "danger";
  return (
    <section className="rounded-xl border border-[var(--line)] bg-[var(--surface)] shadow-[0_1px_2px_rgba(28,26,23,0.04)]">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        className="flex w-full items-start gap-4 px-5 py-4 text-left transition hover:bg-[var(--surface-soft)]"
      >
        <div
          className={cx(
            "grid h-12 w-12 shrink-0 place-items-center rounded-lg font-mono text-[16px] font-bold tabular-nums",
            tone === "success"
              ? "bg-[var(--ok-bg)] text-[var(--ok)]"
              : tone === "info"
                ? "bg-[var(--info-bg)] text-[var(--info)]"
                : tone === "warn"
                  ? "bg-[var(--warn-bg)] text-[var(--warn)]"
                  : "bg-[var(--risk-bg)] text-[var(--risk)]",
          )}
        >
          {score.toFixed(1)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
            <span className="text-[13.5px] font-semibold text-[var(--fg)]">
              {grade.display_name}
            </span>
            <span className="font-mono text-[10.5px] text-[var(--muted)]">
              {grade.customer_unique_id?.slice(0, 14)}…
            </span>
            {grade.churn_probability != null && (
              <Pill tone="accent">
                churn {(grade.churn_probability * 100).toFixed(0)}%
              </Pill>
            )}
            <Pill tone={grade.passed ? "success" : "warn"}>
              {grade.passed ? "pass" : "below pass"}
            </Pill>
            <span className="font-mono text-[10.5px] text-[var(--muted)]">
              certainty {certainty.toFixed(0)}%
            </span>
          </div>
          <div className="mt-1 truncate text-[12.5px] text-[var(--fg-soft)]">
            “{grade.subject || "—"}”
          </div>
          <p className="mt-2 line-clamp-2 text-[12.5px] leading-snug text-[var(--fg-mute)]">
            {grade.reasoning || "No reasoning recorded."}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <div className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-[var(--muted)]">
            judge
          </div>
          <div className="mt-0.5 font-mono text-[11px] text-[var(--fg-soft)]">
            {grade.judge_model ?? "—"}
          </div>
          <div className="mt-1 font-mono text-[10.5px] text-[var(--muted)]">
            {grade.latency_ms ? `${(grade.latency_ms / 1000).toFixed(1)}s` : ""}
          </div>
        </div>
      </button>

      {expanded && <GradeDetail grade={grade} />}
    </section>
  );
}

function GradeDetail({ grade }: { grade: JudgeGrade }) {
  return (
    <div className="grid gap-5 border-t border-[var(--line)] px-5 py-5 lg:grid-cols-[1.05fr_1fr]">
      <div className="space-y-4">
        <div>
          <div className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
            Reasoning
          </div>
          <p className="text-[12.5px] leading-relaxed text-[var(--fg)]">
            {grade.reasoning || "—"}
          </p>
        </div>
        <div>
          <div className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
            Weaknesses
          </div>
          {grade.weaknesses.length === 0 ? (
            <p className="text-[12.5px] text-[var(--muted)]">
              No weaknesses recorded.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {grade.weaknesses.map((w, i) => (
                <li
                  key={i}
                  className="rounded-md border border-[var(--line)] bg-[var(--surface-soft)] px-3 py-1.5 text-[12px] leading-snug text-[var(--fg-soft)]"
                >
                  {w}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <div className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
            Clauses evaluated
          </div>
          {grade.clauses_evaluated.length === 0 ? (
            <p className="text-[12.5px] text-[var(--muted)]">
              No clause-level breakdown recorded.
            </p>
          ) : (
            <ul className="space-y-2">
              {grade.clauses_evaluated.map((c, i) => (
                <ClauseRow key={i} clause={c} />
              ))}
            </ul>
          )}
        </div>
      </div>
      <div>
        <div className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
          Email being graded
        </div>
        <div className="rounded-lg border border-[var(--line)] bg-[var(--surface-soft)] p-3">
          <div className="text-[12.5px] font-semibold text-[var(--fg)]">
            {grade.subject || "—"}
          </div>
          <pre className="mt-2 whitespace-pre-wrap font-sans text-[12px] leading-relaxed text-[var(--fg-soft)]">
            {grade.body || "—"}
          </pre>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <MetricCell label="Score" value={(grade.overall_score ?? 0).toFixed(1)} primary />
          <MetricCell
            label="Certainty"
            value={`${Math.round((grade.certainty ?? 0) * 100)}%`}
          />
        </div>
        <Stat2
          label="Generator"
          value={grade.generator_model ?? "—"}
          mono
          muted
        />
      </div>
    </div>
  );
}

function ClauseRow({ clause }: { clause: ClauseEvaluated }) {
  const tone = VERDICT_TONE[clause.verdict] ?? "neutral";
  const label = VERDICT_LABEL[clause.verdict] ?? clause.verdict;
  return (
    <li className="rounded-md border border-[var(--line)] bg-[var(--surface)] px-3 py-2">
      <div className="flex items-start gap-2.5">
        <Pill tone={tone}>{label}</Pill>
        <span className="flex-1 text-[12.5px] leading-snug text-[var(--fg)]">
          {clause.clause}
        </span>
      </div>
      {clause.evidence && (
        <div className="mt-1.5 border-l-2 border-[var(--line)] pl-2 font-mono text-[11px] leading-snug text-[var(--muted)]">
          {clause.evidence}
        </div>
      )}
    </li>
  );
}
