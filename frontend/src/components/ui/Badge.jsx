import { Check, CircleAlert, CircleDot, Eye, Info, OctagonAlert, ShieldCheck, TriangleAlert, Wrench, X } from "lucide-react";
import { SEVERITY_LABEL, normaliseSeverity, severityTone, statusTone } from "../../utils/severity.js";
import { STATUS_LABEL } from "../../utils/encroachmentFormat.js";

// Risk and status are never shown by colour alone: every badge has an icon and a word.

const base = "inline-flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium";

const SEVERITY_ICON = { critical: OctagonAlert, high: TriangleAlert, medium: CircleAlert, low: Info };

export function SeverityBadge({ value, className = "" }) {
  const sev = normaliseSeverity(value);
  const Icon = SEVERITY_ICON[sev];
  return (
    <span className={`${base} ${severityTone(sev)} ${className}`}>
      <Icon className="h-3 w-3" aria-hidden />
      {SEVERITY_LABEL[sev]}
    </span>
  );
}

const STATUS_ICON = {
  reported: CircleDot,
  under_review: Eye,
  verified: ShieldCheck,
  action_taken: Wrench,
  resolved: Check,
  false_positive: X,
};

export function StatusBadge({ value, className = "" }) {
  const Icon = STATUS_ICON[value] || CircleDot;
  return (
    <span className={`${base} ${statusTone(value)} ${className}`}>
      <Icon className="h-3 w-3" aria-hidden />
      {STATUS_LABEL[value] || value}
    </span>
  );
}

// Neutral label (a class, a reason, a count).
export function Badge({ children, className = "" }) {
  return <span className={`${base} bg-surface-2 text-muted ring-1 ring-inset ring-line ${className}`}>{children}</span>;
}
