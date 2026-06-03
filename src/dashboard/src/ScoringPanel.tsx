// Batch scoring panel — live SSE log + progress + risk histogram.
import { useEffect, useRef, useState } from "react";
import { Loader2, Play, Zap } from "lucide-react";
import { api } from "./api";
import type { Predictions, ScoreEvent } from "./api";
import { Button, Card, KvItem } from "./ui";
import { RiskHistogram } from "./charts";

function lineColor(stage: string): string {
  if (stage === "done") return "text-[var(--ok)]";
  if (stage === "error") return "text-[var(--risk)]";
  if (stage === "score") return "text-[var(--fg-soft)]";
  return "text-[var(--muted)]";
}

export function ScoringPanel({
  predictions,
  threshold,
  modelVersion,
  onScored,
}: {
  predictions?: Predictions;
  threshold: number;
  modelVersion: string;
  onScored: (p: Predictions) => void;
}) {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [log, setLog] = useState<ScoreEvent[]>([]);
  const logRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  // Close any open stream when the panel unmounts (navigating away mid-run)
  // so the connection and its setState calls don't leak.
  useEffect(() => () => esRef.current?.close(), []);

  function run() {
    setRunning(true);
    setProgress(0);
    setLog([]);
    const es = new EventSource("/api/score/stream");
    esRef.current = es;
    es.onmessage = (e) => {
      let evt: ScoreEvent;
      try {
        evt = JSON.parse(e.data);
      } catch {
        return; // ignore a malformed frame rather than throwing in the handler
      }
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

  const scored = predictions?.scored;

  return (
    <Card
      title="Batch scoring"
      subtitle={`Stream output · ${modelVersion} · threshold ${threshold}`}
      icon={<Zap size={14} />}
      right={
        <Button
          variant="primary"
          size="sm"
          onClick={run}
          disabled={running}
          leftIcon={
            running ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />
          }
        >
          {running ? "Scoring…" : "Run scoring"}
        </Button>
      }
    >
      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        {/* Left — progress + log */}
        <div>
          <div className="mb-2.5 flex items-center gap-3">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--surface-mute)]">
              <div
                className="h-full bg-[var(--accent)] transition-all duration-300"
                style={{ width: `${progress * 100}%` }}
              />
            </div>
            <span className="w-10 text-right font-mono text-[11px] tabular-nums text-[var(--muted)]">
              {Math.round(progress * 100)}%
            </span>
          </div>

          <div
            ref={logRef}
            className="h-44 overflow-auto rounded-lg border border-[var(--line)] bg-[var(--surface-soft)] p-3 font-mono text-[11.5px] leading-relaxed"
          >
            {log.length === 0 ? (
              <div className="text-[var(--muted)]">
                <span className="text-[var(--accent)]">›</span> idle — press{" "}
                <span className="text-[var(--fg-soft)]">Run scoring</span> to stream
                live progress
              </div>
            ) : (
              log.map((e, i) => (
                <div key={i} className={lineColor(e.stage)}>
                  {e.ts && <span className="text-[var(--muted)]">{e.ts}</span>}
                  <span className="mx-2 text-[var(--muted)]">│</span>
                  <span className="mr-2 inline-block w-14 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                    {e.stage}
                  </span>
                  {e.message}
                </div>
              ))
            )}
          </div>

          <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-[11.5px]">
            <KvItem
              k="Customers scored"
              v={scored ? (predictions.total ?? 0).toLocaleString() : "—"}
            />
            <KvItem
              k="Predicted churn"
              v={scored ? (predictions.predicted_churn ?? 0).toLocaleString() : "—"}
              tone="warn"
            />
            <KvItem
              k="Avg probability"
              v={scored ? (predictions.avg_probability ?? 0).toFixed(3) : "—"}
              mono
            />
            <KvItem k="Output" v="serving.predictions" mono />
          </div>
        </div>

        {/* Right — risk histogram */}
        <div>
          <div className="mb-1 flex items-baseline justify-between">
            <span className="text-[10.5px] font-medium uppercase tracking-[0.1em] text-[var(--muted)]">
              Risk distribution
            </span>
            <span className="font-mono text-[10.5px] text-[var(--muted)]">
              threshold {threshold} ─→ above flagged
            </span>
          </div>
          {scored && predictions.risk_histogram?.length ? (
            <RiskHistogram data={predictions.risk_histogram} threshold={threshold} />
          ) : (
            <div className="flex h-[180px] items-center justify-center text-[12px] text-[var(--muted)]">
              run scoring to populate the distribution
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
