import { ChevronLeft, ChevronRight } from "lucide-react";

// Previous / next paging: <Pagination offset limit total onChange={(offset) => ...} />
// `total` may be unknown (null); then pass `hasMore` so Next knows when to stop.
export function Pagination({ offset, limit, total = null, hasMore, onChange }) {
  const from = total === 0 ? 0 : offset + 1;
  const to = total == null ? offset + limit : Math.min(offset + limit, total);
  const canNext = total == null ? Boolean(hasMore) : to < total;
  const step = "press flex h-8 w-8 items-center justify-center rounded-lg border border-line text-ink hover:border-muted/60 disabled:pointer-events-none disabled:opacity-40";
  return (
    <nav aria-label="Pages" className="flex items-center justify-between gap-3 border-t border-line px-4 py-3 text-xs text-muted">
      <span className="tabular">
        {from}–{to}
        {total != null && ` of ${total}`}
      </span>
      <div className="flex gap-2">
        <button type="button" className={step} disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))} aria-label="Previous page">
          <ChevronLeft className="h-4 w-4" aria-hidden />
        </button>
        <button type="button" className={step} disabled={!canNext} onClick={() => onChange(offset + limit)} aria-label="Next page">
          <ChevronRight className="h-4 w-4" aria-hidden />
        </button>
      </div>
    </nav>
  );
}
