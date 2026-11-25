import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Printer } from "lucide-react";
import { getReport } from "../../api/encroachment.js";
import EvidencePlan from "../../components/encroachment/EvidencePlan.jsx";
import { Seal } from "../../components/layout/Seal.jsx";
import PlanMap from "../../components/plan/PlanMap.jsx";
import { ErrorBanner, SeverityBadge, Skeleton, StatusBadge, btn } from "../../components/ui/index.jsx";
import { REASON_LABEL, classLabel, shortSite } from "../../utils/encroachmentFormat.js";
import { formatDateTime } from "../../utils/formatDate.js";

function Field({ label, children }) {
  return (
    <div className="border-b border-line py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-ink">{children ?? "–"}</dd>
    </div>
  );
}

function Block({ title, children }) {
  return (
    <section className="break-inside-avoid border-t-2 border-rule px-6 py-5 sm:px-8">
      <h2 className="mb-3 text-sm font-bold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

// One report as a formal sheet: what was found, where, and on what evidence.
// It prints (or saves as PDF) as shown, without the app chrome.
export default function ReportDetails() {
  const { reportNo } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setReport(null);
    setError("");
    getReport(reportNo)
      .then((r) => !cancelled && setReport(r))
      .catch((e) => !cancelled && setError(e.response?.status === 404 ? "No report has this number." : e.message));
    return () => {
      cancelled = true;
    };
  }, [reportNo]);

  const { site, finding, media } = report || {};
  const located = site?.latitude != null && site?.longitude != null;

  return (
    <div className="mx-auto max-w-[880px]">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link to="/reports" className={`${btn.ghost} -ml-3`}>
          <ArrowLeft className="h-4 w-4" aria-hidden />
          All reports
        </Link>
        <div className="flex gap-2">
          {site && (
            <Link to={`/sites/${site.id}`} className={btn.secondary}>
              Open case file
            </Link>
          )}
          <button type="button" className={btn.primary} onClick={() => window.print()} disabled={!report}>
            <Printer className="h-4 w-4" aria-hidden />
            Print or save as PDF
          </button>
        </div>
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      {!error && (
        <article className="border-2 border-rule bg-surface print:border-0 print:bg-white">
          <header className="flex flex-wrap items-start justify-between gap-4 px-6 py-6 sm:px-8">
            <div>
              <p className="text-sm text-muted">Encroachment report</p>
              <h1 className="mt-1 text-[30px] font-bold leading-none tracking-tight">{reportNo}</h1>
              {report ? (
                <p className="mt-2 text-sm">
                  Issued {formatDateTime(report.created_at)} · {REASON_LABEL[report.reason] || report.reason}
                </p>
              ) : (
                <Skeleton className="mt-3 h-4 w-64" />
              )}
            </div>
            <div className="flex items-center gap-2.5">
              <Seal size="h-10 w-10" />
              <div className="leading-tight">
                <div className="font-bold">RailVigil</div>
                <div className="text-xs text-muted">Academic prototype</div>
              </div>
            </div>
          </header>

          <Block title="Site">
            {site ? (
              <dl className="grid gap-x-8 sm:grid-cols-2">
                <Field label="Site number">{shortSite(site.id)}</Field>
                <Field label="Class">{classLabel(site.cls)}</Field>
                <Field label="Severity">
                  <SeverityBadge value={site.max_severity} />
                </Field>
                <Field label="Stage when viewed">
                  <StatusBadge value={site.status} />
                </Field>
                <Field label="Findings at this site">{site.finding_count}</Field>
                <Field label="Position">{located ? `${site.latitude.toFixed(5)}, ${site.longitude.toFixed(5)}` : "Not recorded"}</Field>
              </dl>
            ) : report ? (
              <p className="text-sm text-muted">This report is not tied to a site.</p>
            ) : (
              <Skeleton className="h-24 w-full" />
            )}
          </Block>

          <Block title="Finding">
            {finding ? (
              <dl className="grid gap-x-8 sm:grid-cols-2">
                <Field label="Class">{classLabel(finding.cls)}</Field>
                <Field label="Detector label">{finding.label}</Field>
                <Field label="Share on railway land">{Math.round(finding.overlap_ratio * 100)} %</Field>
                <Field label="Detection confidence">{(finding.confidence * 100).toFixed(1)} %</Field>
                <Field label="Severity">
                  <SeverityBadge value={finding.severity} />
                </Field>
                <Field label="Model">{finding.sources?.join(", ")}</Field>
                {finding.notes?.length > 0 && (
                  <div className="py-2 text-sm sm:col-span-2">
                    <dt className="text-xs text-muted">Notes for the reviewer</dt>
                    <dd className="mt-0.5 font-medium text-sev-high">{finding.notes.join(" · ")}</dd>
                  </div>
                )}
              </dl>
            ) : report ? (
              <p className="text-sm text-muted">No finding is attached to this report.</p>
            ) : (
              <Skeleton className="h-24 w-full" />
            )}
          </Block>

          <Block title="Evidence">
            {finding ? (
              <>
                <EvidencePlan findings={[finding]} />
                <p className="mt-2 text-xs text-muted">
                  {media?.original_filename}
                  {media?.captured_at ? ` · photographed ${formatDateTime(media.captured_at)}` : ""}. Pink wash: the railway land outlined when the photo was
                  uploaded. Box: the finding.
                </p>
              </>
            ) : (
              <Skeleton className="aspect-[16/9] w-full" />
            )}
          </Block>

          {located && (
            <Block title="Location">
              <PlanMap
                compact
                className="h-[280px]"
                marks={[{ id: site.id, number: 1, lat: site.latitude, lon: site.longitude, severity: site.max_severity, label: shortSite(site.id) }]}
                selectedId={site.id}
                focusId={site.id}
                onSelect={() => {}}
              />
            </Block>
          )}

          <footer className="border-t-2 border-rule px-6 py-4 text-xs leading-relaxed text-muted sm:px-8">
            Issued automatically by RailVigil, an academic prototype. The finding is a candidate for officer review, not a determination. Verify on site
            before any action.
          </footer>
        </article>
      )}
    </div>
  );
}
