import { severityTone, statusTone } from "./severity.js";

export { SEVERITIES, SEVERITY_COLOR } from "./severity.js";

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

// Class strings kept for existing callers; new code uses <SeverityBadge> / <StatusBadge>.
export function severityBadge(sev) {
  return `inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold capitalize ${severityTone(sev)}`;
}

export function statusBadge(status) {
  return `inline-flex items-center rounded px-2 py-0.5 text-[11px] font-medium ${statusTone(status)}`;
}

export function shortSite(id) {
  return `SITE-${String(id).slice(0, 6).toUpperCase()}`;
}
