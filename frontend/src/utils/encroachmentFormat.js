export const SEVERITIES = ["critical", "high", "medium", "low"];

// Map marker / chart colours (the map is always dark).
export const SEVERITY_COLOR = {
  critical: "#F43F5E",
  high: "#F97316",
  medium: "#FACC15",
  low: "#34D399",
};

export const CLASS_LABEL = {
  structure_permanent: "Permanent structure",
  structure_temporary: "Temporary structure",
  vegetation: "Vegetation",
  debris_waste: "Debris / waste",
  material_dump: "Material dump",
  vehicle_parked: "Parked vehicle",
};

export const STATUS_LABEL = {
  reported: "Reported",
  under_review: "Under review",
  verified: "Verified",
  action_taken: "Action taken",
  resolved: "Resolved",
  false_positive: "False positive",
};

// Mirrors TRANSITIONS in backend/app/services/site_service.py
export const NEXT_STATUSES = {
  reported: ["under_review", "false_positive"],
  under_review: ["verified", "false_positive", "reported"],
  verified: ["action_taken", "resolved"],
  action_taken: ["resolved", "verified"],
  resolved: ["reported"],
  false_positive: ["reported"],
};

export const REASON_LABEL = {
  new_site: "New site",
  re_encroached: "Re-encroached",
  critical_finding: "Critical finding",
};

export function classLabel(cls) {
  return CLASS_LABEL[cls] || cls;
}

// High and critical pulse, per the design rules: risk must catch the eye.
export function severityBadge(sev) {
  const s = (sev || "").toLowerCase();
  const base = "inline-flex items-center rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ring-1 ring-inset";
  if (s === "critical") return `${base} bg-danger/12 text-danger ring-danger/40 animate-pulse obsidian:text-rose-300`;
  if (s === "high") return `${base} bg-orange-500/12 text-orange-700 ring-orange-500/40 animate-pulse obsidian:text-orange-300`;
  if (s === "medium") return `${base} bg-amber-400/15 text-amber-800 ring-amber-500/40 obsidian:text-amber-300`;
  return `${base} bg-emerald-500/12 text-emerald-800 ring-emerald-500/40 obsidian:text-emerald-300`;
}

export function statusBadge(status) {
  const base = "inline-flex items-center rounded px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset";
  if (status === "resolved") return `${base} bg-emerald-500/12 text-emerald-800 ring-emerald-500/30 obsidian:text-emerald-300`;
  if (status === "false_positive") return `${base} bg-zinc-500/10 text-muted ring-zinc-500/25`;
  if (status === "reported") return `${base} bg-danger/10 text-danger ring-danger/30 obsidian:text-rose-300`;
  return `${base} bg-sky-500/12 text-sky-800 ring-sky-500/30 obsidian:text-sky-300`;
}

export function shortSite(id) {
  return `SITE-${String(id).slice(0, 6).toUpperCase()}`;
}
