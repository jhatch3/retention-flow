// Right rail — two-tier email-quality eval status.
import type { InboxEval } from "../api";
import { SectionHead } from "./ui";

function EvalRow({
  label,
  latency,
  score,
}: {
  label: string;
  latency: string;
  score: number;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between text-[11.5px]">
        <span className="font-medium text-[var(--fg-soft)]">{label}</span>
        <span className="font-mono text-[var(--muted)]">{latency}</span>
      </div>
      <div className="mt-1 flex items-center gap-2">
        <div className="h-1.5 flex-1 rounded-full bg-[var(--line-soft)]">
          <div
            className="h-full rounded-full bg-[var(--ok)]"
            style={{ width: `${(score / 5) * 100}%` }}
          />
        </div>
        <span className="font-mono text-[12px] font-semibold tabular-nums text-[var(--fg)]">
          {score.toFixed(1)}
        </span>
      </div>
    </div>
  );
}

export function EvalCard({ ev }: { ev: InboxEval }) {
  const bar = ev.pass_threshold.toFixed(1);
  return (
    <section>
      <SectionHead eyebrow="Email quality" title="Two-tier eval" />
      <div className="space-y-2.5 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-3">
        <EvalRow
          label="DistilBERT (tier 1)"
          latency={`${ev.distilbert_ms}ms`}
          score={ev.distilbert_score}
        />
        <div className="border-b border-[var(--line-soft)]" />
        <EvalRow
          label="Claude judge (tier 2)"
          latency={`${(ev.judge_ms / 1000).toFixed(1)}s`}
          score={ev.judge_score}
        />
        <div className="pt-0.5 text-[11.5px] leading-[1.5]">
          {ev.passed ? (
            <>
              <span className="text-[var(--muted)]">
                Both clear the {bar} quality bar — auto-eligible to send.
              </span>
              <div className="mt-1 font-medium text-[var(--ok)]">
                ✓ agreement Δ {ev.agreement_delta.toFixed(1)}
              </div>
            </>
          ) : (
            <>
              <span className="text-[var(--risk)]">
                Below the {bar} bar — held from auto-send.
              </span>
              <div className="mt-1 font-medium text-[var(--risk)]">
                ⚠ agreement Δ {ev.agreement_delta.toFixed(1)}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
