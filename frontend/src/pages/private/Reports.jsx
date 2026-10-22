import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listReports } from "../../api/encroachment.js";
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
    <div className="space-y-4 p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Encroachment reports</h1>
          <p className="text-sm text-white/60">Issued automatically for a new site, a re-encroached site or a critical finding.</p>
        </div>
        <select
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="rounded-full border border-white/15 bg-black/30 px-3 py-1.5 text-sm text-white outline-none"
        >
          <option value="">All reasons</option>
          {Object.entries(REASON_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-2xl bg-surface text-ink shadow-none">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-muted">
            <tr>
              {["Report no.", "Reason", "Site", "Issued"].map((h) => (
                <th key={h} className="px-4 py-3 font-semibold">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted">
                  Loading…
                </td>
              </tr>
            )}
            {error && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-rose-300">
                  {error}
                </td>
              </tr>
            )}
            {!loading && !error && reports.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted">
                  No reports yet.
                </td>
              </tr>
            )}
            {reports.map((r) => (
              <tr
                key={r.report_no}
                onClick={() => r.site_id && navigate(`/sites/${r.site_id}`)}
                className={`border-t border-line ${r.site_id ? "cursor-pointer hover:bg-surface-2" : ""}`}
              >
                <td className="px-4 py-3 font-mono text-xs font-semibold">{r.report_no}</td>
                <td className="px-4 py-3">{REASON_LABEL[r.reason] || r.reason}</td>
                <td className="px-4 py-3 font-mono text-xs">{r.site_id ? shortSite(r.site_id) : "No location"}</td>
                <td className="px-4 py-3 text-xs">{formatDateTime(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
