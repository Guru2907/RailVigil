// View switch for a page: <Tabs tabs={[["board","Board", Icon]]} value onChange label="Site views" />
// The caller renders the panel and may keep `value` in the URL. Arrow keys move between tabs.
export function Tabs({ tabs, value, onChange, label }) {
  const onKeyDown = (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const i = tabs.findIndex(([key]) => key === value);
    const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
    onChange(next[0]);
    e.currentTarget.querySelector(`[data-tab="${next[0]}"]`)?.focus();
  };
  return (
    <div role="tablist" aria-label={label} onKeyDown={onKeyDown} className="flex gap-1 border-b border-line">
      {tabs.map(([key, text, Icon]) => {
        const active = key === value;
        return (
          <button
            key={key}
            type="button"
            role="tab"
            data-tab={key}
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(key)}
            className={`-mb-px flex h-10 items-center gap-2 border-b-2 px-3 text-sm font-medium transition-colors ${
              active ? "border-pop text-ink" : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {Icon && <Icon className="h-4 w-4" aria-hidden />}
            {text}
          </button>
        );
      })}
    </div>
  );
}
