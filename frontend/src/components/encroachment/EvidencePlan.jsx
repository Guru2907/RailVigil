import { useEffect, useState } from "react";
import { ImageOff } from "lucide-react";
import { fileUrl, getPhoto } from "../../api/encroachment.js";
import { Skeleton } from "../ui/index.jsx";
import { SEVERITY_COLOR, normaliseSeverity } from "../../utils/severity.js";

// The evidence drawn as a land plan: the photograph, the railway land marked
// on it washed pink inside a dashed boundary, and each finding boxed and
// numbered. Every shape comes from stored data: the zone outlined at upload
// and the detector's boxes.
//   findings: the site's findings on ONE photo (same media_id), most severe first
export default function EvidencePlan({ findings, className = "" }) {
  const mediaId = findings?.[0]?.media_id;
  const [photo, setPhoto] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!mediaId) return undefined;
    let cancelled = false;
    setPhoto(null);
    setFailed(false);
    getPhoto(mediaId)
      .then((p) => !cancelled && setPhoto(p))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [mediaId]);

  if (!mediaId || failed) {
    return (
      <div className={`grid aspect-[16/10] place-items-center border border-rule bg-canvas-2 text-xs text-muted ${className}`}>
        <span className="flex items-center gap-2">
          <ImageOff className="h-4 w-4" aria-hidden />
          {failed ? "The photograph could not be loaded" : "No photograph for this site"}
        </span>
      </div>
    );
  }
  if (!photo) return <Skeleton className={`aspect-[16/10] w-full !rounded-none ${className}`} />;

  const { width: w, height: h } = photo;
  const zone = photo.zone?.points;
  const zonePoints = zone
    ?.map(([x, y]) => (photo.zone.format === "normalized" ? [x * w, y * h] : [x, y]))
    .map(([x, y]) => `${x},${y}`)
    .join(" ");
  const stroke = Math.max(w, h) / 280;
  const label = Math.max(w, h) / 36;

  return (
    <figure className={`relative overflow-hidden border border-rule bg-canvas-2 ${className}`}>
      <img src={fileUrl(photo.original_url)} alt="Photograph of the site" className="block w-full" style={{ aspectRatio: `${w} / ${h}` }} />
      <svg viewBox={`0 0 ${w} ${h}`} className="absolute inset-0 h-full w-full" role="img" aria-label="Railway land and findings marked on the photograph">
        {zonePoints && (
          <polygon
            points={zonePoints}
            fill="var(--color-wash)"
            fillOpacity="0.5"
            stroke="var(--color-wash-edge)"
            strokeWidth={stroke}
            strokeDasharray={`${stroke * 4} ${stroke * 2.5}`}
          />
        )}
        {findings.map((f, i) => {
          const [x1, y1, x2, y2] = f.bbox;
          const colour = SEVERITY_COLOR[normaliseSeverity(f.severity)];
          return (
            <g key={f.id}>
              <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill="none" stroke="#fff" strokeWidth={stroke * 2.2} />
              <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill="none" stroke={colour} strokeWidth={stroke * 1.2} />
              <circle cx={x1 - label * 0.7} cy={y1 - label * 0.7} r={label * 0.62} fill={colour} stroke="#fff" strokeWidth={stroke * 0.8} />
              <text x={x1 - label * 0.7} y={y1 - label * 0.7} textAnchor="middle" dominantBaseline="central" fontSize={label * 0.72} fontWeight="700" fill="#fff">
                {i + 1}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption className="absolute bottom-0 left-0 flex items-center gap-3 border-r border-t border-rule bg-surface px-2.5 py-1 text-[11px] font-medium text-ink">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-4 border border-dashed border-wash-edge bg-wash" aria-hidden />
          Railway land
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 border-2 border-sev-critical" aria-hidden />
          Finding
        </span>
      </figcaption>
    </figure>
  );
}
