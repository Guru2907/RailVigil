import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listIncidents } from "../../api/incidents.js";
import { Card, EmptyState, PageHeader, Table, cellClass, rowClass, selectClass } from "../../components/ui/index.jsx";
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
    [incidents, eventType, minRisk],
  );

  const filters = (
    <div className="flex flex-wrap gap-2">
      <select aria-label="Event type" value={eventType} onChange={(e) => setEventType(e.target.value)} className={selectClass}>
        <option value="all">All event types</option>
        {eventTypes.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
      <select aria-label="Minimum risk" value={minRisk} onChange={(e) => setMinRisk(Number(e.target.value))} className={selectClass}>
        {RISK_OPTIONS.map(([v, label]) => (
          <option key={v} value={v}>
            Risk: {label}
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <>
      <PageHeader
        crumbs={[["Intrusion"], ["Incidents"]]}
        title="Incident register"
        description="Every confirmed intrusion into the track zone across analysed videos, highest risk first."
      />
      <Card
        title="Confirmed incidents"
        subtitle={loading ? "Loading…" : `${visible.length} of ${incidents.length} · sorted by risk`}
        action={filters}
        bodyClass=""
      >
        {error ? (
          <EmptyState>
            <span className="text-danger">Could not load incidents: {error}</span>
          </EmptyState>
        ) : !loading && visible.length === 0 ? (
          <EmptyState>{incidents.length === 0 ? "No incidents yet. Analyse a video to record some." : "No incidents match these filters."}</EmptyState>
        ) : (
          <Table head={["ID", "Time", "Object", "Type", "Dwell", "Penetration", "Risk", "Severity"]}>
            {visible.map((i) => (
              <tr key={i.id} onClick={() => navigate(`/incidents/${i.id}`)} className={rowClass}>
                <td className={`${cellClass} font-mono font-semibold`}>{shortId(i.id)}</td>
                <td className={`${cellClass} tabular font-mono`}>{fmtTime(i.start_ts)}</td>
                <td className={cellClass}>
                  {i.object_class} <span className="font-mono text-muted">#{i.track_id}</span>
                </td>
                <td className={cellClass}>{i.event_type}</td>
                <td className={`${cellClass} tabular font-mono`}>{i.dwell_time_sec.toFixed(1)}s</td>
                <td className={`${cellClass} tabular font-mono`}>{fmtPct(i.max_penetration)}</td>
                <td className={`${cellClass} tabular font-mono font-semibold`}>{Math.round(i.risk_score)}</td>
                <td className={cellClass}>
                  <span className={`px-2 py-0.5 text-[10px] font-bold ${sevClass(i.severity)}`}>{i.severity}</span>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
