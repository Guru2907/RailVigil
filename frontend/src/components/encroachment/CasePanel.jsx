import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { fileUrl, getSite } from "../../api/encroachment.js";
import EvidencePlan from "./EvidencePlan.jsx";
import { KeyValue, SeverityBadge, Skeleton, StatusBadge, btn } from "../ui/index.jsx";
import { SEVERITY_COLOR, normaliseSeverity } from "../../utils/severity.js";
import { NEXT_STATUSES, STATUS_LABEL, classLabel, shortSite } from "../../utils/encroachmentFormat.js";
import { formatDate, timeAgo } from "../../utils/formatDate.js";

// The selected site beside the register: its evidence, where it stands and the
// way into the full case file.
export default function CasePanel({ site }) {
  const [detail, setDetail] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!site) return undefined;
    let cancelled = false;
    setDetail(null);
    setFailed(false);
    getSite(site.id)
      .then((d) => !cancelled && setDetail(d))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [site]);

  if (!site) {
    return (
      <aside className="border border-rule bg-surface p-6 text-sm text-muted">
        Select a site in the register or on the plan to see its evidence and stage.
      </aside>
    );
  }

  // The photograph holding the most severe finding, with every finding of this site on it.
  const ranked = [...(detail?.findings || [])].sort((a, b) => b.severity_score - a.severity_score);
  const finding = ranked[0];
  const onPhoto = ranked.filter((f) => f.media_id === finding?.media_id);
  const elsewhere = ranked.length - onPhoto.length;
  const next = (NEXT_STATUSES[site.status] || []).filter((s) => s !== "false_positive" && s !== "reported")[0];

  return (
    <aside className="border-2 border-rule bg-surface" aria-label={`Site ${shortSite(site.id)}`}>
      <header className="border-b border-line px-5 py-4">
        <div className="flex items-center gap-2.5">
          {site.number && (
            <span
              className="grid h-6 w-6 place-items-center rounded-full text-xs font-bold text-white"
              style={{ background: SEVERITY_COLOR[normaliseSeverity(site.max_severity)] }}
              aria-hidden
            >
              {site.number}
            </span>
          )}
          <h2 className="text-lg font-bold tracking-tight">{shortSite(site.id)}</h2>
        </div>
        <p className="mt-1 text-sm text-muted">
          {classLabel(site.cls)} · {site.finding_count} {site.finding_count === 1 ? "finding" : "findings"}
        </p>
      </header>

      <div className="p-5">
        {detail === null && !failed ? (
          <Skeleton className="aspect-[16/10] w-full !rounded-none" />
        ) : (
          <EvidencePlan findings={failed ? [] : onPhoto} />
        )}

        {onPhoto.length > 0 && (
          <ol className="mt-3 space-y-2 text-sm">
            {onPhoto.map((f, i) => (
              <li key={f.id} className="flex items-center gap-2.5">
                {f.crop_url && (
                  <img
                    src={fileUrl(f.crop_url)}
                    alt={`Finding ${i + 1}, enlarged: ${classLabel(f.cls)}`}
                    className="h-14 w-20 shrink-0 border border-rule object-cover"
                    loading="lazy"
                  />
                )}
                <span
                  className="grid h-5 w-5 shrink-0 place-items-center rounded-full text-[11px] font-bold text-white"
                  style={{ background: SEVERITY_COLOR[normaliseSeverity(f.severity)] }}
                  aria-hidden
                >
                  {i + 1}
                </span>
                <span className="min-w-0 flex-1 leading-snug">
                  <span className="block truncate font-medium">{classLabel(f.cls)}</span>
                  <span className="block text-xs text-muted">{Math.round(f.overlap_ratio * 100)} % on railway land</span>
                </span>
              </li>
            ))}
            {elsewhere > 0 && (
              <li className="pl-[30px] text-xs text-muted">
                {elsewhere} more {elsewhere === 1 ? "finding" : "findings"} on other photographs, in the case file.
              </li>
            )}
          </ol>
        )}

        <KeyValue
          className="mt-3"
          rows={[
            ["Severity", <SeverityBadge key="s" value={site.max_severity} />],
            ["Stage", <StatusBadge key="t" value={site.status} />],
            ["Next stage", next ? STATUS_LABEL[next] : "–"],
            ["Report", site.latest_report_no || "–"],
            ["First reported", formatDate(site.first_reported_at)],
            ["Last seen", timeAgo(site.last_reported_at)],
            ["Position", site.latitude != null ? `${site.latitude.toFixed(5)}, ${site.longitude.toFixed(5)}` : "Not recorded"],
          ]}
        />

        <Link to={`/sites/${site.id}`} className={`${btn.primary} mt-4 w-full`}>
          Open case file
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>
    </aside>
  );
}
