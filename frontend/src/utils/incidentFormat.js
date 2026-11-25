import { severityTone } from "./severity.js";

export function fmtTime(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(Math.floor(sec % 60)).padStart(2, "0");
  return `${m}:${s}`;
}

export function fmtPct(v) {
  return `${Math.round(v <= 1 ? v * 100 : v)}%`;
}

// Tone only; callers add their own size and padding. New code uses <SeverityBadge>.
export function sevClass(sev) {
  return `inline-flex items-center rounded capitalize ${severityTone(sev)}`;
}

export function shortId(id) {
  return `INC-${String(id).slice(0, 6).toUpperCase()}`;
}