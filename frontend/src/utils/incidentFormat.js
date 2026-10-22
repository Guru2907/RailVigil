export function fmtTime(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(Math.floor(sec % 60)).padStart(2, "0");
  return `${m}:${s}`;
}

export function fmtPct(v) {
  return `${Math.round(v <= 1 ? v * 100 : v)}%`;
}

export function sevClass(sev) {
  const s = (sev || "").toUpperCase();
  if (s === "HIGH" || s === "CRITICAL") return "bg-danger/15 text-danger animate-pulse";
  if (s === "MEDIUM" || s === "MED") return "bg-amber-500/15 text-amber-300";
  return "bg-emerald-500/15 text-emerald-300";
}

export function shortId(id) {
  return `INC-${String(id).slice(0, 6).toUpperCase()}`;
}