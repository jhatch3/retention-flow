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
import { RightRail } from "./RightRail";
import type { InboxTab } from "./TabBar";

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

  // Keyboard: ↑/↓ (j/k) move selection, 1/2/3 switch tabs, ⌘/Ctrl+Enter
  // sends. Ignored while typing in a field or the editable email body.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = document.activeElement as HTMLElement | null;
      if (
        el &&
        (el.tagName === "INPUT" ||
          el.tagName === "TEXTAREA" ||
          el.isContentEditable)
      ) {
        return;
      }
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        if (selectedId && !sent.has(selectedId)) {
          e.preventDefault();
          handleSend(selectedId);
        }
        return;
      }
      if (e.key === "1") return setEmailTab("draft");
      if (e.key === "2") return setEmailTab("reasoning");
      if (e.key === "3") return setEmailTab("history");

      const down = e.key === "ArrowDown" || e.key === "j";
      const up = e.key === "ArrowUp" || e.key === "k";
      const rows = list.data?.customers ?? [];
      if ((down || up) && rows.length) {
        e.preventDefault();
        const idx = rows.findIndex((r) => r.customer_unique_id === selectedId);
        const base = idx < 0 ? 0 : idx;
        const next = down
          ? (base + 1) % rows.length
          : (base - 1 + rows.length) % rows.length;
        setSelectedId(rows[next].customer_unique_id);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [list.data, selectedId, sent, handleSend]);

  const isSent: boolean =
    (!!selectedId && sent.has(selectedId)) ||
    detail.data?.summary.status === "sent" ||
    false;

  // Empty queue — no at-risk customers at all (handoff §8.1).
  if (list.data && list.data.totals.all === 0) {
    return (
      <div className="grid h-full place-items-center bg-[var(--surface-soft)]">
        <div className="rounded-lg border border-[var(--line)] bg-[var(--ok-bg)] px-8 py-7 text-center">
          <div className="text-[15px] font-semibold text-[var(--ok)]">
            ✓ Nobody's at risk right now
          </div>
          <p className="mt-1.5 text-[12.5px] text-[var(--fg-mute)]">
            The next nightly score run will refresh this queue.
          </p>
        </div>
      </div>
    );
  }

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

      <RightRail
        detail={detail.data}
        modelVersion={list.data?.model_version ?? ""}
      />
    </div>
  );
}

export default InboxPage;
