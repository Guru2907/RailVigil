export function fmtTime(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(Math.floor(sec % 60)).padStart(2, "0");
  return `${m}:${s}`;
}

export function fmtPct(v) {
  return `${Math.round(v <= 1 ? v * 100 : v)}%`;
}

// Same visual language as encroachment severities (utils/encroachmentFormat.js).
export function sevClass(sev) {
  const s = (sev || "").toUpperCase();
  const base = "inline-flex items-center rounded ring-1 ring-inset uppercase tracking-wider";
  if (s === "CRITICAL") return `${base} bg-danger/12 text-danger ring-danger/40 animate-pulse obsidian:text-rose-300`;
  if (s === "HIGH") return `${base} bg-orange-500/12 text-orange-700 ring-orange-500/40 animate-pulse obsidian:text-orange-300`;
  if (s === "MEDIUM" || s === "MED") return `${base} bg-amber-400/15 text-amber-800 ring-amber-500/40 obsidian:text-amber-300`;
  return `${base} bg-emerald-500/12 text-emerald-800 ring-emerald-500/40 obsidian:text-emerald-300`;
}

export function shortId(id) {
  return `INC-${String(id).slice(0, 6).toUpperCase()}`;
}