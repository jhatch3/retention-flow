// "Why this score" tab — the SHAP decomposition: a base→predicted math strip
// and a per-driver contribution table.
import type { InboxCustomerDetail } from "../api";
import { TIER } from "./inbox.utils";
import { ShapBar } from "./ShapBar";

function signed(n: number): string {
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}`;
}

export function ReasoningView({ detail }: { detail: InboxCustomerDetail }) {
  const { drivers, summary } = detail;
  const maxAbs = Math.max(...drivers.map((d) => Math.abs(d.contrib)), 0.0001);

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="font-mono text-[10.5px] uppercase tracking-[1.4px] text-[var(--muted)]">
            SHAP decomposition
          </div>
          <h3 className="mt-0.5 text-[15px] font-semibold tracking-[-0.2px] text-[var(--fg)]">
            What pushed this score to {TIER[summary.tier].label.toLowerCase()} risk
          </h3>
        </div>
        <div className="shrink-0 text-[11px] text-[var(--muted)]">
          vs. 50% baseline
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-[var(--line)] bg-[var(--surface)]">
        {/* base -> predicted math strip */}
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-[var(--line-soft)] bg-[var(--surface-mute)] px-4 py-3 font-mono text-[11.5px]">
          <span className="text-[var(--fg-soft)]">0.50</span>
          <span className="text-[var(--muted)]">base</span>
          {drivers.map((d) => (
            <span key={d.feature} className="flex items-center gap-2">
              <span className="text-[var(--muted)]">→</span>
              <span style={{ color: d.contrib > 0 ? "var(--risk)" : "var(--ok)" }}>
                {signed(d.contrib)}
              </span>
            </span>
          ))}
          <span className="text-[var(--muted)]">→</span>
          <span className="font-semibold text-[var(--fg)]">
            {summary.risk.toFixed(2)}
          </span>
          <span className="text-[var(--muted)]">predicted</span>
        </div>

        {/* driver table */}
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-[10.5px] uppercase tracking-wide text-[var(--muted)]">
              <th className="px-4 py-2 text-left font-medium">Feature</th>
              <th className="px-2 py-2 text-right font-medium">Value</th>
              <th className="w-[180px] px-2 py-2 text-left font-medium">
                Contribution
              </th>
              <th className="px-4 py-2 text-left font-medium">Why it matters</th>
            </tr>
          </thead>
          <tbody>
            {drivers.map((d) => (
              <tr key={d.feature} className="border-t border-[var(--line-soft)]">
                <td className="px-4 py-2 font-mono text-[var(--fg-soft)]">
                  {d.feature}
                </td>
                <td className="px-2 py-2 text-right font-mono tabular-nums text-[var(--fg-soft)]">
                  {d.value}
                </td>
                <td className="px-2 py-2">
                  <div className="flex items-center gap-2">
                    <div className="w-[110px]">
                      <ShapBar contrib={d.contrib} max={maxAbs} height={14} />
                    </div>
                    <span
                      className="font-mono text-[11px] tabular-nums"
                      style={{
                        color: d.contrib > 0 ? "var(--risk)" : "var(--ok)",
                      }}
                    >
                      {signed(d.contrib)}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-2 text-[var(--fg-mute)]">{d.why}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
