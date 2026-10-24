import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";

// Shared building blocks so every page has the same structure, spacing
// (gap-6, p-6) and states. Colours come only from the theme tokens.

const btnBase =
  "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-semibold transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50";

export const btn = {
  // Primary action on a card or on the canvas
  primary: `${btnBase} bg-accent text-accent-ink shadow-sm hover:bg-accent-hover`,
  // Secondary action on a card
  secondary: `${btnBase} border border-line bg-paper text-ink hover:bg-surface-2`,
  // Secondary action placed directly on the canvas
  outline: `${btnBase} border border-signal/60 text-signal hover:bg-signal/10`,
  small: "px-3 py-1.5 text-xs",
};

export const inputClass =
  "w-full rounded-md border border-line bg-paper px-3 py-2 text-sm text-ink placeholder:text-muted/70 outline-none transition focus:border-ink/40 focus:ring-2 focus:ring-signal/30";

export const selectClass =
  "rounded-md border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus:ring-2 focus:ring-signal/30";

export const linkClass = "font-medium text-ink underline decoration-ink/25 underline-offset-4 hover:decoration-ink";

export function Card({ title, subtitle, action, children, className = "", bodyClass = "p-6" }) {
  return (
    <section className={`min-w-0 rounded-lg border border-line bg-surface text-ink shadow-lg shadow-black/20 ${className}`}>
      {(title || action) && (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-6 py-4">
          <div>
            <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
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
    <div className="mb-6 border-b border-canvas-line pb-6">
      <nav aria-label="Breadcrumb" className="mb-3 flex flex-wrap items-center gap-1 font-mono text-[11px] uppercase tracking-wider text-canvas-muted">
        <Link to="/" className="hover:text-canvas-ink">
          Home
        </Link>
        {crumbs.map(([label, to]) => (
          <span key={label} className="flex items-center gap-1">
            <ChevronRight className="h-3 w-3" aria-hidden />
            {to ? (
              <Link to={to} className="hover:text-canvas-ink">
                {label}
              </Link>
            ) : (
              <span className="text-canvas-ink" aria-current="page">
                {label}
              </span>
            )}
          </span>
        ))}
      </nav>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-canvas-ink md:text-3xl">{title}</h1>
          {description && <p className="mt-1.5 max-w-2xl text-sm text-canvas-muted">{description}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {meta && <span className="font-mono text-[11px] text-canvas-muted">{meta}</span>}
          {actions}
        </div>
      </div>
    </div>
  );
}

export function StatCard({ label, value, hint, tone = "default", loading }) {
  const bar = tone === "danger" ? "bg-danger" : tone === "signal" ? "bg-signal" : "bg-accent";
  return (
    <div className="relative overflow-hidden rounded-lg border border-line bg-surface p-6 text-ink shadow-lg shadow-black/20">
      <span className={`absolute inset-y-0 left-0 w-1 ${bar}`} aria-hidden />
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">{label}</div>
      <div className={`tabular mt-2 font-mono text-3xl font-semibold ${tone === "danger" && value > 0 ? "text-danger" : ""}`}>
        {loading ? "…" : value}
      </div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}

export function EmptyState({ children }) {
  return <p className="py-8 text-center text-sm text-muted">{children}</p>;
}

export function ErrorBanner({ children }) {
  return (
    <div role="alert" className="mb-6 rounded-md border border-danger/40 bg-danger/10 px-4 py-3 font-mono text-sm text-danger obsidian:text-rose-300">
      {children}
    </div>
  );
}

// Register-style table: <Table head={[...]}>rows</Table>
export function Table({ head, children, className = "" }) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm">
        <thead className="bg-surface-2 text-left">
          <tr>
            {head.map((h) => (
              <th key={h} scope="col" className="whitespace-nowrap px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line bg-paper">{children}</tbody>
      </table>
    </div>
  );
}

export const rowClass = "cursor-pointer transition-colors hover:bg-surface-2";
export const cellClass = "whitespace-nowrap px-4 py-3";

export function Segmented({ options, value, onChange, onCanvas = false, label }) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className={`inline-flex rounded-md border p-0.5 ${onCanvas ? "border-canvas-line bg-canvas-2" : "border-line bg-surface-2"}`}
    >
      {options.map(([key, text]) => {
        const active = key === value;
        return (
          <button
            key={key}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(key)}
            className={`rounded px-4 py-1.5 text-sm font-medium transition ${
              active
                ? onCanvas
                  ? "bg-surface text-ink shadow"
                  : "bg-accent text-accent-ink"
                : onCanvas
                  ? "text-canvas-muted hover:text-canvas-ink"
                  : "text-muted hover:text-ink"
            }`}
          >
            {text}
          </button>
        );
      })}
    </div>
  );
}
