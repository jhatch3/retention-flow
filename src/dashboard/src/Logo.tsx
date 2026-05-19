// RetentionFlow brand mark — an ascending three-node flow, echoing the
// pipeline DAG. Inherits `currentColor`, so it tints to its container.
export function Logo({
  size = 24,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M5 17 L12 12 L19 7"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.9"
      />
      <circle cx="5" cy="17" r="2.5" fill="currentColor" />
      <circle cx="12" cy="12" r="2.5" fill="currentColor" />
      <circle cx="19" cy="7" r="2.8" fill="currentColor" />
    </svg>
  );
}
