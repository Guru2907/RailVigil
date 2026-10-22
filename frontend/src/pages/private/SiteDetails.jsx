import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, TileLayer } from "react-leaflet";
import { getSite, updateSiteStatus } from "../../api/encroachment.js";
import FindingList from "../../components/encroachment/FindingList.jsx";
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

  if (error && !site) return <div className="p-6 text-rose-300">{error}</div>;
  if (!site) return <div className="p-6 text-white/60">Loading…</div>;

  const card = "rounded-3xl bg-tactical-card p-5 text-tactical-dark shadow-lg";

  return (
    <div className="space-y-6 p-6">
      <Link to="/sites" className="text-sm text-emerald-300 hover:underline">
        ← All sites
      </Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-mono text-2xl font-semibold">{shortSite(site.id)}</h1>
        <span className="text-lg">{classLabel(site.cls)}</span>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${severityBadge(site.max_severity)}`}>
          {site.max_severity}
        </span>
        <span className={`rounded-full px-2.5 py-0.5 text-xs ${statusBadge(site.status)}`}>{STATUS_LABEL[site.status]}</span>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className={`${card} overflow-hidden p-0 lg:col-span-1`}>
          <MapContainer center={[site.latitude, site.longitude]} zoom={17} className="h-64 w-full" scrollWheelZoom={false}>
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution="&copy; OpenStreetMap contributors &copy; CARTO"
              subdomains="abcd"
            />
            <TileLayer url="https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png" subdomains="abc" opacity={0.7} attribution="&copy; OpenRailwayMap" />
            <CircleMarker
              center={[site.latitude, site.longitude]}
              radius={10}
              pathOptions={{ color: SEVERITY_COLOR[site.max_severity], fillOpacity: 0.6 }}
            />
          </MapContainer>
          <dl className="space-y-1 p-4 font-mono text-xs">
            <div className="flex justify-between">
              <dt className="text-tactical-dark/50">Coords</dt>
              <dd>
                {site.latitude.toFixed(5)}, {site.longitude.toFixed(5)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-tactical-dark/50">First reported</dt>
              <dd>{formatDateTime(site.first_reported_at)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-tactical-dark/50">Last reported</dt>
              <dd>{formatDateTime(site.last_reported_at)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-tactical-dark/50">Findings</dt>
              <dd>{site.finding_count}</dd>
            </div>
          </dl>
        </div>

        <div className={`${card} lg:col-span-2`}>
          <h2 className="mb-3 font-semibold">Review workflow</h2>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Note for the record (optional), e.g. 'Field team confirmed shed on railway land'"
            className="mb-3 w-full rounded-xl border border-tactical-dark/15 bg-white p-3 text-sm outline-none focus:border-emerald-500"
            rows={2}
          />
          <div className="flex flex-wrap gap-2">
            {NEXT_STATUSES[site.status].map((s) => (
              <button
                key={s}
                disabled={saving}
                onClick={() => move(s)}
                className={`rounded-full px-4 py-2 text-sm font-medium disabled:opacity-50 ${
                  s === "false_positive" ? "bg-zinc-200 text-zinc-700 hover:bg-zinc-300" : "bg-tactical-dark text-white hover:bg-black"
                }`}
              >
                → {STATUS_LABEL[s]}
              </button>
            ))}
          </div>
          {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}

          <h3 className="mb-2 mt-6 text-sm font-semibold uppercase tracking-wide text-tactical-dark/50">History</h3>
          <ol className="space-y-2 border-l-2 border-emerald-300 pl-4">
            {site.history.map((h, i) => (
              <li key={i} className="text-sm">
                <span className="font-medium">
                  {h.from_status ? `${STATUS_LABEL[h.from_status]} → ` : ""}
                  {STATUS_LABEL[h.to_status]}
                </span>
                <span className="text-tactical-dark/50"> · {h.actor} · {formatDateTime(h.created_at)}</span>
                {h.note && <div className="text-tactical-dark/70">“{h.note}”</div>}
              </li>
            ))}
          </ol>

          <h3 className="mb-2 mt-6 text-sm font-semibold uppercase tracking-wide text-tactical-dark/50">Reports</h3>
          <ul className="space-y-1 text-sm">
            {site.reports.map((r) => (
              <li key={r.report_no} className="flex justify-between font-mono text-xs">
                <span className="font-semibold">{r.report_no}</span>
                <span>{REASON_LABEL[r.reason] || r.reason}</span>
                <span className="text-tactical-dark/50">{formatDateTime(r.created_at)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className={card}>
        <h2 className="mb-3 font-semibold">Evidence ({site.findings.length})</h2>
        <FindingList findings={site.findings} showSite={false} />
      </div>
    </div>
  );
}
