import { TriangleAlert } from "lucide-react";
import { fileUrl } from "../../api/encroachment.js";
import { classLabel } from "../../utils/encroachmentFormat.js";
import { SEVERITY_COLOR, normaliseSeverity } from "../../utils/severity.js";

// The findings on one photograph, numbered to match the boxes drawn on it:
// the enlarged crop, the class, the share on railway land and any reviewer note.
export default function FindingLines({ findings, detailed = false }) {
  return (
    <ol className="space-y-2 text-sm">
      {findings.map((f, i) => (
        <li key={f.id} className="flex items-center gap-2.5">
          {f.crop_url && (
            <img
              src={fileUrl(f.crop_url)}
              alt={`Finding ${i + 1}, enlarged: ${classLabel(f.cls)}`}
              className={`${detailed ? "h-20 w-28" : "h-14 w-20"} shrink-0 border border-rule object-cover`}
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
            <span className="block text-xs text-muted">
              {Math.round(f.overlap_ratio * 100)} % on railway land
              {detailed && ` · detector confidence ${(f.confidence * 100).toFixed(0)} % · “${f.label}”`}
            </span>
            {detailed && f.notes?.length > 0 && (
              <span className="mt-0.5 flex items-start gap-1.5 text-xs font-medium text-sev-high">
                <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
                {f.notes.join(" · ")}
              </span>
            )}
          </span>
        </li>
      ))}
    </ol>
  );
}
