// Warehouse explorer — every Postgres table and view embedded as a live
// data grid. Each card previews the first rows with a scrollable body and an
// expand button that opens the full sample fullscreen.
import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Database,
  Eye,
  Maximize2,
  Table2,
  X,
} from "lucide-react";
import { api } from "./api";
import type { WarehouseSample, WarehouseTable, WarehouseValue } from "./api";
import { Card, Pill, Skeleton } from "./ui";
import { cx } from "./lib";

// Rows previewed inside an embedded card vs. inside the fullscreen modal.
const PREVIEW_ROWS = 25;
const FULL_ROWS = 500;

// Medallion ordering + a one-line description for each schema group.
const SCHEMA_ORDER = ["raw", "synthetic", "analytics", "serving"] as const;
const SCHEMA_BLURB: Record<string, string> = {
  raw: "Bronze — untouched Olist source tables",
  synthetic: "Synthetic augmentation layered onto the raw orders",
  analytics: "Silver staging views and the gold customer-features table",
  serving: "Model-serving outputs — predictions and SHAP attributions",
};

// ─── Cell formatting ─────────────────────────────────────────────────────
function cell(v: WarehouseValue): { text: string; cls: string } {
  if (v === null || v === undefined)
    return { text: "null", cls: "italic text-[var(--muted)]/55" };
  if (typeof v === "boolean")
    return {
      text: String(v),
      cls: v ? "text-emerald-300" : "text-rose-300",
    };
  if (typeof v === "number") {
    const text = Number.isInteger(v)
      ? v.toLocaleString()
      : String(Number(v.toFixed(6)));
    return { text, cls: "tabular-nums text-[var(--fg)]" };
  }
  return { text: String(v), cls: "text-[var(--fg-soft)]" };
}

// ─── Data grid ───────────────────────────────────────────────────────────
function DataGrid({
  sample,
  className,
}: {
  sample: WarehouseSample;
  className?: string;
}) {
  if (sample.error)
    return (
      <div className="px-5 py-8 text-center text-[12.5px] text-rose-300">
        {sample.error}
      </div>
    );
  if (sample.rows.length === 0)
    return (
      <div className="px-5 py-8 text-center text-[12.5px] text-[var(--muted)]">
        No rows in this {sample.table}.
      </div>
    );

  // A column is right-aligned only when every populated value is numeric.
  const numeric = sample.columns.map((_, ci) =>
    sample.rows.some((r) => typeof r[ci] === "number") &&
    sample.rows.every((r) => r[ci] == null || typeof r[ci] === "number"),
  );

  return (
    <div className={cx("wh-fade overflow-auto", className)}>
      <table className="w-full border-collapse text-[11.5px]">
        <thead>
          <tr className="text-[10px] uppercase tracking-wide text-[var(--muted)]">
            <th className="sticky left-0 top-0 z-30 bg-[var(--surface-strong)] px-3 py-2 text-right font-medium">
              #
            </th>
            {sample.columns.map((c, i) => (
              <th
                key={c}
                className={cx(
                  "sticky top-0 z-20 whitespace-nowrap bg-[var(--surface-strong)] px-3 py-2 font-medium",
                  numeric[i] ? "text-right" : "text-left",
                )}
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sample.rows.map((row, ri) => (
            <tr
              key={ri}
              className="border-t border-[var(--line)] transition-colors hover:bg-white/[0.03]"
            >
              <td className="sticky left-0 z-10 bg-[var(--surface)] px-3 py-1.5 text-right font-mono text-[10.5px] tabular-nums text-[var(--muted)]">
                {ri + 1}
              </td>
              {row.map((v, ci) => {
                const c = cell(v);
                return (
                  <td
                    key={ci}
                    title={c.text}
                    className={cx(
                      "max-w-[300px] truncate px-3 py-1.5 font-mono",
                      numeric[ci] ? "text-right" : "text-left",
                      c.cls,
                    )}
                  >
                    {c.text}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Fullscreen modal ────────────────────────────────────────────────────
function ExpandedTable({
  table,
  onClose,
}: {
  table: WarehouseTable;
  onClose: () => void;
}) {
  const [sample, setSample] = useState<WarehouseSample>();
  const [closing, setClosing] = useState(false);
  const timer = useRef<number>();

  // Animate out, then unmount.
  function requestClose() {
    if (closing) return;
    setClosing(true);
    timer.current = window.setTimeout(onClose, 170);
  }

  useEffect(() => {
    let alive = true;
    api
      .warehouseSample(table.schema, table.name, FULL_ROWS)
      .then((s) => alive && setSample(s))
      .catch(
        (e) => alive && setSample({ ...EMPTY_SAMPLE(table), error: String(e) }),
      );
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && requestClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      alive = false;
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      window.clearTimeout(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [table.schema, table.name]);

  const shown = sample?.rows.length ?? 0;

  return (
    <div
      onClick={requestClose}
      className={cx(
        "fixed inset-0 z-50 grid place-items-stretch bg-black/65 p-4 backdrop-blur-sm sm:p-8",
        closing ? "wh-backdrop-out" : "wh-fade",
      )}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={cx(
          "flex min-h-0 flex-col overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface)] shadow-2xl",
          closing ? "wh-modal-out" : "wh-modal-in",
        )}
      >
        <header className="flex items-center gap-2.5 border-b border-[var(--line)] px-5 py-3.5">
          <span className="text-[var(--muted)]">
            {table.kind === "view" ? <Eye size={14} /> : <Table2 size={14} />}
          </span>
          <div className="min-w-0">
            <h2 className="truncate font-mono text-[13px] font-semibold tracking-tight text-[var(--fg)]">
              {table.schema}.{table.name}
            </h2>
            <p className="mt-0.5 text-[11px] text-[var(--muted)]">
              {table.row_count.toLocaleString()} rows ·{" "}
              {table.columns.length} columns
            </p>
          </div>
          <Pill tone={table.kind === "view" ? "info" : "accent"} className="ml-auto">
            {table.kind}
          </Pill>
          <button
            onClick={requestClose}
            className="rounded-md p-1 text-[var(--muted)] transition-colors hover:bg-white/[0.06] hover:text-[var(--fg)]"
          >
            <X size={16} />
          </button>
        </header>

        {!sample ? (
          <div className="p-5">
            <Skeleton className="h-[60vh] w-full" />
          </div>
        ) : (
          <DataGrid sample={sample} className="min-h-0 flex-1" />
        )}

        <footer className="border-t border-[var(--line)] px-5 py-2 text-[10.5px] text-[var(--muted)]">
          Showing {shown.toLocaleString()} of{" "}
          {table.row_count.toLocaleString()} rows
          {table.row_count > FULL_ROWS && ` · capped at ${FULL_ROWS}`} ·
          press Esc to close
        </footer>
      </div>
    </div>
  );
}

const EMPTY_SAMPLE = (t: WarehouseTable): WarehouseSample => ({
  schema: t.schema,
  table: t.name,
  columns: [],
  rows: [],
  row_limit: 0,
});

// ─── Single table card ───────────────────────────────────────────────────
function TableCard({ table, index }: { table: WarehouseTable; index: number }) {
  const [sample, setSample] = useState<WarehouseSample>();
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let alive = true;
    api
      .warehouseSample(table.schema, table.name, PREVIEW_ROWS)
      .then((s) => alive && setSample(s))
      .catch(
        (e) => alive && setSample({ ...EMPTY_SAMPLE(table), error: String(e) }),
      );
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [table.schema, table.name]);

  const shown = sample?.rows.length ?? 0;

  return (
    <>
      <section
        className="wh-rise overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface)] shadow-[0_1px_0_rgba(255,255,255,0.03)_inset,0_1px_2px_rgba(0,0,0,0.4)] transition-colors hover:border-[var(--line-strong)]"
        style={{ animationDelay: `${Math.min(index, 8) * 45}ms` }}
      >
        <header className="flex items-center gap-2.5 border-b border-[var(--line)] px-5 py-3">
          <span className="text-[var(--muted)]">
            {table.kind === "view" ? <Eye size={14} /> : <Table2 size={14} />}
          </span>
          <div className="min-w-0">
            <h3 className="truncate font-mono text-[12.5px] font-semibold tracking-tight text-[var(--fg)]">
              {table.schema}.{table.name}
            </h3>
            <p className="mt-0.5 text-[10.5px] text-[var(--muted)]">
              {table.row_count.toLocaleString()} rows ·{" "}
              {table.columns.length} columns
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Pill tone={table.kind === "view" ? "info" : "accent"}>
              {table.kind}
            </Pill>
            <button
              onClick={() => setExpanded(true)}
              title="Expand to fullscreen"
              className="grid h-7 w-7 place-items-center rounded-md border border-[var(--line)] text-[var(--muted)] transition-all duration-150 hover:scale-105 hover:border-[var(--line-strong)] hover:bg-white/[0.05] hover:text-[var(--fg)] active:scale-95"
            >
              <Maximize2 size={13} />
            </button>
          </div>
        </header>

        {!sample ? (
          <div className="p-5">
            <Skeleton className="h-44 w-full" />
          </div>
        ) : (
          <DataGrid sample={sample} className="max-h-[336px]" />
        )}

        {sample && !sample.error && sample.rows.length > 0 && (
          <footer className="border-t border-[var(--line)] px-5 py-2 text-[10.5px] text-[var(--muted)]">
            Showing {shown.toLocaleString()} of{" "}
            {table.row_count.toLocaleString()} rows
            {table.row_count > shown && " · scroll for more"}
          </footer>
        )}
      </section>

      {expanded && (
        <ExpandedTable table={table} onClose={() => setExpanded(false)} />
      )}
    </>
  );
}

// ─── Section ─────────────────────────────────────────────────────────────
export function WarehouseTables() {
  const [tables, setTables] = useState<WarehouseTable[]>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    api
      .warehouseTables()
      .then((r) => setTables(r.tables))
      .catch((e) => setError(String(e)));
  }, []);

  if (error)
    return (
      <Card title="Tables & views" icon={<Database size={14} />}>
        <div className="flex items-center gap-2 text-[12.5px] text-rose-300">
          <AlertTriangle size={14} />
          {error} — could not reach the warehouse.
        </div>
      </Card>
    );

  if (!tables)
    return (
      <div className="space-y-4">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-64 w-full" />
        ))}
      </div>
    );

  // Group by schema, in medallion order.
  const groups = SCHEMA_ORDER.map((schema) => ({
    schema,
    items: tables.filter((t) => t.schema === schema),
  })).filter((g) => g.items.length > 0);

  let cardIndex = 0;

  return (
    <div className="space-y-8">
      {groups.map((group) => (
        <div key={group.schema}>
          <div className="mb-3 flex items-baseline gap-3">
            <h2 className="font-mono text-[13px] font-semibold tracking-tight text-[var(--fg)]">
              {group.schema}
            </h2>
            <span className="text-[11px] text-[var(--muted)]">
              {SCHEMA_BLURB[group.schema]}
            </span>
            <span className="ml-auto font-mono text-[10.5px] text-[var(--muted)]">
              {group.items.length} object{group.items.length === 1 ? "" : "s"}
            </span>
          </div>
          <div className="space-y-4">
            {group.items.map((t) => (
              <TableCard
                key={`${t.schema}.${t.name}`}
                table={t}
                index={cardIndex++}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
