import { useEffect, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Loader2, Play, Zap } from "lucide-react";
import { api } from "./api";
import type { Predictions, ScoreEvent } from "./api";
import { Card, Stat, chartTooltip } from "./ui";

export function ScoringPanel({
  preds,
  onScored,
}: {
  preds?: Predictions;
  onScored: (p: Predictions) => void;
}) {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [log, setLog] = useState<ScoreEvent[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  function run() {
    setRunning(true);
    setProgress(0);
    setLog([]);
    const es = new EventSource("/api/score/stream");
    es.onmessage = (e) => {
      const evt: ScoreEvent = JSON.parse(e.data);
      setLog((l) => [...l, evt]);
      setProgress(evt.progress);
      if (evt.done) {
        es.close();
        setRunning(false);
        api.predictions().then(onScored).catch(() => undefined);
      }
    };
    es.onerror = () => {
      es.close();
      setRunning(false);
      setLog((l) => [
        ...l,
        { stage: "error", message: "stream error — is the API running?", progress: 0, ts: "" },
      ]);
    };
  }

  const hist =
    preds?.risk_histogram?.map((h) => ({
      band: `${(h.bucket - 1) * 10}-${h.bucket * 10}`,
      count: h.count,
    })) ?? [];

  return (
    <Card title="Batch scoring" icon={<Zap size={15} />}>
      <button
        onClick={run}
        disabled={running}
        className="mb-3 inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500 disabled:opacity-50"
      >
        {running ? (
          <Loader2 size={15} className="animate-spin" />
        ) : (
          <Play size={15} />
        )}
        {running ? "Scoring…" : "Run batch scoring"}
      </button>

      {(running || log.length > 0) && (
        <>
          <div className="mb-2 h-1.5 w-full overflow-hidden rounded bg-slate-800">
            <div
              className="h-full bg-sky-500 transition-all duration-300"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
          <div
            ref={logRef}
            className="mb-5 h-36 overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-xs leading-relaxed"
          >
            {log.map((e, i) => (
              <div
                key={i}
                className={
                  e.stage === "done"
                    ? "text-emerald-400"
                    : e.stage === "error"
                      ? "text-red-400"
                      : "text-slate-400"
                }
              >
                {e.ts && <span className="text-slate-600">{e.ts} </span>}
                {e.message}
              </div>
            ))}
          </div>
        </>
      )}

      {preds?.scored ? (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          <div>
            <div className="mb-3 flex flex-wrap gap-6">
              <Stat label="customers scored" value={(preds.total ?? 0).toLocaleString()} />
              <Stat
                label="predicted churn"
                value={(preds.predicted_churn ?? 0).toLocaleString()}
                accent="text-amber-400"
              />
              <Stat
                label="avg probability"
                value={(preds.avg_probability ?? 0).toFixed(3)}
              />
            </div>
            <div className="mb-1 text-xs text-slate-500">
              churn-probability distribution (%)
            </div>
            <ResponsiveContainer width="100%" height={150}>
              <BarChart data={hist}>
                <XAxis dataKey="band" stroke="#64748b" fontSize={10} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip contentStyle={chartTooltip} cursor={{ fill: "#1e293b" }} />
                <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                  {hist.map((_, i) => (
                    <Cell key={i} fill={i >= 7 ? "#f59e0b" : "#38bdf8"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div>
            <div className="mb-2 text-xs text-slate-500">
              highest-risk customers
            </div>
            <table className="w-full text-xs">
              <tbody>
                {preds.top_at_risk?.map((c) => (
                  <tr key={c.customer_unique_id} className="border-t border-slate-800">
                    <td className="py-1.5 font-mono text-slate-400">
                      {c.customer_unique_id.slice(0, 12)}…
                    </td>
                    <td className="py-1.5 text-right font-semibold tabular-nums text-amber-400">
                      {(c.churn_probability * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        !running &&
        log.length === 0 && (
          <p className="text-sm text-slate-500">
            No predictions yet — run batch scoring.
          </p>
        )
      )}
    </Card>
  );
}
