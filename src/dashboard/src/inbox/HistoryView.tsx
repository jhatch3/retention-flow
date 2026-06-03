// "Customer history" tab — a vertical event timeline.
import type { InboxCustomerDetail, InboxEvent } from "../api";

const DOT: Record<InboxEvent["tag"], string> = {
  risk: "var(--risk)",
  pos: "var(--ok)",
  neutral: "var(--muted)",
};

export function HistoryView({ detail }: { detail: InboxCustomerDetail }) {
  const { history, summary } = detail;

  return (
    <div className="space-y-3">
      <div>
        <div className="font-mono text-[10.5px] uppercase tracking-[1.4px] text-[var(--muted)]">
          Timeline
        </div>
        <h3 className="mt-0.5 text-[15px] font-semibold tracking-[-0.2px] text-[var(--fg)]">
          Account history
        </h3>
        <div className="mt-0.5 text-[11px] text-[var(--muted)]">
          joined {summary.joined_human} · {summary.orders_lifetime} orders
        </div>
      </div>

      <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] py-1.5">
        {history.map((ev, i) => (
          <div
            key={`${ev.ts}-${i}`}
            className={
              "flex gap-3 px-4 py-2.5 " +
              (i < history.length - 1
                ? "border-b border-[var(--line-soft)]"
                : "")
            }
          >
            <div className="w-[60px] shrink-0 pt-px font-mono text-[11px] text-[var(--muted)]">
              {ev.ts_human}
            </div>
            <div
              className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full"
              style={{ background: DOT[ev.tag] }}
            />
            <div className="min-w-0">
              <div className="text-[13px] font-medium text-[var(--fg)]">
                {ev.title}
              </div>
              {ev.note && (
                <div className="mt-0.5 text-[12px] text-[var(--muted)]">
                  {ev.note}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
