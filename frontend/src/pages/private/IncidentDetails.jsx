import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getIncident } from "../../api/incidents.js";
import { getIncidentSnapshotUrl, getAnnotatedVideoUrl } from "../../api/videos.js";
import { Card, ErrorBanner, PageHeader } from "../../components/ui/index.jsx";
import { formatDateTime } from "../../utils/formatDate.js";
import { fmtTime, fmtPct, sevClass, shortId } from "../../utils/incidentFormat.js";

function MediaFrame({ label, children }) {
  return (
    <figure className="overflow-hidden rounded-lg border border-canvas-line bg-black shadow-lg shadow-black/30">
      <figcaption className="border-b border-white/10 px-4 py-2 font-mono text-[10px] tracking-widest text-white/60">{label}</figcaption>
      {children}
    </figure>
  );
}

export default function IncidentDetails() {
  const { id } = useParams();
  const [incident, setIncident] = useState(null);
  const [error, setError] = useState("");
  const [noImage, setNoImage] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setIncident(null);
    setError("");
    setNoImage(false);
    getIncident(id)
      .then((d) => !cancelled && setIncident(d))
      .catch((e) => !cancelled && setError(e?.response?.status === 404 ? "Incident not found." : e.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  const crumbs = [["Intrusion"], ["Incidents", "/incidents"], [incident ? shortId(incident.id) : "Incident"]];

  if (!incident) {
    return (
      <>
        <PageHeader crumbs={crumbs} title="Incident" />
        {error ? <ErrorBanner>{error}</ErrorBanner> : <p className="text-sm text-canvas-muted">Loading incident…</p>}
      </>
    );
  }

  return (
    <>
      <PageHeader
        crumbs={crumbs}
        title={<span className="font-mono">{shortId(incident.id)}</span>}
        description={`${incident.object_class} #${incident.track_id} · ${incident.event_type} · recorded ${formatDateTime(incident.created_at)}`}
        actions={
          <span className="rounded-md bg-surface px-3 py-2">
            <span className={`px-2 py-0.5 text-xs font-bold ${sevClass(incident.severity)}`}>
              {incident.severity} · risk {Math.round(incident.risk_score)}
            </span>
          </span>
        }
      />

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <MediaFrame label="EVIDENCE SNAPSHOT">
            <div className="flex aspect-video items-center justify-center">
              {noImage ? (
                <span className="font-mono text-xs text-white/60">No snapshot available</span>
              ) : (
                <img
                  src={getIncidentSnapshotUrl(incident.id)}
                  alt={`Evidence for track ${incident.track_id}`}
                  className="h-full w-full object-contain"
                  onError={() => setNoImage(true)}
                />
              )}
            </div>
          </MediaFrame>
        </div>

        <Card className="lg:col-span-2" title="Incident data" bodyClass="p-0">
          <dl className="divide-y divide-line text-sm">
            {[
              ["Object", `${incident.object_class} #${incident.track_id}`],
              ["Event type", incident.event_type],
              ["Persistent", incident.is_persistent ? "Yes" : "No"],
              ["Window", `${fmtTime(incident.start_ts)} – ${fmtTime(incident.end_ts)}`],
              ["Frames", `${incident.start_frame} – ${incident.end_frame}`],
              ["Dwell time", `${incident.dwell_time_sec.toFixed(1)} s`],
              ["Max penetration", fmtPct(incident.max_penetration)],
              ["Avg penetration", fmtPct(incident.avg_penetration)],
              ["Risk score", Math.round(incident.risk_score)],
              ["Zone", incident.zone_label],
              ["Recorded", formatDateTime(incident.created_at)],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between gap-4 px-6 py-2.5">
                <dt className="text-muted">{k}</dt>
                <dd className="tabular max-w-[60%] truncate font-mono font-medium">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </div>

      <div className="mt-6">
        <MediaFrame label={`ANNOTATED VIDEO · STARTS AT ${fmtTime(Math.max(0, incident.start_ts - 1))}`}>
          <video
            src={`${getAnnotatedVideoUrl(incident.video_id)}#t=${Math.max(0, incident.start_ts - 1)}`}
            controls
            className="max-h-[32rem] w-full bg-black"
          />
        </MediaFrame>
      </div>
    </>
  );
}
