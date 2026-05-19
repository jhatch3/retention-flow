// Right rail — the quietest card: a few plain facts about the account.
import type { InboxCustomerDetail } from "../api";
import { SectionHead } from "./ui";

export function ActivityCard({
  detail,
  modelVersion,
}: {
  detail: InboxCustomerDetail;
  modelVersion: string;
}) {
  // Recipient-level outreach history needs the LLM email pipeline (v1.1);
  // until then the attempt line is a fixed placeholder.
  const lines: { label: string; value: string }[] = [
    { label: "Scored by", value: modelVersion || "churn-xgboost" },
    { label: "Retention plays", value: "none attempted yet" },
    { label: "Watchlist", value: `${detail.cohort_label} cohort` },
  ];

  return (
    <section>
      <SectionHead eyebrow="Activity" title="Recent on this account" />
      <ul className="space-y-1.5 text-[11.5px] leading-[1.6] text-[var(--muted)]">
        {lines.map((l) => (
          <li key={l.label}>
            · {l.label}{" "}
            <b className="font-medium text-[var(--fg-soft)]">{l.value}</b>
          </li>
        ))}
      </ul>
    </section>
  );
}
