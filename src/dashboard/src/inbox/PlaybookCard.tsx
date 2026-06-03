// Right rail — suggested retention play + alternatives. The alternative
// radios are visual-only in v1 (selecting one does not re-draft the email).
import type { InboxCustomerDetail } from "../api";
import { SectionHead } from "./ui";

export function PlaybookCard({ detail }: { detail: InboxCustomerDetail }) {
  const { plays, cohort_label, cohort_save_rate_pct, cohort_n } = detail;
  const active = plays.find((p) => p.active) ?? plays[0];

  return (
    <section>
      <SectionHead eyebrow="Suggested play" title={active?.name ?? "—"} />
      <div className="rounded-lg bg-[var(--surface-mute)] p-3 text-[12px] leading-[1.5] text-[var(--fg-soft)]">
        Cohort segment{" "}
        <b className="font-semibold text-[var(--fg)]">{cohort_label}</b>{" "}
        historically responds best to this play.{" "}
        <b className="font-semibold text-[var(--fg)]">
          Save rate: {cohort_save_rate_pct}%
        </b>{" "}
        over the last 90 days (n={cohort_n}).
      </div>

      <ul className="mt-2.5 space-y-px">
        {plays.map((p) => (
          <li
            key={p.id}
            title={p.active ? undefined : "Coming v1.1"}
            className={
              "flex items-center gap-2 rounded-md px-2 py-1.5 text-[12px] " +
              (p.active ? "" : "cursor-not-allowed opacity-70")
            }
          >
            <span
              className="grid h-3.5 w-3.5 shrink-0 place-items-center rounded-full border"
              style={{ borderColor: p.active ? "var(--accent)" : "var(--line)" }}
            >
              {p.active && (
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
              )}
            </span>
            <span
              className={
                "flex-1 truncate " +
                (p.active
                  ? "font-medium text-[var(--fg)]"
                  : "text-[var(--fg-soft)]")
              }
            >
              {p.name}
            </span>
            <span className="font-mono text-[11px] tabular-nums text-[var(--muted)]">
              {p.save_rate_pct}%
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
