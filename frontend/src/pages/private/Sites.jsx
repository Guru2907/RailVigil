import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listSites } from "../../api/encroachment.js";
import {
  CLASS_LABEL,
  SEVERITIES,
  STATUS_LABEL,
  classLabel,
  severityBadge,
  shortSite,
  statusBadge,
} from "../../utils/encroachmentFormat.js";
import { formatDateTime } from "../../utils/formatDate.js";

export default function Sites() {
  const navigate = useNavigate();
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [cls, setCls] = useState("");

  useEffect(() => {
    let cancelled = false;
    listSites({ status: status || undefined, severity: severity || undefined, cls: cls || undefined })
      .then((s) => !cancelled && setSites(s))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [status, severity, cls]);

  const select = "rounded-full border border-white/15 bg-black/30 px-3 py-1.5 text-sm text-white outline-none";

  return (
    <div className="space-y-4 p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Encroachment sites</h1>
          <p className="text-sm text-white/60">Each site groups repeat findings of the same kind within 25 m.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select className={select} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            {Object.entries(STATUS_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
          <select className={select} value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="">All severities</option>
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select className={select} value={cls} onChange={(e) => setCls(e.target.value)}>
            <option value="">All classes</option>
            {Object.entries(CLASS_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-3xl bg-tactical-card text-tactical-dark shadow-lg">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-tactical-dark/50">
            <tr>
              {["Site", "Class", "Severity", "Status", "Findings", "Latest report", "Last seen"].map((h) => (
                <th key={h} className="px-4 py-3 font-semibold">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-tactical-dark/50">
                  Loading…
                </td>
              </tr>
            )}
            {error && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-rose-600">
                  {error}
                </td>
              </tr>
            )}
            {!loading && !error && sites.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-tactical-dark/50">
                  No sites match.
                </td>
              </tr>
            )}
            {sites.map((s) => (
              <tr
                key={s.id}
                onClick={() => navigate(`/sites/${s.id}`)}
                className="cursor-pointer border-t border-tactical-dark/5 hover:bg-emerald-50"
              >
                <td className="px-4 py-3 font-mono text-xs">{shortSite(s.id)}</td>
                <td className="px-4 py-3">{classLabel(s.cls)}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${severityBadge(s.max_severity)}`}>
                    {s.max_severity}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] ${statusBadge(s.status)}`}>{STATUS_LABEL[s.status]}</span>
                </td>
                <td className="px-4 py-3">{s.finding_count}</td>
                <td className="px-4 py-3 font-mono text-xs">{s.latest_report_no || "—"}</td>
                <td className="px-4 py-3 text-xs">{formatDateTime(s.last_reported_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
