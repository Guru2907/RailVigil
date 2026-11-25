// A definition list for facts about one record:
//   <KeyValue rows={[["Risk score", "72"], ["Dwell", "4.2 s"]]} />
export function KeyValue({ rows, className = "" }) {
  return (
    <dl className={`divide-y divide-line/70 text-sm ${className}`}>
      {rows
        .filter(([, value]) => value !== undefined && value !== null && value !== "")
        .map(([label, value]) => (
          <div key={label} className="flex items-baseline justify-between gap-4 py-2.5">
            <dt className="shrink-0 text-muted">{label}</dt>
            <dd className="tabular min-w-0 truncate text-right text-ink">{value}</dd>
          </div>
        ))}
    </dl>
  );
}
