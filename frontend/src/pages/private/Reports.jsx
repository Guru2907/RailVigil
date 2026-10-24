import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, Image } from "lucide-react";
import { listReports } from "../../api/encroachment.js";
import { Card, EmptyState, PageHeader, Table, btn, cellClass, rowClass, selectClass } from "../../components/ui/index.jsx";
import { REASON_LABEL, shortSite } from "../../utils/encroachmentFormat.js";
import { formatDateTime } from "../../utils/formatDate.js";

// The list as shown (current reason filter), for a spreadsheet.
function downloadCsv(reports) {
  const head = ["report_no", "reason", "site_id", "media_id", "finding_id", "issued_at"];
  const rows = reports.map((r) => [r.report_no, r.reason, r.site_id ?? "", r.media_id ?? "", r.finding_id ?? "", r.created_at]);
  const text = [head, ...rows].map((row) => row.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(",")).join("\r\n");
  const url = URL.createObjectURL(new globalThis.Blob([text], { type: "text/csv" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: "railvigil-reports.csv" });
  a.click();
  URL.revokeObjectURL(url);
}

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
          <div className="flex items-center gap-2">
            <select aria-label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} className={selectClass}>
              <option value="">All reasons</option>
              {Object.entries(REASON_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => downloadCsv(reports)}
              disabled={!reports.length}
              className={`${btn.secondary} ${btn.small}`}
            >
              <Download className="h-3.5 w-3.5" /> Export CSV
            </button>
          </div>
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
          <Table head={["Report no.", "Reason", "Site", "Issued", ""]}>
            {reports.map((r) => (
              <tr
                key={r.report_no}
                onClick={() => navigate(r.site_id ? `/sites/${r.site_id}` : `/photos/${r.media_id}`)}
                className={rowClass}
              >
                <td className={`${cellClass} font-mono font-semibold`}>{r.report_no}</td>
                <td className={cellClass}>{REASON_LABEL[r.reason] || r.reason}</td>
                <td className={`${cellClass} font-mono text-xs`}>{r.site_id ? shortSite(r.site_id) : <span className="text-muted">No location</span>}</td>
                <td className={`${cellClass} font-mono text-xs text-muted`}>{formatDateTime(r.created_at)}</td>
                <td className={`${cellClass} text-right`}>
                  {r.media_id && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/photos/${r.media_id}`);
                      }}
                      className={`${btn.secondary} ${btn.small}`}
                    >
                      <Image className="h-3.5 w-3.5" /> View photo
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
