// Shared UI primitives for the dashboard.
import type { ReactNode } from "react";

export const chartTooltip = {
  background: "#0f172a",
  border: "1px solid #1e293b",
  borderRadius: "8px",
  color: "#e2e8f0",
  fontSize: "12px",
};

export function Card({
  title,
  icon,
  right,
  children,
}: {
  title: string;
  icon?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg shadow-black/20">
      <div className="mb-4 flex items-center gap-2">
        {icon && <span className="text-sky-500">{icon}</span>}
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </h2>
        {right && <div className="ml-auto text-xs text-slate-500">{right}</div>}
      </div>
      {children}
    </section>
  );
}

export function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div>
      <div className={`text-xl font-semibold tabular-nums ${accent ?? "text-slate-100"}`}>
        {value}
      </div>
      <div className="mt-0.5 text-xs text-slate-500">{label}</div>
    </div>
  );
}

export function Kpi({
  icon,
  label,
  value,
  accent,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="rounded-lg bg-slate-800/80 p-2 text-sky-400">{icon}</div>
      <div>
        <div className={`text-2xl font-semibold tabular-nums ${accent ?? "text-slate-100"}`}>
          {value}
        </div>
        <div className="text-xs text-slate-500">{label}</div>
      </div>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-slate-800 ${className}`} />;
}
