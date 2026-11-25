// The one place severity and status colours are defined. Badges, charts and
// the map all read from here, so a level looks the same on every page.

export const SEVERITIES = ["critical", "high", "medium", "low"];

// Solid colours for chart fills and map markers.
export const SEVERITY_COLOR = {
  critical: "#B8321F",
  high: "#B26B00",
  medium: "#2A5C86",
  low: "#2F6B45",
};

export const SEVERITY_LABEL = { critical: "Critical", high: "High", medium: "Medium", low: "Low" };

// The intrusion layer on maps and charts.
export const INFO_COLOR = "#2A5C86";

export function normaliseSeverity(sev) {
  const s = String(sev || "").toLowerCase();
  if (s === "med") return "medium";
  return SEVERITIES.includes(s) ? s : "low";
}

const SEVERITY_TONE = {
  critical: "bg-surface text-sev-critical ring-sev-critical/60",
  high: "bg-surface text-sev-high ring-sev-high/60",
  medium: "bg-surface text-sev-medium ring-sev-medium/60",
  low: "bg-surface text-sev-low ring-sev-low/60",
};

// Tint, text and ring for a severity; the caller adds size and padding.
export function severityTone(sev) {
  return `ring-1 ring-inset ${SEVERITY_TONE[normaliseSeverity(sev)]}`;
}

const STATUS_TONE = {
  reported: "bg-surface text-ink ring-rule/50",
  under_review: "bg-surface text-info ring-info/60",
  verified: "bg-surface text-info ring-info/60",
  action_taken: "bg-surface text-accent ring-accent/60",
  resolved: "bg-accent text-accent-ink ring-accent",
  false_positive: "bg-canvas-2 text-muted ring-line",
};

export function statusTone(status) {
  return `ring-1 ring-inset ${STATUS_TONE[status] || STATUS_TONE.under_review}`;
}
