export const SEVERITIES = ["critical", "high", "medium", "low"];

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

export function severityBadge(sev) {
  const s = (sev || "").toLowerCase();
  if (s === "critical") return "bg-rose-500/15 text-rose-600 ring-1 ring-rose-500/30";
  if (s === "high") return "bg-orange-500/15 text-orange-600 ring-1 ring-orange-500/30";
  if (s === "medium") return "bg-amber-400/20 text-amber-700 ring-1 ring-amber-500/30";
  return "bg-emerald-100 text-emerald-700 ring-1 ring-emerald-500/30";
}

export function statusBadge(status) {
  if (status === "resolved") return "bg-emerald-100 text-emerald-700";
  if (status === "false_positive") return "bg-zinc-200 text-zinc-600";
  if (status === "reported") return "bg-rose-100 text-rose-700";
  return "bg-sky-100 text-sky-700";
}

export function shortSite(id) {
  return `SITE-${String(id).slice(0, 6).toUpperCase()}`;
}
