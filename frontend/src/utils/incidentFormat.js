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
  if (s === "HIGH" || s === "CRITICAL") return "bg-tactical-alert/15 text-tactical-alert animate-pulse";
  if (s === "MEDIUM" || s === "MED") return "bg-amber-100 text-amber-700";
  return "bg-emerald-100 text-emerald-700";
}

export function shortId(id) {
  return `INC-${String(id).slice(0, 6).toUpperCase()}`;
}