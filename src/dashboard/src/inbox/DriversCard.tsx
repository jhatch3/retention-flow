// Right rail — compact top-5 SHAP drivers, each with a thin ± bar.
import type { InboxDriver } from "../api";
import { ShapBar } from "./ShapBar";
import { SectionHead } from "./ui";

export function DriversCard({ drivers }: { drivers: InboxDriver[] }) {
  const top = drivers.slice(0, 5);
  const maxAbs = Math.max(...top.map((d) => Math.abs(d.contrib)), 0.0001);

  return (
    <section>
      <SectionHead eyebrow="Top drivers" title="What's moving the score" />
      <div className="space-y-2.5">
        {top.map((d) => (
          <div key={d.feature}>
            <div className="flex items-baseline justify-between gap-2">
              <span className="truncate font-mono text-[11px] text-[var(--fg-soft)]">
                {d.feature}
              </span>
              <span
                className="font-mono text-[11px] font-semibold tabular-nums"
                style={{ color: d.contrib > 0 ? "var(--risk)" : "var(--ok)" }}
              >
                {d.contrib > 0 ? "+" : ""}
                {d.contrib.toFixed(2)}
              </span>
            </div>
            <div className="mt-1">
              <ShapBar contrib={d.contrib} max={maxAbs} height={6} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
