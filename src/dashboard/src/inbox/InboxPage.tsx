// Triage Inbox — three-pane workspace for triaging at-risk customers:
// queue (left) · drafted-email detail (centre) · suggested play + eval (right).
//
// PR2 scaffolding: static skeleton shell. The real QueuePanel / DetailPane /
// RightRail land in PR3–PR6.

// Light-theme skeleton block (the shared dark Skeleton is invisible on
// the inbox's light surface).
function Sk({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-black/[0.06] ${className}`} />;
}

export function InboxPage() {
  return (
    <div className="flex h-full min-h-0">
      {/* Queue */}
      <section className="flex w-[320px] shrink-0 flex-col border-r border-[var(--line)] bg-[var(--surface)]">
        <header className="border-b border-[var(--line)] px-4 py-3.5">
          <Sk className="h-4 w-28" />
        </header>
        <div className="flex-1 space-y-2 overflow-y-auto p-3">
          {Array.from({ length: 8 }, (_, i) => (
            <Sk key={i} className="h-[68px] w-full" />
          ))}
        </div>
      </section>

      {/* Detail */}
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

      {/* Right rail */}
      <aside className="flex w-[296px] shrink-0 flex-col gap-4 overflow-y-auto border-l border-[var(--line)] bg-[var(--surface)] p-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Sk key={i} className="h-32 w-full" />
        ))}
      </aside>
    </div>
  );
}

export default InboxPage;
