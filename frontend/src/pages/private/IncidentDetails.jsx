import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getIncident } from "../../api/incidents.js";
import { getIncidentSnapshotUrl, getAnnotatedVideoUrl } from "../../api/videos.js";
import { fmtTime, fmtPct, sevClass, shortId } from "../../utils/incidentFormat.js";

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

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <Link
        to="/incidents"
        className="inline-block mb-6 text-sm text-white/60 hover:text-white transition-all duration-200"
      >
        ← Back to incidents
      </Link>

      {error ? (
        <div className="rounded-2xl bg-tactical-alert/15 text-tactical-alert text-sm font-mono px-5 py-3">{error}</div>
      ) : !incident ? (
        <p className="text-white/60 text-sm">Loading incident…</p>
      ) : (
        <>
          <div className="mb-8 flex flex-wrap items-center gap-4">
            <div>
              <div className="text-xs font-mono text-tactical-mint mb-2">INCIDENT DETAILS</div>
              <h1 className="text-3xl font-semibold tracking-tight font-mono">{shortId(incident.id)}</h1>
            </div>
            <span className={`text-xs font-semibold px-3 py-1.5 rounded-full ${sevClass(incident.severity)}`}>
              {(incident.severity || "").toUpperCase()}
            </span>
          </div>

          <div className="grid lg:grid-cols-5 gap-6">
            {/* Evidence 60% */}
            <div className="lg:col-span-3 rounded-3xl border border-white/10 bg-black/40 overflow-hidden shadow-2xl">
              <div className="px-5 py-3 border-b border-white/10 text-xs font-mono text-white/50">EVIDENCE SNAPSHOT</div>
              <div className="aspect-video bg-black flex items-center justify-center">
                {noImage ? (
                  <span className="text-xs font-mono text-white/60">No snapshot available</span>
                ) : (
                  <img
                    src={getIncidentSnapshotUrl(incident.id)}
                    alt={`Evidence for track ${incident.track_id}`}
                    className="w-full h-full object-contain"
                    onError={() => setNoImage(true)}
                  />
                )}
              </div>
            </div>

            {/* Details 40% */}
            <div className="lg:col-span-2 rounded-3xl bg-tactical-card text-tactical-dark p-6 shadow-lg border border-emerald-200/50">
              <h3 className="font-semibold mb-4">Incident data</h3>
              <dl className="space-y-3">
                {[
                  ["Object", `${incident.object_class} #${incident.track_id}`],
                  ["Event type", incident.event_type],
                  ["Persistent", incident.is_persistent ? "Yes" : "No"],
                  ["Window", `${fmtTime(incident.start_ts)} – ${fmtTime(incident.end_ts)}`],
                  ["Frames", `${incident.start_frame} – ${incident.end_frame}`],
                  ["Dwell time", `${incident.dwell_time_sec.toFixed(1)}s`],
                  ["Max penetration", fmtPct(incident.max_penetration)],
                  ["Avg penetration", fmtPct(incident.avg_penetration)],
                  ["Risk score", Math.round(incident.risk_score)],
                  ["Zone", incident.zone_label],
                  ["Recorded", new Date(incident.created_at).toLocaleString()],
                ].map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between rounded-2xl bg-white border border-black/5 px-4 py-3">
                    <dt className="text-sm text-tactical-dark/60">{k}</dt>
                    <dd className="text-sm font-mono font-medium truncate max-w-[60%]">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>

          {/* Annotated video */}
          <div className="mt-6 rounded-3xl border border-white/10 bg-black/40 overflow-hidden shadow-2xl">
            <div className="px-5 py-3 border-b border-white/10 text-xs font-mono text-white/50">
              ANNOTATED VIDEO · jump to {fmtTime(incident.start_ts)}
            </div>
            <video
              src={`${getAnnotatedVideoUrl(incident.video_id)}#t=${Math.max(0, incident.start_ts - 1)}`}
              controls
              className="w-full max-h-[32rem] bg-black"
            />
          </div>
        </>
      )}
    </div>
  );
}