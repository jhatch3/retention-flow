// Modal summarising a full pipeline run (dbt → train → score).
import { CheckCircle2, X } from "lucide-react";
import type { PipelineReport } from "./api";

function Row({
  label,
  headline,
  detail,
}: {
  label: string;
  headline: string;
  detail: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-[var(--ok)]" />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-[12.5px] font-medium text-[var(--fg)]">{label}</span>
          <span className="font-mono text-[11px] text-[var(--muted)]">{detail}</span>
        </div>
        <div className="text-[11.5px] text-[var(--fg-mute)]">{headline}</div>
      </div>
    </div>
  );
}

export function RunReport({
  report,
  onClose,
}: {
  report: PipelineReport;
  onClose: () => void;
}) {
  const { dbt, model, scoring, emails } = report;
  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 grid place-items-center bg-[var(--fg)]/30 p-6 backdrop-blur-sm"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="report-pop w-full max-w-md rounded-xl border border-[var(--line)] bg-[var(--surface)] shadow-2xl"
      >
        <header className="flex items-center gap-2 border-b border-[var(--line)] px-5 py-3.5">
          <span className="grid h-6 w-6 place-items-center rounded-md bg-[var(--ok-bg)]">
            <CheckCircle2 size={14} className="text-[var(--ok)]" />
          </span>
          <h2 className="text-[13px] font-semibold tracking-tight text-[var(--fg)]">
            Pipeline run complete
          </h2>
          <button
            onClick={onClose}
            className="ml-auto rounded p-1 text-[var(--muted)] hover:text-[var(--fg)]"
            aria-label="Close report"
          >
            <X size={15} />
          </button>
        </header>

        <div className="space-y-4 p-5">
          {dbt && (
            <Row
              label="dbt rebuild"
              headline={`${dbt.gold_rows.toLocaleString()} gold rows`}
              detail={`${dbt.seconds}s`}
            />
          )}
          {model && (
            <Row
              label="Model training"
              headline={`churn-xgboost v${model.version} · ROC-AUC ${model.roc_auc.toFixed(3)} · threshold ${model.threshold.toFixed(2)}`}
              detail="registered"
            />
          )}
          {scoring && (
            <Row
              label="Batch scoring"
              headline={`${scoring.predicted_churn.toLocaleString()} of ${scoring.scored_count.toLocaleString()} flagged · SHAP computed`}
              detail="serving"
            />
          )}
          {emails && (
            <Row
              label="Retention emails"
              headline={`${emails.generated} drafted for top ${emails.top_n_requested}${
                emails.failed > 0 ? ` · ${emails.failed} failed` : ""
              } · ${emails.model}`}
              detail={`${emails.elapsed_seconds.toFixed(0)}s`}
            />
          )}

          <div className="flex items-baseline justify-between border-t border-[var(--line)] pt-3">
            <span className="text-[12.5px] font-medium text-[var(--fg)]">
              Total runtime
            </span>
            <span className="font-mono text-[16px] font-semibold tabular-nums text-[var(--accent-fg)]">
              {report.total_seconds.toFixed(0)}s
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
