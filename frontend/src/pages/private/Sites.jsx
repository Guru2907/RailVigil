import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listSites } from "../../api/encroachment.js";
import { Card, EmptyState, PageHeader, Table, cellClass, rowClass, selectClass } from "../../components/ui/index.jsx";
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

  const filters = (
    <div className="flex flex-wrap gap-2">
      <select aria-label="Status" className={selectClass} value={status} onChange={(e) => setStatus(e.target.value)}>
        <option value="">All statuses</option>
        {Object.entries(STATUS_LABEL).map(([k, v]) => (
          <option key={k} value={k}>
            {v}
          </option>
        ))}
      </select>
      <select aria-label="Severity" className={selectClass} value={severity} onChange={(e) => setSeverity(e.target.value)}>
        <option value="">All severities</option>
        {SEVERITIES.map((s) => (
          <option key={s} value={s}>
            {s[0].toUpperCase() + s.slice(1)}
          </option>
        ))}
      </select>
      <select aria-label="Class" className={selectClass} value={cls} onChange={(e) => setCls(e.target.value)}>
        <option value="">All classes</option>
        {Object.entries(CLASS_LABEL).map(([k, v]) => (
          <option key={k} value={k}>
            {v}
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <>
      <PageHeader
        crumbs={[["Encroachment"], ["Sites"]]}
        title="Encroachment sites"
        description="Each site groups repeat findings of the same kind within 25 m and carries its own review case."
      />
      <Card title="Site register" subtitle={loading ? "Loading…" : `${sites.length} sites`} action={filters} bodyClass="">
        {error ? (
          <EmptyState>
            <span className="text-danger">{error}</span>
          </EmptyState>
        ) : !loading && sites.length === 0 ? (
          <EmptyState>No sites match these filters.</EmptyState>
        ) : (
          <Table head={["Site", "Class", "Severity", "Status", "Findings", "Latest report", "Last reported"]}>
            {sites.map((s) => (
              <tr key={s.id} onClick={() => navigate(`/sites/${s.id}`)} className={rowClass}>
                <td className={`${cellClass} font-mono font-semibold`}>{shortSite(s.id)}</td>
                <td className={cellClass}>{classLabel(s.cls)}</td>
                <td className={cellClass}>
                  <span className={severityBadge(s.max_severity)}>{s.max_severity}</span>
                </td>
                <td className={cellClass}>
                  <span className={statusBadge(s.status)}>{STATUS_LABEL[s.status]}</span>
                </td>
                <td className={`${cellClass} tabular font-mono`}>{s.finding_count}</td>
                <td className={`${cellClass} font-mono text-xs`}>{s.latest_report_no || "—"}</td>
                <td className={`${cellClass} font-mono text-xs text-muted`}>{formatDateTime(s.last_reported_at)}</td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
