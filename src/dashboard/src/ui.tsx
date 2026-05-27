// Primitives: Card, Pill, Delta, Sparkline, Kpi, Button, Skeleton,
// SectionHeader, Stat2, MetricCell, KvItem. Warm cream surfaces, hairline
// borders — matched to the inbox style.
import { useMemo } from "react";
import type { ReactNode } from "react";
import { cx } from "./lib";

type Tone = "neutral" | "accent" | "success" | "warn" | "danger" | "info";

// ─── Card ────────────────────────────────────────────────────────────────
export function Card({
  title,
  subtitle,
  icon,
  right,
  children,
  className = "",
  pad = true,
  divider = true,
}: {
  title?: string;
  subtitle?: string;
  icon?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  pad?: boolean;
  divider?: boolean;
}) {
  return (
    <section
      className={cx(
        "rounded-xl border border-[var(--line)] bg-[var(--surface)]",
        "shadow-[0_1px_2px_rgba(28,26,23,0.04)]",
        className,
      )}
    >
      {(title || right) && (
        <header
          className={cx(
            "flex items-center gap-2 px-5 py-3.5",
            divider && "border-b border-[var(--line)]",
          )}
        >
          {icon && <span className="text-[var(--muted)]">{icon}</span>}
          <div className="min-w-0">
            {title && (
              <h2 className="truncate text-[13px] font-semibold tracking-tight text-[var(--fg)]">
                {title}
              </h2>
            )}
            {subtitle && (
              <p className="mt-0.5 text-[11px] text-[var(--muted)]">{subtitle}</p>
            )}
          </div>
          {right && (
            <div className="ml-auto flex items-center gap-2 text-[11px] text-[var(--muted)]">
              {right}
            </div>
          )}
        </header>
      )}
      <div className={pad ? "p-5" : ""}>{children}</div>
    </section>
  );
}

// ─── Pill ────────────────────────────────────────────────────────────────
export function Pill({
  tone = "neutral",
  dot = false,
  children,
  className = "",
}: {
  tone?: Tone;
  dot?: boolean;
  children: ReactNode;
  className?: string;
}) {
  const tones: Record<Tone, string> = {
    neutral:
      "bg-[var(--surface-mute)] text-[var(--fg-mute)] border-[var(--line)]",
    accent:
      "bg-[var(--risk-bg)] text-[var(--accent-fg)] border-[color-mix(in_oklch,var(--accent)_30%,transparent)]",
    success:
      "bg-[var(--ok-bg)] text-[var(--ok)] border-[color-mix(in_oklch,var(--ok)_28%,transparent)]",
    warn:
      "bg-[var(--warn-bg)] text-[var(--warn)] border-[color-mix(in_oklch,var(--warn)_28%,transparent)]",
    danger:
      "bg-[var(--risk-bg)] text-[var(--risk)] border-[color-mix(in_oklch,var(--risk)_28%,transparent)]",
    info:
      "bg-[var(--info-bg)] text-[var(--info)] border-[color-mix(in_oklch,var(--info)_28%,transparent)]",
  };
  const dotColors: Record<Tone, string> = {
    neutral: "bg-[var(--muted)]",
    accent: "bg-[var(--accent)]",
    success: "bg-[var(--ok)]",
    warn: "bg-[var(--warn)]",
    danger: "bg-[var(--risk)]",
    info: "bg-[var(--info)]",
  };
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5",
        "text-[10.5px] font-medium tracking-tight",
        tones[tone],
        className,
      )}
    >
      {dot && <span className={cx("h-1.5 w-1.5 rounded-full", dotColors[tone])} />}
      {children}
    </span>
  );
}

// ─── Delta ───────────────────────────────────────────────────────────────
export function Delta({
  value,
  suffix = "%",
  positiveIsGood = true,
}: {
  value: number;
  suffix?: string;
  positiveIsGood?: boolean;
}) {
  const up = value > 0;
  const good = positiveIsGood ? up : !up;
  const color =
    value === 0
      ? "text-[var(--muted)]"
      : good
        ? "text-[var(--ok)]"
        : "text-[var(--risk)]";
  const sign = value > 0 ? "+" : "";
  return (
    <span
      className={cx(
        "inline-flex items-center gap-0.5 text-[11px] font-medium tabular-nums",
        color,
      )}
    >
      {value === 0 ? "→" : up ? "↑" : "↓"} {sign}
      {value.toFixed(1)}
      {suffix}
    </span>
  );
}

// ─── Sparkline (no external lib) ─────────────────────────────────────────
export function Sparkline({
  data,
  width = 96,
  height = 28,
  color,
  fill = true,
}: {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fill?: boolean;
}) {
  const gid = useMemo(() => "spark-" + Math.random().toString(36).slice(2, 8), []);
  if (!data?.length) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const stepX = width / (data.length - 1);
  const points = data.map(
    (v, i) => [i * stepX, height - 2 - ((v - min) / range) * (height - 4)] as const,
  );
  const path = points
    .map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`))
    .join(" ");
  const area = `${path} L${width},${height} L0,${height} Z`;
  const c = color ?? "var(--accent)";
  const last = points[points.length - 1];
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
      <defs>
        <linearGradient id={gid} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={c} stopOpacity="0.35" />
          <stop offset="100%" stopColor={c} stopOpacity="0" />
        </linearGradient>
      </defs>
      {fill && <path d={area} fill={`url(#${gid})`} />}
      <path
        d={path}
        stroke={c}
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={last[0]} cy={last[1]} r="2" fill={c} />
    </svg>
  );
}

// ─── KPI card ────────────────────────────────────────────────────────────
export function Kpi({
  label,
  value,
  delta,
  deltaSuffix = "%",
  positiveIsGood = true,
  sparkData,
  sparkColor,
  footnote,
}: {
  label: string;
  value: string;
  delta?: number;
  deltaSuffix?: string;
  positiveIsGood?: boolean;
  sparkData?: number[];
  sparkColor?: string;
  footnote?: string;
}) {
  return (
    <div className="group rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5 shadow-[0_1px_2px_rgba(28,26,23,0.04)] transition hover:border-[var(--line-strong)]">
      <div className="flex items-start justify-between gap-3">
        <div className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-[var(--muted)]">
          {label}
        </div>
        {delta !== undefined && (
          <Delta value={delta} suffix={deltaSuffix} positiveIsGood={positiveIsGood} />
        )}
      </div>
      <div className="mt-3 flex items-end justify-between gap-3">
        <div className="text-[28px] font-semibold leading-none tracking-tight tabular-nums text-[var(--fg)]">
          {value}
        </div>
        {sparkData && (
          <Sparkline data={sparkData} color={sparkColor} width={88} height={32} />
        )}
      </div>
      {footnote && (
        <div className="mt-2 text-[11px] text-[var(--muted)]">{footnote}</div>
      )}
    </div>
  );
}

// ─── Button ──────────────────────────────────────────────────────────────
type Variant = "primary" | "secondary" | "ghost" | "outline" | "danger";

export function Button({
  variant = "secondary",
  size = "md",
  children,
  leftIcon,
  rightIcon,
  onClick,
  disabled,
  className = "",
  type = "button",
  title,
}: {
  variant?: Variant;
  size?: "sm" | "md" | "lg";
  children?: ReactNode;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
  type?: "button" | "submit";
  title?: string;
}) {
  const base =
    "inline-flex items-center justify-center gap-1.5 font-medium tracking-tight rounded-lg border transition disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap";
  const sizes = {
    sm: "h-7 px-2.5 text-[12px]",
    md: "h-8 px-3 text-[12.5px]",
    lg: "h-9 px-3.5 text-[13px]",
  };
  const variants: Record<Variant, string> = {
    primary:
      "bg-[var(--accent)] text-[var(--on-accent)] border-[var(--accent)] hover:bg-[var(--accent-hov)] hover:border-[var(--accent-hov)] shadow-[0_1px_2px_rgba(196,74,45,0.18)]",
    secondary:
      "bg-[var(--surface)] text-[var(--fg)] border-[var(--line)] hover:bg-[var(--surface-mute)] hover:border-[var(--line-strong)]",
    ghost:
      "bg-transparent text-[var(--fg-soft)] border-transparent hover:bg-black/[0.04] hover:text-[var(--fg)]",
    outline:
      "bg-[var(--surface)] text-[var(--fg)] border-[var(--line)] hover:border-[var(--fg-mute)]",
    danger:
      "bg-[var(--risk-bg)] text-[var(--risk)] border-[color-mix(in_oklch,var(--risk)_30%,transparent)] hover:bg-[color-mix(in_oklch,var(--risk-bg)_70%,var(--risk))]",
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cx(base, sizes[size], variants[variant], className)}
    >
      {leftIcon}
      {children}
      {rightIcon}
    </button>
  );
}

// ─── Skeleton ────────────────────────────────────────────────────────────
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={cx("animate-pulse rounded-md bg-black/[0.05]", className)} />;
}

// ─── Section header ──────────────────────────────────────────────────────
export function SectionHeader({
  eyebrow,
  title,
  action,
}: {
  eyebrow?: string;
  title?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-3 flex items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
            {eyebrow}
          </div>
        )}
        {title && (
          <h3 className="text-[15px] font-semibold tracking-tight text-[var(--fg)]">
            {title}
          </h3>
        )}
      </div>
      {action}
    </div>
  );
}

// ─── Small stat (card-internal) ──────────────────────────────────────────
export function Stat2({
  label,
  value,
  mono = false,
  muted = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
  muted?: boolean;
}) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
        {label}
      </div>
      <div
        className={cx(
          "mt-1 text-[18px] font-semibold leading-none tracking-tight tabular-nums",
          muted ? "text-[var(--fg-soft)]" : "text-[var(--fg)]",
          mono && "font-mono",
        )}
      >
        {value}
      </div>
    </div>
  );
}

export function MetricCell({
  label,
  value,
  primary = false,
}: {
  label: string;
  value: string;
  primary?: boolean;
}) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-[0.1em] text-[var(--muted)]">
        {label}
      </div>
      <div
        className={cx(
          "mt-1 font-mono font-semibold leading-none tracking-tight tabular-nums",
          primary ? "text-[20px] text-[var(--accent-fg)]" : "text-[18px] text-[var(--fg)]",
        )}
      >
        {value}
      </div>
    </div>
  );
}

export function KvItem({
  k,
  v,
  tone,
  mono = false,
}: {
  k: string;
  v: string;
  tone?: "warn" | "danger";
  mono?: boolean;
}) {
  const color =
    tone === "warn"
      ? "text-[var(--warn)]"
      : tone === "danger"
        ? "text-[var(--risk)]"
        : "text-[var(--fg)]";
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className="text-[var(--muted)]">{k}</span>
      <span className={cx("font-semibold tabular-nums", mono && "font-mono", color)}>
        {v}
      </span>
    </span>
  );
}
