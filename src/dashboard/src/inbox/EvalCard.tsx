// Right rail — LLM-judge email-quality eval status.
import type { InboxEval } from "../api";
import { SectionHead } from "./ui";

export function EvalCard({ ev }: { ev: InboxEval }) {
  const bar = ev.pass_threshold.toFixed(1);
  return (
    <section>
      <SectionHead eyebrow="Email quality" title="LLM-judge eval" />
      <div className="space-y-2.5 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-3">
        <div>
          <div className="flex items-baseline justify-between text-[11.5px]">
            <span className="font-medium text-[var(--fg-soft)]">
              Claude judge
            </span>
            <span className="font-mono text-[var(--muted)]">
              {(ev.judge_ms / 1000).toFixed(1)}s
            </span>
          </div>
          <div className="mt-1 flex items-center gap-2">
            <div className="h-1.5 flex-1 rounded-full bg-[var(--line-soft)]">
              <div
                className="h-full rounded-full bg-[var(--ok)]"
                style={{ width: `${(ev.judge_score / 5) * 100}%` }}
              />
            </div>
            <span className="font-mono text-[12px] font-semibold tabular-nums text-[var(--fg)]">
              {ev.judge_score.toFixed(1)}
            </span>
          </div>
        </div>
        <div className="pt-0.5 text-[11.5px] leading-[1.5]">
          {ev.passed ? (
            <span className="font-medium text-[var(--ok)]">
              ✓ Clears the {bar} quality bar — auto-eligible to send.
            </span>
          ) : (
            <span className="font-medium text-[var(--risk)]">
              ⚠ Below the {bar} bar — held from auto-send.
            </span>
          )}
        </div>
      </div>
    </section>
  );
}
