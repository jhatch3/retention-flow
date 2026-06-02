// Helpers + client-side fallback data for sections the API does not yet
// expose (KPI history sparklines, churn time-series). See the design handoff.

export const cx = (...xs: (string | false | null | undefined)[]): string =>
  xs.filter(Boolean).join(" ");

/** A smooth 12-point placeholder sparkline series. */
export function sparkline(seed: number, trend = 0): number[] {
  const out: number[] = [];
  let v = 48 + seed * 6;
  for (let i = 0; i < 12; i++) {
    v += Math.sin(seed + i * 0.9) * 5 + trend;
    out.push(Math.max(1, v));
  }
  return out;
}

export interface ChurnPoint {
  label: string;
  rate: number;
  predicted_churn: number;
  scored: number;
}

/** Fallback churn time-series ending near `currentRate` (no history API yet). */
export function churnSeries(currentRate: number, scored: number): ChurnPoint[] {
  const days = 90;
  const out: ChurnPoint[] = [];
  const start = currentRate * 1.05;
  for (let i = 0; i < days; i++) {
    const t = i / (days - 1);
    const rate = start + (currentRate - start) * t + Math.sin(i / 5) * 0.004;
    const d = new Date();
    d.setDate(d.getDate() - (days - 1 - i));
    out.push({
      label: d.toISOString().slice(5, 10),
      rate: Math.max(0, rate),
      predicted_churn: Math.round(scored * Math.max(0, rate)),
      scored,
    });
  }
  return out;
}

const CATEGORY_RULES: [RegExp, string][] = [
  [/recency|days_since|tenure/i, "recency"],
  [/freq|orders|count|interval/i, "frequency"],
  [/monetary|value|payment|revenue|price|freight/i, "monetary"],
  [/review|sentiment|score/i, "sentiment"],
  [/deliver|ship|late|fulfil/i, "fulfillment"],
  [/state|geo|region|city|zip|seller|categor/i, "geographic"],
];

/** Heuristic feature → category, for the importance-bar colour coding. */
export function featureCategory(name: string): string {
  for (const [re, cat] of CATEGORY_RULES) if (re.test(name)) return cat;
  return "recency";
}

/** Escape one field per RFC 4180: quote when it contains a comma, quote, or
 *  newline, and double any embedded quotes. */
function csvField(value: unknown): string {
  const s = String(value ?? "");
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** Trigger a client-side CSV download from an array of flat objects. */
export function downloadCsv(filename: string, rows: Record<string, unknown>[]): void {
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const body = rows.map((r) => headers.map((h) => csvField(r[h])).join(","));
  const csv = [headers.map(csvField).join(","), ...body].join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Open an external tool in a new tab. */
export function openExternal(url: string): void {
  window.open(url, "_blank", "noopener,noreferrer");
}
