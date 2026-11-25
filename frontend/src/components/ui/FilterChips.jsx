import { Check } from "lucide-react";

// A row of toggle chips for one filter:
//   <FilterChips label="Severity" options={[["critical","Critical"]]} value={["critical"]} onChange={...} />
// `value` is an array (multi-select) or a single key when `single` is set; "" / [] means "all".
export function FilterChips({ label, options, value, onChange, single = false }) {
  const selected = single ? (value ? [value] : []) : value || [];
  const toggle = (key) => {
    if (single) return onChange(selected[0] === key ? "" : key);
    return onChange(selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key]);
  };
  return (
    <div role="group" aria-label={label} className="flex flex-wrap items-center gap-1.5">
      <span className="mr-1 text-xs text-muted">{label}</span>
      {options.map(([key, text]) => {
        const on = selected.includes(key);
        return (
          <button
            key={key}
            type="button"
            aria-pressed={on}
            onClick={() => toggle(key)}
            className={`press inline-flex h-8 items-center gap-1.5 rounded-sm border px-3 text-xs font-medium ${
              on ? "border-rule bg-surface font-semibold text-ink" : "border-line bg-surface text-muted hover:border-rule hover:text-ink"
            }`}
          >
            {on && <Check className="h-3 w-3" aria-hidden />}
            {text}
          </button>
        );
      })}
    </div>
  );
}
