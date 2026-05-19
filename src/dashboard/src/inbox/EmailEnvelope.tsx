// The drafted email rendered as a card — To/From/Subject head, serif body,
// grounding-trace footer. In edit mode the body is contentEditable with a
// warning-yellow tint; edits live in the DOM only (v1, local-only).
import { ShieldCheck } from "lucide-react";
import type { InboxEmailDraft } from "../api";
import { Chip } from "./ui";

export function EmailEnvelope({
  email,
  edit,
}: {
  email: InboxEmailDraft;
  edit: boolean;
}) {
  return (
    <article
      className="overflow-hidden rounded-lg border"
      style={{
        borderColor: edit ? "var(--warn)" : "var(--line)",
        borderStyle: edit ? "dashed" : "solid",
        background: edit ? "#fffcf3" : "#ffffff",
      }}
    >
      <div className="grid grid-cols-[60px_1fr] gap-y-1.5 border-b border-[var(--line-soft)] px-4 py-3 text-[12.5px]">
        <span className="text-[var(--muted)]">To</span>
        <span className="text-[var(--fg-soft)]">
          {email.to}
          <span className="ml-1.5 text-[var(--muted)]">· verified · opted-in</span>
        </span>
        <span className="text-[var(--muted)]">From</span>
        <span className="flex flex-wrap items-center gap-1.5 text-[var(--fg-soft)]">
          {email.from_name}
          <Chip tone="mono">persona: {email.persona}</Chip>
        </span>
        <span className="text-[var(--muted)]">Subject</span>
        <span className="font-semibold text-[var(--fg)]">{email.subject}</span>
      </div>

      <div
        className="min-h-[220px] whitespace-pre-wrap px-5 py-4 font-serif text-[13.5px] leading-[1.65] text-[var(--fg-soft)] focus:outline-none"
        contentEditable={edit}
        suppressContentEditableWarning
      >
        {email.body}
      </div>

      <div className="flex items-center gap-1.5 border-t border-[var(--line-soft)] bg-[var(--surface-mute)] px-4 py-2.5 text-[11.5px] text-[var(--muted)]">
        <ShieldCheck size={13} />
        <span>Every claim references real account data —</span>
        <a href="#" className="font-medium text-[var(--accent)]">
          grounding trace →
        </a>
      </div>
    </article>
  );
}
