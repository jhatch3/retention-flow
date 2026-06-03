// Top of the detail pane — identity on the left, the churn-probability
// number as the centerpiece on the right. Shares the white block with the
// tab bar below it (no own bottom border).
import type { InboxCustomerSummary } from "../api";
import { TIER, pctInt } from "./inbox.utils";
import { Avatar, Chip } from "./ui";

export function CustomerHead({
  c,
  threshold,
  modelVersion,
}: {
  c: InboxCustomerSummary;
  threshold: number;
  modelVersion: string;
}) {
  const tone = TIER[c.tier];
  return (
    <header className="flex items-start gap-4 bg-[var(--surface)] px-6 pt-5">
      <div className="flex flex-1 items-start gap-3.5 pb-4">
        <Avatar id={c.customer_unique_id} name={c.display_name} size={44} />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-[18px] font-semibold tracking-[-0.3px] text-[var(--fg)]">
              {c.display_name}
            </h1>
            <Chip tone="risk">{tone.label} risk</Chip>
            <Chip tone="mono">{c.customer_unique_id.slice(0, 8)}…</Chip>
          </div>
          <div className="mt-1 text-[12.5px] text-[var(--fg-mute)]">
            {c.city} · joined {c.joined_human} · {c.orders_lifetime} orders ·
            last: {c.last_order_label}
          </div>
        </div>
      </div>
      <div className="shrink-0 pb-4 text-right">
        <div className="font-mono text-[10.5px] uppercase tracking-[1px] text-[var(--muted)]">
          Churn probability
        </div>
        <div className="mt-0.5 tabular-nums">
          <span
            className="text-[28px] font-semibold leading-none"
            style={{ color: "var(--risk)" }}
            aria-label={`Churn probability ${pctInt(c.risk)} percent`}
          >
            {pctInt(c.risk)}
          </span>
          <span className="ml-0.5 text-[16px] font-medium text-[var(--muted)]">
            %
          </span>
        </div>
        <div className="mt-1 text-[11px] text-[var(--muted)]">
          threshold {Math.round(threshold * 100)}% · model {modelVersion}
        </div>
      </div>
    </header>
  );
}
