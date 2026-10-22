import { Link } from "react-router-dom";
import { fileUrl } from "../../api/encroachment.js";
import { classLabel, severityBadge, shortSite } from "../../utils/encroachmentFormat.js";

export default function FindingList({ findings, showSite = true }) {
  if (!findings?.length) {
    return <p className="text-sm text-tactical-dark/50">No potential encroachments found on the marked railway land.</p>;
  }
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {findings.map((f) => (
        <li key={f.id} className="flex gap-3 rounded-2xl border border-tactical-dark/10 bg-white p-3">
          {f.crop_url ? (
            <img src={fileUrl(f.crop_url)} alt={f.label} className="h-20 w-20 shrink-0 rounded-xl bg-black object-contain" />
          ) : (
            <div className="h-20 w-20 shrink-0 rounded-xl bg-tactical-dark/5" />
          )}
          <div className="min-w-0 flex-1 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-semibold">{classLabel(f.cls)}</span>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${severityBadge(f.severity)}`}>
                {f.severity}
              </span>
            </div>
            <div className="mt-0.5 font-mono text-[11px] text-tactical-dark/60">
              “{f.label}” · conf {Math.round(f.confidence * 100)}% · on railway land {Math.round(f.overlap_ratio * 100)}%
            </div>
            {f.notes?.length > 0 && <div className="mt-1 text-[11px] text-amber-700">⚠ {f.notes.join(" · ")}</div>}
            {showSite &&
              (f.site_id ? (
                <Link to={`/sites/${f.site_id}`} className="mt-1 inline-block font-mono text-[11px] text-emerald-700 hover:underline">
                  {shortSite(f.site_id)} →
                </Link>
              ) : (
                <div className="mt-1 text-[11px] text-tactical-dark/40">No location → not on map</div>
              ))}
          </div>
        </li>
      ))}
    </ul>
  );
}
