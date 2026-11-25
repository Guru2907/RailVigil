import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, ImageOff, Siren } from "lucide-react";
import { listIncidents } from "../../api/incidents.js";
import { getIncidentSnapshotUrl, getVideo } from "../../api/videos.js";
import { EmptyState, ErrorBanner, FilterChips, KeyValue, Pagination, SeverityBadge, SkeletonRows, Table, btn, cellClass, selectClass } from "../../components/ui/index.jsx";
import { eventLabel, fmtPct, fmtTime, shortId } from "../../utils/incidentFormat.js";
import { SEVERITIES, SEVERITY_COLOR, SEVERITY_LABEL, normaliseSeverity } from "../../utils/severity.js";
import { formatDateTime, timeAgo } from "../../utils/formatDate.js";

const PAGE = 10;
const SEVERITY_OPTIONS = SEVERITIES.map((s) => [s, SEVERITY_LABEL[s]]);

// Risk 0-100 as a figure and a bar in the severity colour.
function Risk({ incident }) {
  return (
    <span className="flex items-center gap-2">
      <span className="tabular w-7 font-bold">{Math.round(incident.risk_score)}</span>
      <span className="h-1.5 w-16 bg-canvas-2" aria-hidden>
        <span className="block h-full" style={{ width: `${Math.min(100, incident.risk_score)}%`, background: SEVERITY_COLOR[normaliseSeverity(incident.severity)] }} />
      </span>
    </span>
  );
}

// The selected incident beside the register: its snapshot, what happened and for how long.
function IncidentPanel({ incident }) {
  const [video, setVideo] = useState(null);
  const [broken, setBroken] = useState(false);
  useEffect(() => {
    if (!incident) return undefined;
    let cancelled = false;
    setVideo(null);
    setBroken(false);
    getVideo(incident.video_id)
      .then((v) => !cancelled && setVideo(v))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [incident]);

  if (!incident) return null;
  return (
    <aside className="border-2 border-rule bg-surface" aria-label={`Incident ${shortId(incident.id)}`}>
      <header className="border-b border-line px-5 py-4">
        <h2 className="text-lg font-bold tracking-tight">{shortId(incident.id)}</h2>
        <p className="mt-1 text-sm text-muted">{eventLabel(incident.event_type)}</p>
      </header>
      <div className="p-5">
        <div className="aspect-video overflow-hidden border border-rule bg-ink">
          {incident.has_snapshot && !broken ? (
            <img
              src={getIncidentSnapshotUrl(incident.id)}
              alt={`Frame from the video at the moment of the incident: ${incident.object_class} in the track zone`}
              className="h-full w-full object-contain"
              onError={() => setBroken(true)}
            />
          ) : (
            <div className="grid h-full place-items-center text-xs text-surface/80">
              <span className="flex items-center gap-2">
                <ImageOff className="h-4 w-4" aria-hidden />
                No snapshot was saved for this incident
              </span>
            </div>
          )}
        </div>
        <KeyValue
          className="mt-3"
          rows={[
            ["Severity", <SeverityBadge key="s" value={incident.severity} />],
            ["Risk score", <Risk key="r" incident={incident} />],
            ["Object", `${incident.object_class}, track ${incident.track_id}`],
            ["Time in the zone", `${incident.dwell_time_sec.toFixed(1)} s`],
            ["Deepest in the zone", fmtPct(incident.max_penetration)],
            ["In the video at", `${fmtTime(incident.start_ts)} to ${fmtTime(incident.end_ts)}`],
            ["Camera", video ? video.camera_label || "Not named" : null],
            ["Video", video?.original_filename],
            ["Processed", formatDateTime(incident.created_at)],
          ]}
        />
        <Link to={`/incidents/${incident.id}`} className={`${btn.primary} mt-4 w-full`}>
          Open incident and clip
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>
    </aside>
  );
}

// Every confirmed entry into a track zone, highest risk first. Filters live in the URL.
export default function Incidents() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const severity = params.get("severity") || "";
  const type = params.get("type") || "";
  const offset = Number(params.get("offset")) || 0;
  const [incidents, setIncidents] = useState(null);
  const [error, setError] = useState("");
  const [chosenId, setChosenId] = useState(null);

  const update = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    if (!("offset" in changes)) next.delete("offset");
    setChosenId(null);
    setParams(next, { replace: true });
  };

  useEffect(() => {
    let cancelled = false;
    listIncidents()
      .then((d) => !cancelled && setIncidents(d))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, []);

  const loading = incidents === null && !error;
  const types = useMemo(() => [...new Set((incidents || []).map((i) => i.event_type))], [incidents]);
  const shown = useMemo(() => {
    const wanted = severity ? severity.split(",") : null;
    return (incidents || [])
      .filter((i) => (!wanted || wanted.includes(normaliseSeverity(i.severity))) && (!type || i.event_type === type))
      .sort((a, b) => b.risk_score - a.risk_score);
  }, [incidents, severity, type]);
  const rows = shown.slice(offset, offset + PAGE);
  const selected = rows.find((i) => i.id === chosenId) || rows[0] || null;
  const critical = (incidents || []).filter((i) => normaliseSeverity(i.severity) === "critical").length;
  const videos = new Set((incidents || []).map((i) => i.video_id)).size;
  const empty = !loading && !error && shown.length === 0;

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div>
          <h1 className="text-[32px] font-bold leading-none tracking-tight">Intrusion incidents</h1>
          <p className="mt-1.5 text-sm text-canvas-muted">
            {loading ? "Loading the register" : `${incidents?.length ?? 0} confirmed in ${videos} ${videos === 1 ? "video" : "videos"} · ${critical} critical · highest risk first`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <FilterChips label="Severity" options={SEVERITY_OPTIONS} value={severity ? severity.split(",") : []} onChange={(v) => update({ severity: v.join(",") })} />
          <select aria-label="Event" className={`${selectClass} !h-8 text-xs`} value={type} onChange={(e) => update({ type: e.target.value })}>
            <option value="">All events</option>
            {types.map((t) => (
              <option key={t} value={t}>
                {eventLabel(t)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorBanner>The incidents could not be loaded ({error}). Check that the backend is running, then reload.</ErrorBanner>}

      {empty ? (
        <section className="border-2 border-rule bg-surface">
          <EmptyState
            icon={Siren}
            title={incidents?.length ? "No incidents match these filters" : "No incidents yet"}
            action={
              incidents?.length ? (
                <button type="button" className={`${btn.secondary} ${btn.small}`} onClick={() => setParams({}, { replace: true })}>
                  Clear filters
                </button>
              ) : (
                <Link to="/upload" className={`${btn.primary} ${btn.small}`}>
                  Analyse a video
                </Link>
              )
            }
          >
            {incidents?.length
              ? "Try another severity or event."
              : "An incident is recorded when a person, vehicle or animal stays inside the track zone of an analysed video."}
          </EmptyState>
        </section>
      ) : (
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(0,1fr)_400px]">
          <section className="order-2 min-w-0 border-2 border-rule bg-surface lg:order-1" aria-label="Incident register">
            <div className="hidden sm:block">
              <Table head={["Incident", "Event", "In zone for", "Deepest", "Risk", "Severity", "Processed"]}>
                {loading ? (
                  <SkeletonRows rows={PAGE} cols={7} />
                ) : (
                  rows.map((i) => {
                    const on = i.id === selected?.id;
                    return (
                      <tr
                        key={i.id}
                        onClick={() => setChosenId(i.id)}
                        onDoubleClick={() => navigate(`/incidents/${i.id}`)}
                        aria-selected={on}
                        className={`cursor-pointer transition-colors ${on ? "bg-wash" : "hover:bg-canvas-2"}`}
                      >
                        <td className={`${cellClass} font-semibold`}>
                          <button type="button" onClick={() => setChosenId(i.id)} aria-label={`Select ${shortId(i.id)}`}>
                            {shortId(i.id)}
                          </button>
                        </td>
                        <td className={cellClass}>{eventLabel(i.event_type)}</td>
                        <td className={`${cellClass} tabular`}>{i.dwell_time_sec.toFixed(1)} s</td>
                        <td className={`${cellClass} tabular`}>{fmtPct(i.max_penetration)}</td>
                        <td className={cellClass}>
                          <Risk incident={i} />
                        </td>
                        <td className={cellClass}>
                          <SeverityBadge value={i.severity} />
                        </td>
                        <td className={`${cellClass} text-muted`}>{timeAgo(i.created_at)}</td>
                      </tr>
                    );
                  })
                )}
              </Table>
            </div>
            <ul className="divide-y divide-line sm:hidden">
              {rows.map((i) => (
                <li key={i.id}>
                  <button type="button" onClick={() => setChosenId(i.id)} aria-pressed={i.id === selected?.id} className={`block w-full px-4 py-3 text-left ${i.id === selected?.id ? "bg-wash" : ""}`}>
                    <span className="flex items-center gap-2.5">
                      <span className="font-semibold">{shortId(i.id)}</span>
                      <SeverityBadge value={i.severity} className="ml-auto" />
                    </span>
                    <span className="mt-1 block text-xs text-muted">
                      {eventLabel(i.event_type)} · {i.dwell_time_sec.toFixed(1)} s in zone · risk {Math.round(i.risk_score)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {shown.length > PAGE && <Pagination offset={offset} limit={PAGE} total={shown.length} onChange={(o) => update({ offset: o ? String(o) : "" })} />}
          </section>
          <div className="order-1 min-w-0 lg:order-2">{!loading && <IncidentPanel incident={selected} />}</div>
        </div>
      )}
    </>
  );
}
