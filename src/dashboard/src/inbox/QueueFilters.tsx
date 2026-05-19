// Risk-tier filter chips above the queue. The "High" chip counts high OR
// critical — "high or worse" — even though the API filter does the same.
import type { FilterKey, InboxCustomerList } from "../api";

const CHIPS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "crit", label: "Critical" },
  { key: "high", label: "High" },
  { key: "med", label: "Medium" },
];

export function QueueFilters({
  totals,
  active,
  onChange,
}: {
  totals?: InboxCustomerList["totals"];
  active: FilterKey;
  onChange: (k: FilterKey) => void;
}) {
  function count(k: FilterKey): number | undefined {
    if (!totals) return undefined;
    if (k === "all") return totals.all;
    if (k === "crit") return totals.crit;
    if (k === "high") return totals.crit + totals.high; // high or worse
    return totals.med;
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {CHIPS.map((chip) => {
        const on = chip.key === active;
        const n = count(chip.key);
        return (
          <button
            key={chip.key}
            type="button"
            onClick={() => onChange(chip.key)}
            className={
              "rounded px-2 py-1 text-[11px] font-medium transition " +
              (on
                ? "bg-[var(--fg)] text-white"
                : "bg-[var(--surface-mute)] text-[var(--fg-soft)] hover:bg-[var(--line-soft)]")
            }
          >
            {chip.label}
            {n !== undefined && (
              <span
                className={
                  "ml-1 tabular-nums " +
                  (on ? "text-white/70" : "text-[var(--muted)]")
                }
              >
                {n}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
