// Triage Inbox — three-pane workspace for triaging at-risk customers:
// queue (left) · drafted-email detail (centre) · suggested play + eval (right).
//
// PR3: real queue + selection plumbed. The centre + right panes are still
// skeletons — DetailPane / RightRail land in PR4–PR6.
import { useEffect, useState } from "react";
import type { FilterKey } from "../api";
import { useInboxQueue } from "./inbox.hooks";
import { QueuePanel } from "./QueuePanel";

// PR4 replaces this with the optimistic "sent" set owned by InboxPage.
const NO_SENT = new Set<string>();

// Light-theme skeleton block (the shared dark Skeleton is invisible here).
function Sk({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-black/[0.06] ${className}`} />;
}

export function InboxPage() {
  const [filter, setFilter] = useState<FilterKey>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const list = useInboxQueue(filter);

  // Auto-select the first row once the queue arrives, and re-select when the
  // current pick drops out of the filtered list.
  useEffect(() => {
    const rows = list.data?.customers ?? [];
    if (!rows.length) return;
    if (!selectedId || !rows.some((r) => r.customer_unique_id === selectedId)) {
      setSelectedId(rows[0].customer_unique_id);
    }
  }, [list.data, selectedId]);

  return (
    <div className="flex h-full min-h-0">
      <QueuePanel
        list={list.data}
        loading={list.loading}
        error={list.error}
        filter={filter}
        onFilter={setFilter}
        selectedId={selectedId}
        sent={NO_SENT}
        onSelect={setSelectedId}
      />

      {/* Detail — real DetailPane lands in PR4. */}
      <section className="flex min-w-0 flex-1 flex-col bg-[var(--surface-soft)]">
        <header className="border-b border-[var(--line)] bg-[var(--surface)] px-6 py-4">
          <Sk className="h-6 w-52" />
        </header>
        <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
          <Sk className="h-9 w-full" />
          <Sk className="h-64 w-full" />
          <Sk className="h-10 w-72" />
        </div>
      </section>

      {/* Right rail — real cards land in PR6. */}
      <aside className="flex w-[296px] shrink-0 flex-col gap-4 overflow-y-auto border-l border-[var(--line)] bg-[var(--surface)] p-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Sk key={i} className="h-32 w-full" />
        ))}
      </aside>
    </div>
  );
}

export default InboxPage;
