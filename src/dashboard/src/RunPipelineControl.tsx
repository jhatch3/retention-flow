// Split button "Run pipeline" + chevron popover for the run options
// (retrain model · generate retention emails · top-N).
import { useEffect, useRef, useState } from "react";
import {
  Brain,
  Check,
  ChevronDown,
  Loader2,
  Mail,
  Play,
} from "lucide-react";
import { cx } from "./lib";

export interface PipelineOpts {
  train: boolean;
  emails: boolean;
  /** Top-N at-risk customers to draft emails for when ``emails`` is on. */
  topN: number;
}

const MIN_TOP_N = 1;
const MAX_TOP_N = 500;

export function RunPipelineControl({
  opts,
  onOpts,
  onRun,
  running,
  compact = false,
  className = "",
}: {
  opts: PipelineOpts;
  onOpts: (next: PipelineOpts) => void;
  onRun: () => void;
  running: boolean;
  compact?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [topNDraft, setTopNDraft] = useState(String(opts.topN));
  const ref = useRef<HTMLDivElement>(null);

  // Keep the input in sync if `opts.topN` is updated from elsewhere.
  useEffect(() => {
    setTopNDraft(String(opts.topN));
  }, [opts.topN]);

  // Close on outside-click / Escape.
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function commitTopN() {
    const n = Number.parseInt(topNDraft, 10);
    const clamped = Number.isFinite(n)
      ? Math.max(MIN_TOP_N, Math.min(n, MAX_TOP_N))
      : opts.topN;
    setTopNDraft(String(clamped));
    if (clamped !== opts.topN) onOpts({ ...opts, topN: clamped });
  }

  const label = running
    ? "Running…"
    : opts.train && opts.emails
      ? `Run pipeline · top ${opts.topN}`
      : opts.train
        ? "Rebuild + train + score"
        : opts.emails
          ? `Rebuild + score + top ${opts.topN} emails`
          : "Rebuild + score";

  const sizeMain = compact ? "h-7 text-[12px] px-2.5" : "h-8 text-[12.5px] px-3";
  const sizeChevron = compact ? "h-7 w-7" : "h-8 w-8";

  return (
    <div ref={ref} className={cx("relative inline-flex", className)}>
      <button
        type="button"
        onClick={onRun}
        disabled={running}
        title={label}
        className={cx(
          "inline-flex items-center gap-1.5 rounded-l-lg border border-r-0 border-[var(--accent)]",
          "bg-[var(--accent)] font-medium tracking-tight text-[var(--on-accent)]",
          "shadow-[0_1px_2px_rgba(196,74,45,0.18)]",
          "transition hover:bg-[var(--accent-hov)] hover:border-[var(--accent-hov)]",
          "disabled:cursor-not-allowed disabled:opacity-60",
          sizeMain,
        )}
      >
        {running ? (
          <Loader2 size={13} className="animate-spin" />
        ) : (
          <Play size={13} />
        )}
        {label}
      </button>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        disabled={running}
        aria-haspopup="menu"
        aria-expanded={open}
        title="Pipeline options"
        className={cx(
          "inline-flex shrink-0 items-center justify-center rounded-r-lg border border-[var(--accent)]",
          "bg-[var(--accent)] text-[var(--on-accent)]",
          "transition hover:bg-[var(--accent-hov)] hover:border-[var(--accent-hov)]",
          "border-l-[color-mix(in_oklch,var(--on-accent)_22%,transparent)]",
          "disabled:cursor-not-allowed disabled:opacity-60",
          sizeChevron,
        )}
      >
        <ChevronDown
          size={14}
          className={cx("transition-transform", open && "rotate-180")}
        />
      </button>

      {open && (
        <div
          role="menu"
          className={cx(
            "absolute right-0 top-[calc(100%+6px)] z-30 w-[300px]",
            "rounded-xl border border-[var(--line)] bg-[var(--surface)]",
            "shadow-[0_8px_24px_rgba(28,26,23,0.10)] p-2",
          )}
        >
          <div className="px-2 pb-1.5 pt-1 font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
            Pipeline options
          </div>
          <Toggle
            icon={<Brain size={14} />}
            label="Retrain churn model"
            sub="Refit XGBoost on the rebuilt gold table and register as champion."
            checked={opts.train}
            onChange={(v) => onOpts({ ...opts, train: v })}
          />
          <Toggle
            icon={<Mail size={14} />}
            label="Generate retention emails"
            sub="Draft emails for the top-N at-risk customers via Claude."
            checked={opts.emails}
            onChange={(v) => onOpts({ ...opts, emails: v })}
          />

          <div
            className={cx(
              "flex items-center justify-between gap-2 rounded-md px-2 py-2 transition",
              !opts.emails && "opacity-50",
            )}
          >
            <div className="min-w-0 flex-1">
              <div className="text-[12.5px] font-medium text-[var(--fg)]">
                Top-N customers
              </div>
              <div className="mt-0.5 text-[11px] leading-snug text-[var(--fg-mute)]">
                1 – {MAX_TOP_N}. Higher N = more LLM cost &amp; runtime.
              </div>
            </div>
            <input
              type="number"
              min={MIN_TOP_N}
              max={MAX_TOP_N}
              step={1}
              disabled={!opts.emails || running}
              value={topNDraft}
              onChange={(e) => setTopNDraft(e.target.value)}
              onBlur={commitTopN}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  commitTopN();
                  (e.currentTarget as HTMLInputElement).blur();
                }
              }}
              className={cx(
                "h-7 w-[68px] rounded-md border border-[var(--line)] bg-[var(--surface)]",
                "px-2 text-right font-mono text-[12.5px] tabular-nums text-[var(--fg)]",
                "focus:border-[var(--accent)] focus:outline-none",
                "disabled:cursor-not-allowed disabled:bg-[var(--surface-mute)]",
              )}
            />
          </div>

          <div className="mt-1.5 border-t border-[var(--line)] pt-2">
            <button
              type="button"
              onClick={() => {
                commitTopN();
                setOpen(false);
                onRun();
              }}
              disabled={running}
              className={cx(
                "flex w-full items-center justify-center gap-1.5 rounded-md",
                "bg-[var(--accent)] px-3 py-2 text-[12.5px] font-semibold text-[var(--on-accent)]",
                "transition hover:bg-[var(--accent-hov)]",
                "disabled:cursor-not-allowed disabled:opacity-60",
              )}
            >
              {running ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Play size={13} />
              )}
              Run pipeline
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Toggle({
  icon,
  label,
  sub,
  checked,
  onChange,
}: {
  icon: React.ReactNode;
  label: string;
  sub: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      role="menuitemcheckbox"
      aria-checked={checked}
      className={cx(
        "flex w-full items-start gap-2.5 rounded-md px-2 py-1.5 text-left transition",
        "hover:bg-[var(--surface-soft)]",
      )}
    >
      <span
        className={cx(
          "mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border transition",
          checked
            ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--on-accent)]"
            : "border-[var(--line-strong)] bg-[var(--surface)] text-transparent",
        )}
      >
        {checked && <Check size={11} strokeWidth={3} />}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-1.5 text-[12.5px] font-medium text-[var(--fg)]">
          <span className="text-[var(--muted)]">{icon}</span>
          {label}
        </span>
        <span className="mt-0.5 block text-[11px] leading-snug text-[var(--fg-mute)]">
          {sub}
        </span>
      </span>
    </button>
  );
}
