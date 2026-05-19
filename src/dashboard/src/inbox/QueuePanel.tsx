// Left pane — queue header (count + sort), filter chips, scrollable row list.
// Fixed 320px width; intentionally not resizable (handoff §6.2).
import type { FilterKey, InboxCustomerList } from "../api";
import { QueueFilters } from "./QueueFilters";
import { QueueRow } from "./QueueRow";

function RowSkeleton() {
  return (
    <div className="mx-3 my-1 h-[68px] animate-pulse rounded-md bg-black/[0.06]" />
  );
}

export function QueuePanel({
  list,
  loading,
  error,
  filter,
  onFilter,
  selectedId,
  sent,
  onSelect,
}: {
  list?: InboxCustomerList;
  loading: boolean;
  error?: string;
  filter: FilterKey;
  onFilter: (k: FilterKey) => void;
  selectedId: string | null;
  sent: Set<string>;
  onSelect: (id: string) => void;
}) {
  const customers = list?.customers ?? [];

  return (
    <section className="flex w-[320px] shrink-0 flex-col border-r border-[var(--line)] bg-[var(--surface)]">
      <header className="border-b border-[var(--line)] px-4 pb-2.5 pt-3.5">
        <div className="mb-2.5 flex items-center justify-between">
          <div className="text-[13px] font-semibold text-[var(--fg)]">
            Queue · {list?.totals.all ?? "—"}
          </div>
          <div className="font-mono text-[10.5px] text-[var(--muted)]">
            sorted: risk ↓
          </div>
        </div>
        <QueueFilters totals={list?.totals} active={filter} onChange={onFilter} />
      </header>

      <ul
        role="listbox"
        aria-label="At-risk customers"
        className="flex-1 overflow-y-auto py-1"
      >
        {error ? (
          <li className="px-4 py-8 text-center text-[12px] text-[var(--risk)]">
            {error}
          </li>
        ) : loading && !list ? (
          Array.from({ length: 8 }, (_, i) => <RowSkeleton key={i} />)
        ) : customers.length === 0 ? (
          <li className="px-4 py-10 text-center text-[12px] text-[var(--muted)]">
            No customers in this filter.
          </li>
        ) : (
          customers.map((c) => (
            <QueueRow
              key={c.customer_unique_id}
              c={c}
              selected={c.customer_unique_id === selectedId}
              sent={sent.has(c.customer_unique_id)}
              onClick={() => onSelect(c.customer_unique_id)}
            />
          ))
        )}
      </ul>
    </section>
  );
}
