// The one place severity and status colours are defined. Badges, charts and
// the map all read from here, so a level looks the same on every page.

export const SEVERITIES = ["critical", "high", "medium", "low"];

// Solid colours for chart fills and map markers.
export const SEVERITY_COLOR = {
  critical: "#F43F5E",
  high: "#F97316",
  medium: "#FACC15",
  low: "#34D399",
};

export const SEVERITY_LABEL = { critical: "Critical", high: "High", medium: "Medium", low: "Low" };

// The intrusion layer on maps and charts.
export const INFO_COLOR = "#38BDF8";

export function normaliseSeverity(sev) {
  const s = String(sev || "").toLowerCase();
  if (s === "med") return "medium";
  return SEVERITIES.includes(s) ? s : "low";
}

const SEVERITY_TONE = {
  critical: "bg-sev-critical/12 text-sev-critical ring-sev-critical/35",
  high: "bg-sev-high/12 text-sev-high ring-sev-high/35",
  medium: "bg-sev-medium/12 text-sev-medium ring-sev-medium/35",
  low: "bg-sev-low/12 text-sev-low ring-sev-low/35",
};

// Tint, text and ring for a severity; the caller adds size and padding.
export function severityTone(sev) {
  return `ring-1 ring-inset ${SEVERITY_TONE[normaliseSeverity(sev)]}`;
}

const STATUS_TONE = {
  reported: "bg-sev-critical/10 text-sev-critical ring-sev-critical/30",
  under_review: "bg-info/10 text-info ring-info/30",
  verified: "bg-info/10 text-info ring-info/30",
  action_taken: "bg-accent/10 text-accent ring-accent/30",
  resolved: "bg-sev-low/10 text-sev-low ring-sev-low/30",
  false_positive: "bg-muted/10 text-muted ring-muted/25",
};

export function statusTone(status) {
  return `ring-1 ring-inset ${STATUS_TONE[status] || STATUS_TONE.under_review}`;
}
