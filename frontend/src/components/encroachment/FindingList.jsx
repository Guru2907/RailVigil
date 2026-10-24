import { Link } from "react-router-dom";
import { fileUrl } from "../../api/encroachment.js";
import { classLabel, severityBadge, shortSite } from "../../utils/encroachmentFormat.js";
import { linkClass } from "../ui/index.jsx";

export default function FindingList({ findings, showSite = true }) {
  if (!findings?.length) {
    return <p className="text-sm text-muted">No potential encroachments found on the marked railway land.</p>;
  }
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {findings.map((f, i) => (
        <li key={f.id} className="flex gap-3 rounded-md border border-line bg-paper p-3">
          {f.crop_url ? (
            <img src={fileUrl(f.crop_url)} alt={f.label} className="h-20 w-20 shrink-0 rounded bg-black object-contain" />
          ) : (
            <div className="h-20 w-20 shrink-0 rounded bg-surface-2" />
          )}
          <div className="min-w-0 flex-1 text-sm">
            <div className="flex items-start justify-between gap-2">
              <span className="font-semibold leading-tight">{classLabel(f.cls)}</span>
              <span className={severityBadge(f.severity)}>{f.severity}</span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted">
              #{String(i + 1).padStart(2, "0")} · “{f.label}”
            </div>
            <div className="tabular mt-0.5 font-mono text-[11px] text-muted">
              conf {(f.confidence * 100).toFixed(1)}% · on railway land {Math.round(f.overlap_ratio * 100)}%
            </div>
            {f.notes?.length > 0 && (
              <div className="mt-1 text-[11px] font-medium text-amber-800 obsidian:text-amber-300">⚠ {f.notes.join(" · ")}</div>
            )}
            {showSite &&
              (f.site_id ? (
                <Link to={`/sites/${f.site_id}`} className={`mt-1 inline-block font-mono text-[11px] ${linkClass}`}>
                  {shortSite(f.site_id)}
                </Link>
              ) : (
                <div className="mt-1 text-[11px] text-muted">No location · not on map</div>
              ))}
          </div>
        </li>
      ))}
    </ul>
  );
}
