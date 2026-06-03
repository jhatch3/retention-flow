// Shared inbox primitives (light theme). SectionHead is added with the
// right rail in PR6.
import type { ReactNode } from "react";
import { avatarHue, initials } from "./inbox.utils";

type ChipTone = "neutral" | "risk" | "warn" | "ok" | "info" | "mono";

const CHIP_TONES: Record<ChipTone, string> = {
  neutral: "bg-[var(--surface-mute)] text-[var(--fg-mute)] border-[var(--line)]",
  risk: "bg-[var(--risk-bg)] text-[var(--risk)] border-transparent",
  warn: "bg-[var(--warn-bg)] text-[var(--warn)] border-transparent",
  ok: "bg-[var(--ok-bg)] text-[var(--ok)] border-transparent",
  info: "bg-[var(--info-bg)] text-[var(--info)] border-transparent",
  mono: "bg-[var(--surface-mute)] text-[var(--fg-mute)] border-[var(--line)] font-mono",
};

export function Chip({
  tone = "neutral",
  children,
}: {
  tone?: ChipTone;
  children: ReactNode;
}) {
  return (
    <span
      className={
        "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 " +
        "text-[10.5px] font-medium leading-none " +
        CHIP_TONES[tone]
      }
    >
      {children}
    </span>
  );
}

export function Avatar({
  id,
  name,
  size = 44,
}: {
  id: string;
  name: string;
  size?: number;
}) {
  const hue = avatarHue(id);
  return (
    <span
      className="grid shrink-0 place-items-center rounded-full font-semibold"
      style={{
        width: size,
        height: size,
        fontSize: Math.round(size * 0.34),
        background: `oklch(0.86 0.04 ${hue})`,
        color: `oklch(0.35 0.05 ${hue})`,
      }}
    >
      {initials(name)}
    </span>
  );
}

// Light-theme skeleton block (the shared dark Skeleton is invisible here).
export function Sk({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-black/[0.06] ${className}`} />;
}

// Card / section header — caps-mono eyebrow + title + optional action.
export function SectionHead({
  eyebrow,
  title,
  action,
}: {
  eyebrow: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-2 flex items-start justify-between gap-2">
      <div className="min-w-0">
        <div className="font-mono text-[10px] uppercase tracking-[1.2px] text-[var(--muted)]">
          {eyebrow}
        </div>
        <div className="mt-0.5 truncate text-[13px] font-semibold tracking-[-0.2px] text-[var(--fg)]">
          {title}
        </div>
      </div>
      {action}
    </div>
  );
}
