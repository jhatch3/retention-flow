// A centered ± contribution bar. Positive contributions fill rightward from
// the midpoint (risk red); negative fill leftward (ok green). The bar occupies
// half the track per side, hence width = pct / 2. Decorative — aria-hidden.

export function ShapBar({
  contrib,
  max,
  height = 14,
}: {
  contrib: number;
  max: number;
  height?: number;
}) {
  const pct = Math.min(100, (Math.abs(contrib) / max) * 100); // 0..100
  const positive = contrib > 0;
  return (
    <div
      aria-hidden="true"
      className="relative w-full rounded-sm bg-[var(--line-soft)]"
      style={{ height }}
    >
      <div className="absolute inset-y-0 left-1/2 w-px bg-[var(--muted)] opacity-30" />
      <div
        className="absolute inset-y-0 rounded-[2px]"
        style={{
          left: positive ? "50%" : `${50 - pct / 2}%`,
          width: `${pct / 2}%`,
          background: positive ? "var(--risk)" : "var(--ok)",
        }}
      />
    </div>
  );
}
