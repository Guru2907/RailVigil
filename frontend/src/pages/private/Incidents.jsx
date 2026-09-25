import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listIncidents } from "../../api/incidents.js";
import { fmtTime, fmtPct, sevClass, shortId } from "../../utils/incidentFormat.js";

const RISK_OPTIONS = [
  [0, "Any risk"],
  [25, "25+"],
  [50, "50+"],
  [75, "75+"],
];

export default function Incidents() {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [eventType, setEventType] = useState("all");
  const [minRisk, setMinRisk] = useState(0);

  useEffect(() => {
    let cancelled = false;
    listIncidents()
      .then((data) => !cancelled && setIncidents(data))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const eventTypes = useMemo(() => [...new Set(incidents.map((i) => i.event_type))], [incidents]);

  const visible = useMemo(
    () =>
      incidents
        .filter((i) => (eventType === "all" || i.event_type === eventType) && i.risk_score >= minRisk)
        .sort((a, b) => b.risk_score - a.risk_score),
    [incidents, eventType, minRisk]
  );

  const selectClass =
    "rounded-full bg-white border border-black/10 px-4 py-2.5 text-sm font-medium text-tactical-dark focus:outline-none focus:ring-2 focus:ring-emerald-300";

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="mb-8">
        <div className="text-xs font-mono text-tactical-mint mb-2">INCIDENTS</div>
        <h1 className="text-3xl font-semibold tracking-tight">All recorded incidents</h1>
        <p className="mt-2 text-white/60 max-w-md">
          Every confirmed encroachment across all analyzed videos.
        </p>
      </div>

      <div className="rounded-3xl bg-tactical-card text-tactical-dark p-6 shadow-lg border border-emerald-200/50">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
          <div className="flex flex-wrap items-center gap-3">
            <select value={eventType} onChange={(e) => setEventType(e.target.value)} className={selectClass}>
              <option value="all">All event types</option>
              {eventTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select value={minRisk} onChange={(e) => setMinRisk(Number(e.target.value))} className={selectClass}>
              {RISK_OPTIONS.map(([v, label]) => (
                <option key={v} value={v}>
                  Risk: {label}
                </option>
              ))}
            </select>
          </div>
          <span className="text-xs font-mono text-emerald-600">
            {visible.length} of {incidents.length} · sorted by risk
          </span>
        </div>

        {loading ? (
          <p className="text-sm text-tactical-dark/60">Loading incidents…</p>
        ) : error ? (
          <p className="text-sm font-mono text-tactical-alert">Could not load incidents: {error}</p>
        ) : visible.length === 0 ? (
          <p className="text-sm text-tactical-dark/60">
            {incidents.length === 0
              ? "No incidents yet. Analyze a video to record some."
              : "No incidents match these filters."}
          </p>
        ) : (
          <div className="max-h-[36rem] overflow-auto rounded-2xl bg-white border border-black/5">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white text-left text-[11px] font-mono text-tactical-dark/50">
                <tr>
                  {["ID", "TIME", "OBJECT", "TYPE", "DWELL", "PENETRATION", "RISK", "SEVERITY", ""].map((h) => (
                    <th key={h} className="px-4 py-3 font-normal">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="font-mono">
                {visible.map((i) => (
                  <tr
                    key={i.id}
                    onClick={() => navigate(`/incidents/${i.id}`)}
                    className="cursor-pointer border-t border-black/5 hover:bg-emerald-50 transition-all duration-200"
                  >
                    <td className="px-4 py-3">{shortId(i.id)}</td>
                    <td className="px-4 py-3">{fmtTime(i.start_ts)}</td>
                    <td className="px-4 py-3">
                      {i.object_class} #{i.track_id}
                    </td>
                    <td className="px-4 py-3">{i.event_type}</td>
                    <td className="px-4 py-3">{i.dwell_time_sec.toFixed(1)}s</td>
                    <td className="px-4 py-3">{fmtPct(i.max_penetration)}</td>
                    <td className="px-4 py-3">{Math.round(i.risk_score)}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${sevClass(i.severity)}`}>
                        {(i.severity || "").toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-emerald-600">View</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}