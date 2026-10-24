import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listReports } from "../../api/encroachment.js";
import { Card, EmptyState, PageHeader, Table, cellClass, rowClass, selectClass } from "../../components/ui/index.jsx";
import { REASON_LABEL, shortSite } from "../../utils/encroachmentFormat.js";
import { formatDateTime } from "../../utils/formatDate.js";

export default function Reports() {
  const navigate = useNavigate();
  const [reports, setReports] = useState([]);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    listReports({ reason: reason || undefined, limit: 500 })
      .then((r) => !cancelled && setReports(r))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [reason]);

  return (
    <>
      <PageHeader
        crumbs={[["Encroachment"], ["Reports"]]}
        title="Report register"
        description="Reports are issued automatically for a new site, a re-encroached site or a critical finding. Numbers are unique and sequential."
      />
      <Card
        title="All reports"
        subtitle={loading ? "Loading…" : `${reports.length} reports`}
        action={
          <select aria-label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} className={selectClass}>
            <option value="">All reasons</option>
            {Object.entries(REASON_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        }
        bodyClass=""
      >
        {error ? (
          <EmptyState>
            <span className="text-danger">{error}</span>
          </EmptyState>
        ) : !loading && reports.length === 0 ? (
          <EmptyState>No reports yet.</EmptyState>
        ) : (
          <Table head={["Report no.", "Reason", "Site", "Issued"]}>
            {reports.map((r) => (
              <tr
                key={r.report_no}
                onClick={() => r.site_id && navigate(`/sites/${r.site_id}`)}
                className={r.site_id ? rowClass : ""}
              >
                <td className={`${cellClass} font-mono font-semibold`}>{r.report_no}</td>
                <td className={cellClass}>{REASON_LABEL[r.reason] || r.reason}</td>
                <td className={`${cellClass} font-mono text-xs`}>{r.site_id ? shortSite(r.site_id) : <span className="text-muted">No location</span>}</td>
                <td className={`${cellClass} font-mono text-xs text-muted`}>{formatDateTime(r.created_at)}</td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
