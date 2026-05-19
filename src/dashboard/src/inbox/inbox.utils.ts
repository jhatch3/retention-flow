// Triage Inbox — tier colors, labels, and small format helpers.
import type { RiskTier } from "../api";

// Per-tier risk-meter color, chip label, and tinted background.
// Colors are intentionally literal (not all map to a single token) — see
// HANDOFF-triage-inbox.md §6.4.
export const TIER: Record<RiskTier, { label: string; bar: string; bg: string }> = {
  crit: { label: "Critical", bar: "var(--risk)", bg: "var(--risk-bg)" },
  high: { label: "High", bar: "#a85426", bg: "var(--warn-bg)" },
  med: { label: "Medium", bar: "var(--warn)", bg: "var(--warn-bg)" },
  low: { label: "Low", bar: "var(--ok)", bg: "var(--ok-bg)" },
};

/** Churn probability 0..1 → integer-percent string, e.g. 0.91 → "91". */
export function pctInt(p: number): string {
  return `${Math.round(p * 100)}`;
}

/** Brazilian-real amount, e.g. 1840 → "R$ 1.840". */
export function brl(n: number): string {
  return `R$ ${n.toLocaleString("pt-BR")}`;
}

/** ISO timestamp → "14m ago" / "2h ago" / "3d ago". */
export function relTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const s = Math.max(0, (Date.now() - then) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

/** Deterministic 0–359 hue from a customer id (for avatar tinting). */
export function avatarHue(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) % 360;
  return h;
}

/** First two initials from a display name. */
export function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}
