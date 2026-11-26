import { Link } from "react-router-dom";
import { ChevronRight, CircleAlert } from "lucide-react";

// Shared building blocks: every page uses these, so structure, spacing
// (gap-6, p-6), radius and states stay the same. Colours come only from tokens.

export { SeverityBadge, StatusBadge, Badge } from "./Badge.jsx";
export { Skeleton, SkeletonRows } from "./Skeleton.jsx";
export { Drawer } from "./Drawer.jsx";
export { Tabs } from "./Tabs.jsx";
export { FilterChips } from "./FilterChips.jsx";
export { Pagination } from "./Pagination.jsx";
export { KeyValue } from "./KeyValue.jsx";

const btnBase =
  "press inline-flex h-10 items-center justify-center gap-2 whitespace-nowrap rounded-sm px-4 text-sm font-semibold disabled:pointer-events-none disabled:opacity-50";

export const btn = {
  // The one main action of a view
  primary: `${btnBase} bg-pop text-ink hover:bg-pop-hover`,
  // Any other action
  secondary: `${btnBase} border border-rule bg-surface text-ink hover:bg-canvas-2`,
  // Same look as secondary; kept so existing callers on the page background work
  outline: `${btnBase} border border-rule bg-surface text-ink hover:bg-canvas-2`,
  // Low-emphasis action inside dense areas
  ghost: `${btnBase} text-muted hover:bg-canvas-2 hover:text-ink`,
  small: "h-8 px-3 text-xs",
};

export const inputClass =
  "h-10 w-full rounded-sm border border-rule/50 bg-paper px-3 text-sm text-ink placeholder:text-muted/80 outline-none transition-colors focus:border-accent";

export const selectClass =
  "h-10 rounded-sm border border-rule/50 bg-paper px-3 text-sm text-ink outline-none transition-colors focus:border-accent";

export const linkClass = "font-medium text-ink underline decoration-pop decoration-2 underline-offset-4 hover:text-pop-hover";

export function Card({ title, subtitle, action, children, className = "", bodyClass = "p-6" }) {
  return (
    <section className={`min-w-0 border-2 border-rule bg-surface text-ink ${className}`}>
      {(title || action) && (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-6 py-4">
          <div>
            <h2 className="text-sm font-semibold">{title}</h2>
            {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={bodyClass}>{children}</div>
    </section>
  );
}

export function PageHeader({ crumbs = [], title, description, actions, meta }) {
  return (
    <div className="mb-6">
      {crumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="mb-2 flex flex-wrap items-center gap-1 text-xs text-canvas-muted">
          {crumbs.map(([label, to], i) => (
            <span key={label} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="h-3 w-3" aria-hidden />}
              {to ? (
                <Link to={to} className="hover:text-canvas-ink">
                  {label}
                </Link>
              ) : (
                <span aria-current="page">{label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-balance text-[32px] font-bold leading-none tracking-tight text-canvas-ink">{title}</h1>
          {description && <p className="mt-1.5 max-w-[68ch] text-sm text-canvas-muted">{description}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {meta && <span className="tabular text-xs text-canvas-muted">{meta}</span>}
          {actions}
        </div>
      </div>
    </div>
  );
}

export function StatCard({ label, value, hint, tone = "default", loading }) {
  const alert = tone === "danger" && Number(value) > 0;
  return (
    <div className="border border-rule bg-surface p-5 text-ink">
      <div className="text-xs font-medium text-muted">{label}</div>
      <div className={`tabular mt-2 text-3xl font-semibold tracking-tight ${alert ? "text-sev-critical" : ""}`}>
        {loading ? <span className="skeleton inline-block h-8 w-16 align-middle" aria-label="Loading" /> : value}
      </div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      {Icon && <Icon className="mb-3 h-6 w-6 text-muted" aria-hidden />}
      {title && <p className="text-sm font-semibold text-ink">{title}</p>}
      <p className="mt-1 max-w-[52ch] text-sm text-muted">{children}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorBanner({ children }) {
  return (
    <div role="alert" className="mb-6 flex items-start gap-3 rounded-sm border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-sev-critical">
      <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="min-w-0">{children}</div>
    </div>
  );
}

// Register-style table: <Table head={[...]}>rows</Table>
export function Table({ head, children, className = "" }) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm">
        <thead className="border-b border-rule text-left">
          <tr>
            {head.map((h) => (
              <th key={h} scope="col" className="whitespace-nowrap px-4 py-3 text-xs font-medium text-muted">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line/70">{children}</tbody>
      </table>
    </div>
  );
}

export const rowClass = "cursor-pointer transition-colors hover:bg-canvas-2";
export const cellClass = "whitespace-nowrap px-4 py-3";

// A two-or-three way switch.
export function Segmented({ options, value, onChange, label }) {
  return (
    <div role="group" aria-label={label} className="inline-flex border border-rule bg-surface">
      {options.map(([key, text]) => {
        const active = key === value;
        return (
          <button
            key={key}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(key)}
            className={`press h-9 px-3.5 text-sm font-semibold ${
              active ? "bg-ink text-surface" : "text-ink hover:bg-canvas-2"
            }`}
          >
            {text}
          </button>
        );
      })}
    </div>
  );
}
