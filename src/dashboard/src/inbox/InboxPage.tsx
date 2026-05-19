// Triage Inbox — three-pane workspace for triaging at-risk customers:
// queue (left) · drafted-email detail (centre) · suggested play + eval (right).
//
// PR4: queue + detail (draft tab) live. The right rail is still skeletons —
// its cards land in PR6; the reasoning/history tabs in PR5.
import { useCallback, useEffect, useState } from "react";
import type { FilterKey } from "../api";
import { useInboxCustomer, useInboxQueue } from "./inbox.hooks";
import { DetailPane } from "./DetailPane";
import { QueuePanel } from "./QueuePanel";
import type { InboxTab } from "./TabBar";
import { Sk } from "./ui";

export function InboxPage() {
  const [filter, setFilter] = useState<FilterKey>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sent, setSent] = useState<Set<string>>(new Set());
  const [emailTab, setEmailTab] = useState<InboxTab>("draft");

  const list = useInboxQueue(filter);
  const detail = useInboxCustomer(selectedId);

  // Auto-select the first row once the queue arrives, and re-select when the
  // current pick drops out of the filtered list.
  useEffect(() => {
    const rows = list.data?.customers ?? [];
    if (!rows.length) return;
    if (!selectedId || !rows.some((r) => r.customer_unique_id === selectedId)) {
      setSelectedId(rows[0].customer_unique_id);
    }
  }, [list.data, selectedId]);

  const handleSend = useCallback((id: string) => {
    // Optimistic — v1.1 will POST and roll back on failure.
    setSent((prev) => new Set(prev).add(id));
  }, []);

  const isSent: boolean =
    (!!selectedId && sent.has(selectedId)) ||
    detail.data?.summary.status === "sent" ||
    false;

  return (
    <div className="flex h-full min-h-0">
      <QueuePanel
        list={list.data}
        loading={list.loading}
        error={list.error}
        filter={filter}
        onFilter={setFilter}
        selectedId={selectedId}
        sent={sent}
        onSelect={setSelectedId}
      />

      <DetailPane
        detail={detail.data}
        error={detail.error}
        tab={emailTab}
        onTab={setEmailTab}
        isSent={isSent}
        onSend={() => selectedId && handleSend(selectedId)}
        threshold={list.data?.threshold ?? 0.33}
        modelVersion={list.data?.model_version ?? ""}
      />

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
