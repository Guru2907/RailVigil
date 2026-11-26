import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ImageOff, VideoOff } from "lucide-react";
import { getIncident, listIncidents } from "../../api/incidents.js";
import { getAnnotatedVideoUrl, getIncidentSnapshotUrl, getVideo } from "../../api/videos.js";
import { ErrorBanner, KeyValue, SeverityBadge, Skeleton, btn } from "../../components/ui/index.jsx";
import { eventLabel, fmtPct, fmtTime, shortId } from "../../utils/incidentFormat.js";
import { SEVERITY_COLOR, normaliseSeverity } from "../../utils/severity.js";
import { formatDateTime } from "../../utils/formatDate.js";

function Sheet({ title, aside, children }) {
  return (
    <section className="min-w-0 border-2 border-rule bg-surface">
      <header className="flex items-baseline justify-between gap-3 border-b border-line px-5 py-3">
        <h2 className="text-sm font-bold tracking-tight">{title}</h2>
        {aside && <span className="text-xs text-muted">{aside}</span>}
      </header>
      {children}
    </section>
  );
}

function Missing({ icon: Icon, children }) {
  return (
    <div className="grid min-h-40 place-items-center bg-canvas-2 p-6 text-center text-sm text-muted">
      <span className="flex max-w-[44ch] flex-col items-center gap-2">
        <Icon className="h-5 w-5" aria-hidden />
        {children}
      </span>
    </div>
  );
}

// Where this incident sits in its video, drawn to scale against the others.
function Timeline({ incident, others, duration }) {
  const pct = (t) => `${Math.min(100, (t / duration) * 100)}%`;
  const width = (a, b) => `${Math.max(0.6, ((b - a) / duration) * 100)}%`;
  return (
    <div className="px-5 py-4">
      <div className="relative h-7 border border-rule bg-paper" role="img" aria-label={`This incident runs from ${fmtTime(incident.start_ts)} to ${fmtTime(incident.end_ts)} of the video`}>
        {others.map((o) => (
          <span key={o.id} className="absolute inset-y-0 bg-ink/15" style={{ left: pct(o.start_ts), width: width(o.start_ts, o.end_ts) }} />
        ))}
        <span
          className="absolute inset-y-0 border-x border-rule"
          style={{ left: pct(incident.start_ts), width: width(incident.start_ts, incident.end_ts), background: SEVERITY_COLOR[normaliseSeverity(incident.severity)] }}
        />
      </div>
      <div className="mt-1.5 flex flex-wrap justify-between gap-x-3 gap-y-1 text-xs text-muted">
        <span>00:00</span>
        <span className="order-last basis-full sm:order-none sm:basis-auto">
          This incident {fmtTime(incident.start_ts)} to {fmtTime(incident.end_ts)} · grey: {others.length} other {others.length === 1 ? "incident" : "incidents"} in this video
        </span>
        <span>{fmtTime(duration)}</span>
      </div>
    </div>
  );
}

// One incident: the saved frame, the clip from just before it, what was measured, and its place in the video.
export default function IncidentDetails() {
  const { id } = useParams();
  const [incident, setIncident] = useState(null);
  const [video, setVideo] = useState(null);
  const [siblings, setSiblings] = useState([]);
  const [error, setError] = useState("");
  const [noImage, setNoImage] = useState(false);
  const [noClip, setNoClip] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setIncident(null);
    setVideo(null);
    setSiblings([]);
    setError("");
    setNoImage(false);
    setNoClip(false);
    getIncident(id)
      .then((d) => {
        if (cancelled) return;
        setIncident(d);
        getVideo(d.video_id)
          .then((v) => !cancelled && setVideo(v))
          .catch(() => {});
        listIncidents({ video_id: d.video_id })
          .then((all) => !cancelled && setSiblings(all.filter((o) => o.id !== d.id)))
          .catch(() => {});
      })
      .catch((e) => !cancelled && setError(e?.response?.status === 404 ? "No incident has this number." : e.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  const duration = incident ? Math.max(incident.end_ts, ...siblings.map((s) => s.end_ts)) : 0;

  return (
    <>
      <Link to="/incidents" className={`${btn.ghost} -ml-3 mb-2`}>
        <ArrowLeft className="h-4 w-4" aria-hidden />
        All incidents
      </Link>

      <div className="mb-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div>
          <h1 className="text-[32px] font-bold leading-none tracking-tight">{shortId(id)}</h1>
          {incident ? (
            <p className="mt-1.5 text-sm text-canvas-muted">
              {eventLabel(incident.event_type)} · {incident.dwell_time_sec.toFixed(1)} s in the zone · processed {formatDateTime(incident.created_at)}
            </p>
          ) : (
            !error && <Skeleton className="mt-2 h-4 w-80" />
          )}
        </div>
        {incident && (
          <div className="flex items-center gap-3">
            <span className="text-sm">
              Risk <span className="tabular text-lg font-bold">{Math.round(incident.risk_score)}</span>
              <span className="text-muted"> of 100</span>
            </span>
            <SeverityBadge value={incident.severity} />
          </div>
        )}
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      {incident && (
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(0,1fr)_400px]">
          <div className="min-w-0 space-y-5">
            <Sheet title="Clip" aside={`Starts at ${fmtTime(Math.max(0, incident.start_ts - 1))}, one second before the incident`}>
              {noClip ? (
                <Missing icon={VideoOff}>The annotated video for this incident is not on the server, so the clip cannot be played.</Missing>
              ) : (
                <video
                  key={incident.id}
                  controls
                  preload="metadata"
                  className="block aspect-video w-full bg-ink"
                  src={`${getAnnotatedVideoUrl(incident.video_id)}#t=${Math.max(0, incident.start_ts - 1)}`}
                  onError={() => setNoClip(true)}
                />
              )}
            </Sheet>

            <Sheet title="Place in the video" aside={video?.original_filename}>
              <Timeline incident={incident} others={siblings} duration={duration} />
            </Sheet>
          </div>

          <div className="min-w-0 space-y-5">
            <Sheet title="Saved frame">
              {incident.has_snapshot && !noImage ? (
                <img
                  src={getIncidentSnapshotUrl(incident.id)}
                  alt={`Frame saved at the moment of the incident: ${incident.object_class} in the track zone`}
                  className="block w-full"
                  onError={() => setNoImage(true)}
                />
              ) : (
                <Missing icon={ImageOff}>No frame was saved for this incident, or its file is no longer on the server.</Missing>
              )}
            </Sheet>

            <Sheet title="Measured">
              <KeyValue
                className="px-5 py-1"
                rows={[
                  ["Event", eventLabel(incident.event_type)],
                  ["Object", `${incident.object_class}, track ${incident.track_id}`],
                  ["Time in the zone", `${incident.dwell_time_sec.toFixed(1)} s`],
                  ["Deepest in the zone", fmtPct(incident.max_penetration)],
                  ["Average depth", fmtPct(incident.avg_penetration)],
                  ["In the video at", `${fmtTime(incident.start_ts)} to ${fmtTime(incident.end_ts)}`],
                  ["Frames", `${incident.start_frame} to ${incident.end_frame}`],
                  ["Stayed long enough to count as persistent", incident.is_persistent ? "Yes" : "No"],
                  ["Camera", video ? video.camera_label || "Not named" : null],
                  ["Zone", incident.zone_label],
                ]}
              />
            </Sheet>
          </div>
        </div>
      )}
    </>
  );
}
