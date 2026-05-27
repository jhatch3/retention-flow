// App shell — sidebar, top bar, page header.
import type { ReactNode } from "react";
import {
  Boxes,
  ChevronRight,
  Clock,
  Database,
  Gavel,
  GitBranch,
  Inbox,
  LayoutGrid,
  Menu,
  RefreshCw,
  Settings,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Button } from "./ui";
import { Logo } from "./Logo";
import { RunPipelineControl } from "./RunPipelineControl";
import type { PipelineOpts } from "./RunPipelineControl";
import { cx } from "./lib";

export type NavId =
  | "inbox"
  | "overview"
  | "pipeline"
  | "models"
  | "scoring"
  | "insights"
  | "warehouse"
  | "runs"
  | "settings";

interface NavItem {
  id: NavId;
  label: string;
  icon: LucideIcon;
}

const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Workspace",
    items: [
      { id: "inbox", label: "Inbox", icon: Inbox },
      { id: "overview", label: "Overview", icon: LayoutGrid },
      { id: "pipeline", label: "Pipeline", icon: GitBranch },
      { id: "models", label: "Models", icon: Boxes },
      { id: "scoring", label: "Scoring", icon: Zap },
      { id: "insights", label: "Insights", icon: Gavel },
    ],
  },
  {
    group: "Data",
    items: [
      { id: "warehouse", label: "Warehouse", icon: Database },
      { id: "runs", label: "Runs", icon: Clock },
    ],
  },
  {
    group: "Account",
    items: [{ id: "settings", label: "Settings", icon: Settings }],
  },
];

export function Sidebar({
  active,
  onChange,
  collapsed,
  badges,
}: {
  active: NavId;
  onChange: (id: NavId) => void;
  collapsed: boolean;
  badges?: Partial<Record<NavId, number>>;
}) {
  return (
    <aside
      className={cx(
        "shrink-0 border-r border-[var(--line)] bg-[var(--surface-deep)]",
        "sticky top-0 flex h-screen flex-col transition-[width] duration-200",
        collapsed ? "w-[60px]" : "w-[224px]",
      )}
    >
      {/* Brand */}
      <div className="flex h-[57px] items-center gap-2.5 border-b border-[var(--line)] px-4">
        <div className="relative grid h-7 w-7 shrink-0 place-items-center rounded-md bg-[var(--accent)] shadow-[0_1px_2px_rgba(0,0,0,0.12)]">
          <Logo size={16} className="text-white" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <div className="text-[13.5px] font-semibold leading-tight tracking-tight text-[var(--fg)]">
              RetentionFlow
            </div>
            <div className="font-mono text-[10.5px] leading-tight text-[var(--muted)]">
              churn · production
            </div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {NAV.map((group) => (
          <div key={group.group} className="mb-3">
            {!collapsed && (
              <div className="px-2.5 pb-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
                {group.group}
              </div>
            )}
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const isActive = active === item.id;
                const Icon = item.icon;
                return (
                  <li key={item.id}>
                    <button
                      onClick={() => onChange(item.id)}
                      className={cx(
                        "group flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[12.5px] font-medium transition",
                        isActive
                          ? "bg-[var(--surface)] text-[var(--fg)] shadow-[0_1px_2px_rgba(28,26,23,0.06)]"
                          : "text-[var(--fg-soft)] hover:bg-black/[0.03] hover:text-[var(--fg)]",
                      )}
                    >
                      <Icon
                        size={15}
                        className={cx(
                          "shrink-0",
                          isActive
                            ? "text-[var(--accent)]"
                            : "text-[var(--muted)] group-hover:text-[var(--fg-soft)]",
                        )}
                      />
                      {!collapsed && <span className="truncate">{item.label}</span>}
                      {!collapsed && !!badges?.[item.id] && (
                        <span className="ml-auto rounded-full bg-[var(--accent)] px-1.5 py-px text-[10px] font-semibold tabular-nums text-[var(--on-accent)]">
                          {badges[item.id]}
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}

export function TopBar({
  breadcrumb,
  running,
  opts,
  onOpts,
  onRunPipeline,
  onSync,
  onToggleSidebar,
}: {
  breadcrumb: string[];
  running: boolean;
  opts: PipelineOpts;
  onOpts: (o: PipelineOpts) => void;
  onRunPipeline: () => void;
  onSync: () => void;
  onToggleSidebar: () => void;
}) {
  return (
    <header className="sticky top-0 z-20 h-[57px] border-b border-[var(--line)] bg-[var(--bg)]/85 backdrop-blur-md">
      <div className="flex h-full items-center gap-3 px-6">
        <div className="flex min-w-0 items-center gap-2">
          <button
            onClick={onToggleSidebar}
            className="-ml-1 rounded p-1 text-[var(--muted)] hover:text-[var(--fg)]"
          >
            <Menu size={16} />
          </button>
          {breadcrumb.map((b, i) => (
            <span key={i} className="flex items-center gap-2">
              {i > 0 && <ChevronRight size={12} className="text-[var(--muted)]" />}
              <span
                className={cx(
                  "text-[12.5px]",
                  i === breadcrumb.length - 1
                    ? "font-medium text-[var(--fg)]"
                    : "text-[var(--muted)]",
                )}
              >
                {b}
              </span>
            </span>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onSync}
            leftIcon={<RefreshCw size={14} />}
          >
            Sync
          </Button>
          <RunPipelineControl
            opts={opts}
            onOpts={onOpts}
            onRun={onRunPipeline}
            running={running}
            compact
          />
        </div>
      </div>
    </header>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  meta,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <div className="mb-1.5 flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[color-mix(in_oklch,var(--accent)_28%,transparent)] bg-[var(--risk-bg)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-[var(--accent-fg)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
              {eyebrow}
            </span>
            {meta}
          </div>
        )}
        <h1 className="text-[24px] font-semibold leading-tight tracking-[-0.2px] text-[var(--fg)]">
          {title}
        </h1>
        {description && (
          <p className="mt-1.5 max-w-2xl text-[13px] text-[var(--fg-mute)]">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
