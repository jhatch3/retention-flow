// One at-risk customer in the queue. Selection / sent states are mutually
// exclusive backgrounds; the risk meter is colored by tier, not raw risk.
import type { InboxCustomerSummary } from "../api";
import { TIER, avatarHue, brl, initials, pctInt } from "./inbox.utils";

export function QueueRow({
  c,
  selected,
  sent,
  onClick,
}: {
  c: InboxCustomerSummary;
  selected: boolean;
  sent: boolean;
  onClick: () => void;
}) {
  const tone = TIER[c.tier];
  const hue = avatarHue(c.customer_unique_id);
  // A customer is "sent" via the optimistic set or the API status.
  const isSent = sent || c.status === "sent";
  const bg = selected ? "#fbf3ee" : isSent ? "#f6f9f3" : "var(--surface)";
  const meterPct = Math.min(100, Math.round(c.risk * 100));

  return (
    <li role="option" aria-selected={selected}>
      <button
        type="button"
        onClick={onClick}
        style={{ background: bg }}
        className="relative flex w-full items-start gap-2.5 px-3.5 py-2.5 text-left"
      >
        <span
          className="absolute inset-y-0 left-0 w-[3px]"
          style={{ background: selected ? "var(--accent)" : "transparent" }}
        />
        <span
          className="mt-0.5 grid h-[30px] w-[30px] shrink-0 place-items-center rounded-full text-[11px] font-semibold"
          style={{
            background: `oklch(0.86 0.04 ${hue})`,
            color: `oklch(0.35 0.05 ${hue})`,
          }}
        >
          {initials(c.display_name)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline justify-between gap-2">
            <span className="truncate text-[12.5px] font-semibold text-[var(--fg)]">
              {c.display_name}
            </span>
            <span
              className="shrink-0 font-mono text-[12.5px] font-semibold tabular-nums"
              style={{ color: tone.bar }}
            >
              {pctInt(c.risk)}
            </span>
          </span>
          <span className="mt-0.5 block truncate text-[11px] text-[var(--fg-mute)]">
            {c.city} · {brl(c.ltv_brl)} · {c.recency_days}d
          </span>
          <span className="mt-1.5 flex items-center gap-2">
            <span className="h-1 flex-1 rounded-full bg-[var(--line-soft)]">
              <span
                className="block h-full rounded-full"
                style={{ width: `${meterPct}%`, background: tone.bar }}
              />
            </span>
            {isSent && (
              <span className="shrink-0 rounded bg-[var(--ok-bg)] px-1.5 py-px text-[9.5px] font-semibold uppercase tracking-wide text-[var(--ok)]">
                sent
              </span>
            )}
          </span>
        </span>
      </button>
    </li>
  );
}
