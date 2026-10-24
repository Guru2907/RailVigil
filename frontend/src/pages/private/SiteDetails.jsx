import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, TileLayer } from "react-leaflet";
import { Check } from "lucide-react";
import { getSite, updateSiteStatus } from "../../api/encroachment.js";
import FindingList from "../../components/encroachment/FindingList.jsx";
import { Card, ErrorBanner, PageHeader, btn, inputClass } from "../../components/ui/index.jsx";
import {
  NEXT_STATUSES,
  REASON_LABEL,
  SEVERITY_COLOR,
  STATUS_LABEL,
  classLabel,
  severityBadge,
  shortSite,
  statusBadge,
} from "../../utils/encroachmentFormat.js";
import { formatDateTime } from "../../utils/formatDate.js";
import { DARK_BASE, RAILWAYS } from "../../utils/mapTiles.js";

// The normal path of a case; false positive is an exit from it.
const LIFECYCLE = ["reported", "under_review", "verified", "action_taken", "resolved"];

function Lifecycle({ status }) {
  const current = LIFECYCLE.indexOf(status);
  if (status === "false_positive") {
    return <p className="text-sm text-muted">Closed as a false positive. It can be reopened if needed.</p>;
  }
  return (
    <ol className="flex items-center gap-1" aria-label="Case progress">
      {LIFECYCLE.map((s, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={s} className="flex min-w-0 flex-1 flex-col items-center gap-1.5 text-center">
            <div className="flex w-full items-center">
              <span className={`h-0.5 flex-1 ${i === 0 ? "opacity-0" : done || active ? "bg-ink" : "bg-line"}`} />
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 text-[10px] font-bold ${
                  done ? "border-ink bg-ink text-surface" : active ? "border-ink bg-surface text-ink" : "border-line bg-surface text-muted"
                }`}
              >
                {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </span>
              <span className={`h-0.5 flex-1 ${i === LIFECYCLE.length - 1 ? "opacity-0" : done ? "bg-ink" : "bg-line"}`} />
            </div>
            <span className={`text-[10px] leading-tight ${active ? "font-semibold text-ink" : "text-muted"}`}>{STATUS_LABEL[s]}</span>
          </li>
        );
      })}
    </ol>
  );
}

export default function SiteDetails() {
  const { id } = useParams();
  const [site, setSite] = useState(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getSite(id)
      .then((s) => !cancelled && setSite(s))
      .catch((e) => !cancelled && setError(e.response?.status === 404 ? "Site not found." : e.message));
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

  const crumbs = [["Encroachment"], ["Sites", "/sites"], [site ? shortSite(site.id) : "Site"]];

  if (!site) {
    return (
      <>
        <PageHeader crumbs={crumbs} title="Site case" />
        {error ? <ErrorBanner>{error}</ErrorBanner> : <p className="text-sm text-canvas-muted">Loading…</p>}
      </>
    );
  }

  return (
    <>
      <PageHeader
        crumbs={crumbs}
        title={
          <span className="flex flex-wrap items-center gap-3">
            <span className="font-mono">{shortSite(site.id)}</span>
            <span className="text-canvas-muted">·</span>
            <span>{classLabel(site.cls)}</span>
          </span>
        }
        description={`First reported ${formatDateTime(site.first_reported_at)} · ${site.finding_count} finding(s)`}
        actions={
          <div className="flex items-center gap-2 rounded-md bg-surface px-3 py-2">
            <span className={severityBadge(site.max_severity)}>{site.max_severity}</span>
            <span className={statusBadge(site.status)}>{STATUS_LABEL[site.status]}</span>
          </div>
        }
      />
      {error && <ErrorBanner>{error}</ErrorBanner>}

      <div className="grid gap-6 lg:grid-cols-5">
        {/* 60%: evidence */}
        <div className="space-y-6 lg:col-span-3">
          <Card title="Evidence" subtitle="Crops of every finding grouped into this site">
            <FindingList findings={site.findings} showSite={false} />
          </Card>
          <Card title="Location" subtitle={`${site.latitude.toFixed(5)}, ${site.longitude.toFixed(5)}`} bodyClass="" className="overflow-hidden">
            <MapContainer center={[site.latitude, site.longitude]} zoom={17} className="rv-map h-72 w-full" scrollWheelZoom={false}>
              <TileLayer {...DARK_BASE} maxNativeZoom={DARK_BASE.maxZoom} maxZoom={19} />
              <TileLayer {...RAILWAYS} opacity={0.7} />
              <CircleMarker
                center={[site.latitude, site.longitude]}
                radius={10}
                pathOptions={{ color: SEVERITY_COLOR[site.max_severity], fillOpacity: 0.6 }}
              />
            </MapContainer>
          </Card>
        </div>

        {/* 40%: case */}
        <div className="space-y-6 lg:col-span-2">
          <Card title="Case progress">
            <Lifecycle status={site.status} />
            <div className="mt-6 border-t border-line pt-5">
              <label htmlFor="note" className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-muted">
                Officer note
              </label>
              <textarea
                id="note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="e.g. Field team confirmed shed on railway land"
                className={inputClass}
                rows={2}
              />
              <div className="mt-3 flex flex-wrap gap-2">
                {NEXT_STATUSES[site.status].map((s) => (
                  <button
                    key={s}
                    disabled={saving}
                    onClick={() => move(s)}
                    className={s === "false_positive" || s === "reported" ? btn.secondary : btn.primary}
                  >
                    {s === "reported" ? "Reopen" : `Mark ${STATUS_LABEL[s].toLowerCase()}`}
                  </button>
                ))}
              </div>
            </div>
          </Card>

          <Card title="Case history">
            <ol className="relative space-y-4 border-l-2 border-line pl-5">
              {site.history.map((h, i) => (
                <li key={i} className="relative text-sm">
                  <span className="absolute -left-[27px] top-1 h-3 w-3 rounded-full border-2 border-surface bg-ink" aria-hidden />
                  <div className="font-medium">
                    {h.from_status ? `${STATUS_LABEL[h.from_status]} → ` : ""}
                    {STATUS_LABEL[h.to_status]}
                  </div>
                  <div className="font-mono text-[11px] text-muted">
                    {h.actor} · {formatDateTime(h.created_at)}
                  </div>
                  {h.note && <p className="mt-1 rounded bg-paper px-3 py-2 text-sm">“{h.note}”</p>}
                </li>
              ))}
            </ol>
          </Card>

          <Card title="Reports" bodyClass="p-0">
            <ul className="divide-y divide-line">
              {site.reports.map((r) => (
                <li key={r.report_no} className="flex items-center justify-between gap-3 px-6 py-3">
                  <div>
                    <div className="font-mono text-xs font-semibold">{r.report_no}</div>
                    <div className="text-xs text-muted">{REASON_LABEL[r.reason] || r.reason}</div>
                  </div>
                  <span className="font-mono text-[11px] text-muted">{formatDateTime(r.created_at)}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </>
  );
}
