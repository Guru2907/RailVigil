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
// Plain words for the pipeline's event types.
export const EVENT_LABEL = {
  human_intrusion: "Person on the track",
  persistent_human_presence: "Person staying on the track",
  vehicle_intrusion: "Vehicle on the track",
  animal_intrusion: "Animal on the track",
  persistent_animal_presence: "Animal staying on the track",
  other_intrusion: "Other object on the track",
};

export function eventLabel(type) {
  return EVENT_LABEL[type] || type;
}
