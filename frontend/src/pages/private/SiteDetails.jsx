import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { getSite, updateSiteStatus } from "../../api/encroachment.js";
import EvidencePlan from "../../components/encroachment/EvidencePlan.jsx";
import FindingLines from "../../components/encroachment/FindingLines.jsx";
import PlanMap from "../../components/plan/PlanMap.jsx";
import { ErrorBanner, SeverityBadge, Skeleton, StatusBadge, btn, inputClass, linkClass } from "../../components/ui/index.jsx";
import { NEXT_STATUSES, REASON_LABEL, STATUS_LABEL, classLabel, shortSite } from "../../utils/encroachmentFormat.js";
import { formatDateTime, timeAgo } from "../../utils/formatDate.js";

// The normal path of a case; false positive is an exit from it.
const LIFECYCLE = ["reported", "under_review", "verified", "action_taken", "resolved"];
const ACTION_LABEL = {
  under_review: "Start review",
  verified: "Mark verified",
  action_taken: "Record action taken",
  resolved: "Mark resolved",
  false_positive: "Close as false positive",
  reported: "Reopen the case",
};

function Lifecycle({ status }) {
  const current = LIFECYCLE.indexOf(status);
  if (status === "false_positive") {
    return <p className="text-sm text-muted">Closed as a false positive. It can be reopened.</p>;
  }
  return (
    <ol className="flex items-start" aria-label="Case progress">
      {LIFECYCLE.map((s, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={s} className="flex min-w-0 flex-1 flex-col items-center gap-2 text-center" aria-current={active ? "step" : undefined}>
            <div className="flex w-full items-center">
              <span className={`h-0.5 flex-1 ${i === 0 ? "opacity-0" : done || active ? "bg-ink" : "bg-line"}`} />
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold ${
                  done ? "border-ink bg-ink text-surface" : active ? "border-ink bg-surface text-ink outline outline-2 outline-offset-2 outline-ink" : "border-line bg-surface text-muted"
                }`}
              >
                {done ? <Check className="h-4 w-4" aria-hidden /> : i + 1}
              </span>
              <span className={`h-0.5 flex-1 ${i === LIFECYCLE.length - 1 ? "opacity-0" : done ? "bg-ink" : "bg-line"}`} />
            </div>
            <span className={`text-xs leading-tight ${active ? "font-bold text-ink" : done ? "text-ink" : "text-muted"}`}>{STATUS_LABEL[s]}</span>
          </li>
        );
      })}
    </ol>
  );
}

function Sheet({ title, aside, children, className = "" }) {
  return (
    <section className={`border-2 border-rule bg-surface ${className}`}>
      <header className="flex items-baseline justify-between gap-3 border-b border-line px-5 py-3">
        <h2 className="text-sm font-bold tracking-tight">{title}</h2>
        {aside && <span className="text-xs text-muted">{aside}</span>}
      </header>
      {children}
    </section>
  );
}

// One site's case file: where it stands, the next action, the evidence on
// every photograph, where it is, and everything that has happened to it.
export default function SiteDetails() {
  const { id } = useParams();
  const [site, setSite] = useState(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setSite(null);
    setError("");
    getSite(id)
      .then((s) => !cancelled && setSite(s))
      .catch((e) => !cancelled && setError(e.response?.status === 404 ? "No site has this number." : e.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function move(status) {
    setSaving(true);
    setError("");
    try {
      setSite(await updateSiteStatus(id, status, note));
      setNote("");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  }

  // Findings grouped by the photograph they were found on, most severe first.
  const photos = useMemo(() => {
    const groups = new Map();
    [...(site?.findings || [])]
      .sort((a, b) => b.severity_score - a.severity_score)
      .forEach((f) => groups.set(f.media_id, [...(groups.get(f.media_id) || []), f]));
    return [...groups.values()];
  }, [site]);

  const located = site?.latitude != null && site?.longitude != null;
  const next = site ? NEXT_STATUSES[site.status] || [] : [];
  const forward = next.filter((s) => s !== "false_positive" && s !== "reported");
  const other = next.filter((s) => s === "false_positive" || s === "reported");

  return (
    <>
      <Link to="/sites" className={`${btn.ghost} -ml-3 mb-2`}>
        <ArrowLeft className="h-4 w-4" aria-hidden />
        All sites
      </Link>

      <div className="mb-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div>
          <h1 className="text-[32px] font-bold leading-none tracking-tight">{shortSite(id)}</h1>
          {site ? (
            <p className="mt-1.5 text-sm text-canvas-muted">
              {classLabel(site.cls)} · {site.finding_count} {site.finding_count === 1 ? "finding" : "findings"} on {photos.length}{" "}
              {photos.length === 1 ? "photograph" : "photographs"} · first reported {formatDateTime(site.first_reported_at)}
            </p>
          ) : (
            !error && <Skeleton className="mt-2 h-4 w-80" />
          )}
        </div>
        {site && (
          <div className="flex items-center gap-2">
            <SeverityBadge value={site.max_severity} />
            <StatusBadge value={site.status} />
          </div>
        )}
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      {site && (
        <>
          <Sheet title="Case progress" aside={`Last change ${timeAgo(site.history.at(-1)?.created_at)}`}>
            <div className="grid gap-6 p-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,420px)]">
              <div className="self-center">
                <Lifecycle status={site.status} />
              </div>
              <div className="lg:border-l lg:border-line lg:pl-6">
                <label htmlFor="note" className="mb-1.5 block text-xs font-semibold text-ink">
                  Note for this step <span className="font-normal text-muted">(optional, kept in the history)</span>
                </label>
                <textarea
                  id="note"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Field team confirmed a shed on railway land"
                  className={`${inputClass} !h-auto py-2`}
                  rows={2}
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  {forward.map((s) => (
                    <button key={s} type="button" disabled={saving} onClick={() => move(s)} className={btn.primary}>
                      {saving ? "Saving" : ACTION_LABEL[s]}
                    </button>
                  ))}
                  {other.map((s) => (
                    <button key={s} type="button" disabled={saving} onClick={() => move(s)} className={btn.secondary}>
                      {ACTION_LABEL[s]}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </Sheet>

          <div className="mt-5 grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,420px)]">
            <div className="min-w-0 space-y-5">
              {photos.map((findings, i) => (
                <Sheet key={findings[0].media_id} title={photos.length > 1 ? `Evidence, photograph ${i + 1} of ${photos.length}` : "Evidence"} aside={`${findings.length} on this photograph`}>
                  <div className="p-5">
                    <EvidencePlan findings={findings} />
                    <div className="mt-4">
                      <FindingLines findings={findings} detailed />
                    </div>
                    <Link to={`/photos/${findings[0].media_id}`} className={`${linkClass} mt-4 inline-block text-sm`}>
                      Open the full photo analysis
                    </Link>
                  </div>
                </Sheet>
              ))}
            </div>

            <div className="min-w-0 space-y-5">
              <Sheet title="Location" aside={located ? `${site.latitude.toFixed(5)}, ${site.longitude.toFixed(5)}` : "Not recorded"}>
                {located ? (
                  <PlanMap
                    compact
                    className="h-[260px] !border-0"
                    marks={[{ id: site.id, number: 1, lat: site.latitude, lon: site.longitude, severity: site.max_severity, label: shortSite(site.id) }]}
                    selectedId={site.id}
                    focusId={site.id}
                    onSelect={() => {}}
                  />
                ) : (
                  <p className="p-5 text-sm text-muted">The photographs of this site carried no position, so it cannot be placed on a plan.</p>
                )}
              </Sheet>

              <Sheet title="History" aside={`${site.history.length} ${site.history.length === 1 ? "entry" : "entries"}`}>
                <ol className="relative mx-5 my-5 space-y-4 border-l-2 border-line pl-5">
                  {site.history.map((h, i) => (
                    <li key={i} className="relative text-sm">
                      <span className="absolute -left-[27px] top-1 h-3 w-3 rounded-full border-2 border-surface bg-ink" aria-hidden />
                      <div className="flex flex-wrap items-center gap-1.5 font-semibold">
                        {h.from_status && (
                          <>
                            <span className="font-normal text-muted">{STATUS_LABEL[h.from_status]}</span>
                            <ArrowRight className="h-3.5 w-3.5 text-muted" aria-label="to" />
                          </>
                        )}
                        {STATUS_LABEL[h.to_status]}
                      </div>
                      <div className="text-xs text-muted">
                        {h.actor} · {formatDateTime(h.created_at)}
                      </div>
                      {h.note && <p className="mt-1.5 border border-line bg-canvas-2 px-3 py-2 text-sm">{h.note}</p>}
                    </li>
                  ))}
                </ol>
              </Sheet>

              <Sheet title="Reports" aside={`${site.reports.length} issued`}>
                {site.reports.length === 0 ? (
                  <p className="p-5 text-sm text-muted">No report has been issued for this site.</p>
                ) : (
                  <ul className="divide-y divide-line">
                    {site.reports.map((r) => (
                      <li key={r.report_no}>
                        <Link to={`/reports/${r.report_no}`} className="flex items-center justify-between gap-3 px-5 py-3 transition-colors hover:bg-canvas-2">
                          <span>
                            <span className="block font-bold">{r.report_no}</span>
                            <span className="block text-xs text-muted">
                              {REASON_LABEL[r.reason] || r.reason} · {formatDateTime(r.created_at)}
                            </span>
                          </span>
                          <ArrowRight className="h-4 w-4 text-muted" aria-hidden />
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </Sheet>
            </div>
          </div>
        </>
      )}
    </>
  );
}
