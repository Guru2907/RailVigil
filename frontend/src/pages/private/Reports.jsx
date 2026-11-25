import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Download, FileText } from "lucide-react";
import { listReports } from "../../api/encroachment.js";
import { Badge, EmptyState, ErrorBanner, FilterChips, Pagination, SkeletonRows, Table, btn, cellClass, inputClass, linkClass } from "../../components/ui/index.jsx";
import { REASON_LABEL, shortSite } from "../../utils/encroachmentFormat.js";
import { formatDateTime, timeAgo } from "../../utils/formatDate.js";

const PAGE = 12;

// The register as shown (current filters), for a spreadsheet.
function downloadCsv(reports) {
  const head = ["report_no", "reason", "site_id", "media_id", "finding_id", "issued_at"];
  const rows = reports.map((r) => [r.report_no, r.reason, r.site_id ?? "", r.media_id ?? "", r.finding_id ?? "", r.created_at]);
  const text = [head, ...rows].map((row) => row.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(",")).join("\r\n");
  const url = URL.createObjectURL(new globalThis.Blob([text], { type: "text/csv" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: "railvigil-reports.csv" });
  a.click();
  URL.revokeObjectURL(url);
}

// Every numbered report the system has issued. A report is raised for a new
// site, a critical finding or a re-encroachment; each opens as a printable sheet.
export default function Reports() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const reason = params.get("reason") || "";
  const query = params.get("q") || "";
  const offset = Number(params.get("offset")) || 0;
  const [reports, setReports] = useState(null);
  const [error, setError] = useState("");

  const update = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    if (!("offset" in changes)) next.delete("offset");
    setParams(next, { replace: true });
  };

  useEffect(() => {
    let cancelled = false;
    listReports({ limit: 500 })
      .then((r) => !cancelled && setReports(r))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, []);

  const loading = reports === null && !error;
  const counts = useMemo(() => {
    const c = {};
    (reports || []).forEach((r) => (c[r.reason] = (c[r.reason] || 0) + 1));
    return c;
  }, [reports]);
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (reports || []).filter(
      (r) => (!reason || r.reason === reason) && (!q || r.report_no.toLowerCase().includes(q) || (r.site_id && shortSite(r.site_id).toLowerCase().includes(q))),
    );
  }, [reports, reason, query]);
  const rows = shown.slice(offset, offset + PAGE);
  const latest = reports?.[0];

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div>
          <h1 className="text-[32px] font-bold leading-none tracking-tight">Reports</h1>
          <p className="mt-1.5 text-sm text-canvas-muted">
            {loading
              ? "Loading the register"
              : `${reports?.length ?? 0} issued${latest ? ` · latest ${timeAgo(latest.created_at)}` : ""} · raised for a new site, a critical finding or a re-encroachment`}
          </p>
        </div>
        <button type="button" className={btn.secondary} onClick={() => downloadCsv(shown)} disabled={!shown.length}>
          <Download className="h-4 w-4" aria-hidden />
          Export {shown.length || ""} as CSV
        </button>
      </div>

      {error && <ErrorBanner>The reports could not be loaded ({error}). Check that the backend is running, then reload.</ErrorBanner>}

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <FilterChips
          label="Reason"
          single
          options={Object.entries(REASON_LABEL).map(([k, v]) => [k, `${v} ${counts[k] ?? 0}`])}
          value={reason}
          onChange={(v) => update({ reason: v })}
        />
        <label className="flex items-center gap-2 text-xs text-canvas-muted">
          Find
          <input
            type="search"
            value={query}
            onChange={(e) => update({ q: e.target.value })}
            placeholder="Report or site number"
            className={`${inputClass} !h-8 w-56 text-xs`}
          />
        </label>
      </div>

      <section className="border-2 border-rule bg-surface" aria-label="Report register">
        {!loading && !error && shown.length === 0 ? (
          <EmptyState
            icon={FileText}
            title={reports?.length ? "No reports match" : "No reports yet"}
            action={
              (reason || query) && (
                <button type="button" className={`${btn.secondary} ${btn.small}`} onClick={() => setParams({}, { replace: true })}>
                  Clear filters
                </button>
              )
            }
          >
            {reports?.length
              ? "Try another reason, or clear the search."
              : "A report is issued when an analysed photo creates a site, shows a critical finding, or finds a resolved site encroached again."}
          </EmptyState>
        ) : (
          <>
            <div className="hidden sm:block">
              <Table head={["Report", "Reason", "Site", "Issued", ""]}>
                {loading ? (
                  <SkeletonRows rows={PAGE} cols={5} />
                ) : (
                  rows.map((r) => (
                    <tr key={r.report_no} onClick={() => navigate(`/reports/${r.report_no}`)} className="cursor-pointer transition-colors hover:bg-canvas-2">
                      <td className={`${cellClass} text-[15px] font-bold`}>
                        <Link to={`/reports/${r.report_no}`} onClick={(e) => e.stopPropagation()}>
                          {r.report_no}
                        </Link>
                      </td>
                      <td className={cellClass}>
                        <Badge>{REASON_LABEL[r.reason] || r.reason}</Badge>
                      </td>
                      <td className={cellClass}>
                        {r.site_id ? (
                          <Link to={`/sites/${r.site_id}`} className={linkClass} onClick={(e) => e.stopPropagation()}>
                            {shortSite(r.site_id)}
                          </Link>
                        ) : (
                          "–"
                        )}
                      </td>
                      <td className={`${cellClass} text-muted`}>{formatDateTime(r.created_at)}</td>
                      <td className={`${cellClass} text-right text-sm font-semibold text-accent`}>Open sheet</td>
                    </tr>
                  ))
                )}
              </Table>
            </div>
            <ul className="divide-y divide-line sm:hidden">
              {rows.map((r) => (
                <li key={r.report_no}>
                  <Link to={`/reports/${r.report_no}`} className="block px-4 py-3">
                    <span className="block font-bold">{r.report_no}</span>
                    <span className="mt-0.5 block text-xs text-muted">
                      {REASON_LABEL[r.reason] || r.reason} · {r.site_id ? shortSite(r.site_id) : "no site"} · {timeAgo(r.created_at)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
            {shown.length > PAGE && <Pagination offset={offset} limit={PAGE} total={shown.length} onChange={(o) => update({ offset: o ? String(o) : "" })} />}
          </>
        )}
      </section>
    </>
  );
}
