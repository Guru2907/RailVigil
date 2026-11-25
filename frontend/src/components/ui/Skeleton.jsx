// Loading placeholders shaped like the content they stand in for.

export function Skeleton({ className = "h-4 w-full" }) {
  return <span className={`skeleton block ${className}`} aria-hidden />;
}

// Placeholder rows for a table body: <SkeletonRows rows={6} cols={5} />
export function SkeletonRows({ rows = 6, cols = 4 }) {
  return Array.from({ length: rows }, (_, r) => (
    <tr key={r} aria-hidden>
      {Array.from({ length: cols }, (_, c) => (
        <td key={c} className="px-4 py-3.5">
          <Skeleton className={`h-3.5 ${c === 0 ? "w-24" : "w-full max-w-32"}`} />
        </td>
      ))}
    </tr>
  ));
}
