// High-fidelity SVG asset graph of the medallion pipeline — elevated service
// cards (Railway-style), smooth connectors, live state from the
// /api/pipeline/rebuild/stream events.
import { Loader2, Play } from "lucide-react";
import type { PipelineStatus, WarehouseData } from "./api";
import { Button, Card } from "./ui";
import { cx } from "./lib";

type NodeState = "idle" | "running" | "done" | "warn" | "error";

interface DagNode {
  id: string;
  label: string;
  col: number;
  row: number;
  kind: "source" | "view" | "table" | "model";
}

const STAGING = [
  "stg_customers",
  "stg_orders",
  "stg_order_items",
  "stg_order_payments",
  "stg_order_reviews",
  "stg_products",
];

const NODES: DagNode[] = [
  { id: "database", label: "database", col: 0, row: 0, kind: "source" },
  ...STAGING.map((id, row): DagNode => ({ id, label: id, col: 1, row, kind: "view" })),
  { id: "int_customer_orders", label: "int_customer_orders", col: 2, row: 0, kind: "view" },
  { id: "customer_features", label: "customer_features", col: 3, row: 0, kind: "table" },
  { id: "churn_model", label: "churn_model", col: 4, row: 0, kind: "model" },
];

const EDGES: [string, string][] = [
  ...STAGING.map((s): [string, string] => ["database", s]),
  ...STAGING.map((s): [string, string] => [s, "int_customer_orders"]),
  ["int_customer_orders", "customer_features"],
  ["customer_features", "churn_model"],
];

const COL_LABELS = ["Sources", "Staging · silver", "Intermediate", "Gold", "Model"];

const NODE_W = 200;
const NODE_H = 56;
const GAP = 22;
const TOP = 50;
const COL_DX = 272;
const COL_X = COL_LABELS.map((_, i) => 18 + i * COL_DX);
const SPAN = 6 * NODE_H + 5 * GAP;
const VB_W = COL_X[4] + NODE_W + 18;
const VB_H = TOP + SPAN + 16;

function layout(): Record<string, { x: number; y: number }> {
  const byCol: Record<number, DagNode[]> = {};
  for (const n of NODES) (byCol[n.col] ??= []).push(n);
  const pos: Record<string, { x: number; y: number }> = {};
  for (const [col, nodes] of Object.entries(byCol)) {
    const blockH = nodes.length * NODE_H + (nodes.length - 1) * GAP;
    const startY = TOP + (SPAN - blockH) / 2;
    nodes
      .sort((a, b) => a.row - b.row)
      .forEach((n, i) => {
        pos[n.id] = { x: COL_X[Number(col)], y: startY + i * (NODE_H + GAP) };
      });
  }
  return pos;
}
const POS = layout();

const STATE: Record<NodeState, { accent: string; stroke: string; dot: string }> = {
  idle: { accent: "var(--muted)", stroke: "var(--line)", dot: "var(--muted)" },
  running: { accent: "var(--accent)", stroke: "var(--accent)", dot: "var(--accent)" },
  done: {
    accent: "oklch(0.74 0.15 150)",
    stroke: "color-mix(in oklch, oklch(0.74 0.15 150) 50%, var(--line))",
    dot: "oklch(0.74 0.15 150)",
  },
  warn: {
    accent: "oklch(0.8 0.14 70)",
    stroke: "color-mix(in oklch, oklch(0.8 0.14 70) 50%, var(--line))",
    dot: "oklch(0.8 0.14 70)",
  },
  error: {
    accent: "oklch(0.7 0.2 25)",
    stroke: "color-mix(in oklch, oklch(0.7 0.2 25) 55%, var(--line))",
    dot: "oklch(0.7 0.2 25)",
  },
};

function edgePath(from: { x: number; y: number }, to: { x: number; y: number }): string {
  const x1 = from.x + NODE_W;
  const y1 = from.y + NODE_H / 2;
  const x2 = to.x - 7;
  const y2 = to.y + NODE_H / 2;
  const dx = Math.max(40, (x2 - x1) * 0.55);
  return `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`;
}

export function PipelineDag({
  pipeline,
  data,
  championVersion,
  running,
  liveState,
  onRun,
}: {
  pipeline?: PipelineStatus;
  data?: WarehouseData;
  championVersion?: string | null;
  running: boolean;
  liveState: Record<string, string>;
  onRun: () => void;
}) {
  function nodeState(node: DagNode): NodeState {
    if (node.kind === "source") return "done";
    if (node.kind === "model") {
      if (!running) return "done";
      const s = liveState[node.id];
      return s === "done" ? "done" : s === "running" ? "running" : "idle";
    }
    if (running) {
      const s = liveState[node.id];
      return s === "done" ? "done" : s === "error" ? "error" : "running";
    }
    const model = pipeline?.models?.find((m) => m.name === node.id);
    if (!model) return "idle";
    return model.status === "success"
      ? "done"
      : model.status === "warning"
        ? "warn"
        : "error";
  }

  function meta(node: DagNode, st: NodeState): string {
    if (st === "running") return "running…";
    if (st === "idle") return "queued";
    if (st === "error") return "failed";
    if (st === "warn") return "warning";
    if (node.id === "database") {
      const syn = data ? `${Math.round(data.synthetic_orders / 1000)}K synthetic` : "synthetic";
      return `9 Olist tables + ${syn} orders`;
    }
    if (node.id === "customer_features")
      return data ? `${data.gold_rows.toLocaleString()} rows` : "materialized";
    if (node.id === "churn_model")
      return championVersion ? `champion · v${championVersion}` : "registered";
    const model = pipeline?.models?.find((m) => m.name === node.id);
    return model ? `materialized · ${model.execution_time.toFixed(2)}s` : "materialized";
  }

  const states: Record<string, NodeState> = {};
  for (const n of NODES) states[n.id] = nodeState(n);

  return (
    <Card
      title="Pipeline DAG"
      subtitle="medallion asset graph · live during a rebuild"
      right={
        <Button
          variant="primary"
          size="sm"
          onClick={onRun}
          disabled={running}
          leftIcon={
            running ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />
          }
        >
          {running ? "Running…" : "Run pipeline"}
        </Button>
      }
    >
      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="w-full" role="img">
        <defs>
          <marker
            id="dag-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M0,1 L9,5 L0,9 z" fill="var(--line-strong)" />
          </marker>
          <filter id="dag-shadow" x="-20%" y="-30%" width="140%" height="170%">
            <feDropShadow dx="0" dy="2" stdDeviation="3.5" floodColor="#000" floodOpacity="0.5" />
          </filter>
        </defs>

        {/* Column headers */}
        {COL_LABELS.map((label, i) => (
          <text
            key={label}
            x={COL_X[i]}
            y={28}
            className="fill-[var(--muted)] text-[10.5px] font-medium uppercase"
            style={{ letterSpacing: "0.09em" }}
          >
            {label}
          </text>
        ))}

        {/* Edges */}
        {EDGES.map(([from, to], i) => {
          const flowing = running && states[to] === "running";
          return (
            <path
              key={i}
              d={edgePath(POS[from], POS[to])}
              fill="none"
              stroke={
                states[to] === "done"
                  ? "color-mix(in oklch, oklch(0.74 0.15 150) 48%, transparent)"
                  : "var(--line-strong)"
              }
              strokeWidth={1.5}
              strokeLinecap="round"
              markerEnd="url(#dag-arrow)"
              className={cx(flowing && "dag-edge-flow")}
              opacity={0.85}
            />
          );
        })}

        {/* Nodes — elevated service cards */}
        {NODES.map((n) => {
          const p = POS[n.id];
          const st = states[n.id];
          const s = STATE[st];
          return (
            <g key={n.id}>
              <rect
                x={p.x}
                y={p.y}
                width={NODE_W}
                height={NODE_H}
                rx={12}
                fill="var(--surface-strong)"
                stroke={s.stroke}
                strokeWidth={1.5}
                filter="url(#dag-shadow)"
                className={cx(st === "running" && "animate-pulse")}
              />
              <rect
                x={p.x + 1.5}
                y={p.y + 11}
                width={3.5}
                height={NODE_H - 22}
                rx={2}
                fill={s.accent}
              />
              <circle cx={p.x + 18} cy={p.y + 21} r={3.4} fill={s.dot} />
              <text
                x={p.x + 28}
                y={p.y + 24.5}
                className="text-[12px] font-medium"
                style={{ fill: "var(--fg)", fontFamily: "var(--font-mono)" }}
              >
                {n.label}
              </text>
              <text
                x={p.x + 28}
                y={p.y + 41}
                className="text-[10px]"
                style={{ fill: st === "idle" ? "var(--muted)" : s.accent }}
              >
                {meta(n, st)}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 border-t border-[var(--line)] pt-3 text-[10.5px] text-[var(--muted)]">
        {(
          [
            ["done", "materialized"],
            ["running", "running"],
            ["idle", "queued"],
            ["error", "failed"],
          ] as [NodeState, string][]
        ).map(([state, label]) => (
          <span key={state} className="flex items-center gap-1.5">
            <span
              className="h-2 w-2 rounded-full"
              style={{ background: STATE[state].dot }}
            />
            {label}
          </span>
        ))}
      </div>
    </Card>
  );
}
