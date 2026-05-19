// Centre-pane tab control — underline style, three fixed tabs.
export type InboxTab = "draft" | "reasoning" | "history";

const TABS: { key: InboxTab; label: string }[] = [
  { key: "draft", label: "AI-drafted email" },
  { key: "reasoning", label: "Why this score" },
  { key: "history", label: "Customer history" },
];

export function TabBar({
  tab,
  onTab,
}: {
  tab: InboxTab;
  onTab: (t: InboxTab) => void;
}) {
  return (
    <div
      role="tablist"
      className="flex border-b border-[var(--line)] bg-[var(--surface)] px-6"
    >
      {TABS.map((t) => {
        const on = t.key === tab;
        return (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={on}
            onClick={() => onTab(t.key)}
            className={
              "-mb-px mr-[18px] border-b-2 py-2.5 text-[12.5px] transition " +
              (on
                ? "border-[var(--accent)] font-semibold text-[var(--fg)]"
                : "border-transparent font-medium text-[var(--muted)] hover:text-[var(--fg-soft)]")
            }
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
