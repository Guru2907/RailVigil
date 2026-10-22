import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, TileLayer } from "react-leaflet";
import { getMapFeatures, getStatsSummary, listReports } from "../../api/encroachment.js";
import {
  CLASS_LABEL,
  REASON_LABEL,
  SEVERITIES,
  SEVERITY_COLOR,
  STATUS_LABEL,
  shortSite,
} from "../../utils/encroachmentFormat.js";
import { timeAgo } from "../../utils/formatDate.js";

const card = "rounded-3xl bg-tactical-card text-tactical-dark p-6 shadow-lg border border-emerald-200/50";

export default function EncroachmentDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [reports, setReports] = useState([]);
  const [features, setFeatures] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([getStatsSummary(), listReports({ limit: 6 }), getMapFeatures()])
      .then(([s, r, geo]) => {
        if (cancelled) return;
        setStats(s.encroachment);
        setReports(r);
        setFeatures(geo.features || []);
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div className="rounded-2xl bg-tactical-alert/15 text-tactical-alert text-sm font-mono px-5 py-3">
        Could not load data: {error}
      </div>
    );
  }

  const v = (x) => (stats ? x : "…");
  const kpis = [
    ["Photos analysed", v(stats?.photos_by_status?.done ?? 0)],
    ["Open sites", v(stats?.sites_open)],
    ["Critical open sites", v(stats?.critical_open_sites), true],
    ["Reports (7 days)", v(stats?.reports_last_7_days)],
  ];

  const bySeverity = SEVERITIES.map((s) => ({ name: s, value: stats?.findings_by_severity?.[s] || 0 }));
  const byClass = Object.entries(CLASS_LABEL)
    .map(([k, label]) => ({ name: label, value: stats?.findings_by_class?.[k] || 0 }))
    .sort((a, b) => b.value - a.value);

  const center = features.length
    ? [features[0].geometry.coordinates[1], features[0].geometry.coordinates[0]]
    : [22.5, 79.0];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        {kpis.map(([label, value, alert]) => (
          <div key={label} className={`${card} hover:-translate-y-1 transition-all duration-300`}>
            <div className={`text-3xl font-semibold font-mono ${alert && value > 0 ? "text-tactical-alert" : ""}`}>{value}</div>
            <div className="mt-1 text-sm text-tactical-dark/60">{label}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        <div className={`${card} lg:col-span-3 overflow-hidden p-0`}>
          <div className="flex items-center justify-between px-6 pt-5 pb-3">
            <h3 className="font-semibold">Site map</h3>
            <Link to="/map" className="text-sm font-medium text-emerald-700 hover:underline">
              Open full map →
            </Link>
          </div>
          <MapContainer center={center} zoom={features.length ? 13 : 4} className="h-72 w-full" scrollWheelZoom={false}>
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution="&copy; OpenStreetMap contributors &copy; CARTO"
              subdomains="abcd"
            />
            {features.map((f) => (
              <CircleMarker
                key={f.id}
                center={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
                radius={7}
                pathOptions={{ color: SEVERITY_COLOR[f.properties.max_severity], fillOpacity: 0.7 }}
                eventHandlers={{ click: () => navigate(`/sites/${f.id}`) }}
              />
            ))}
          </MapContainer>
        </div>

        <div className={`${card} lg:col-span-2`}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Latest reports</h3>
            <Link to="/reports" className="text-sm font-medium text-emerald-700 hover:underline">
              View all →
            </Link>
          </div>
          {reports.length === 0 ? (
            <p className="text-sm text-tactical-dark/50">No reports yet.</p>
          ) : (
            <ul className="space-y-2">
              {reports.map((r) => (
                <li
                  key={r.report_no}
                  onClick={() => r.site_id && navigate(`/sites/${r.site_id}`)}
                  className="flex items-center justify-between rounded-xl px-3 py-2 hover:bg-emerald-50 cursor-pointer"
                >
                  <div>
                    <div className="font-mono text-xs font-semibold">{r.report_no}</div>
                    <div className="text-xs text-tactical-dark/60">
                      {REASON_LABEL[r.reason]} · {r.site_id ? shortSite(r.site_id) : "no location"}
                    </div>
                  </div>
                  <span className="text-xs text-tactical-dark/50">{timeAgo(r.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className={card}>
          <h3 className="font-semibold mb-4">Findings by severity</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={bySeverity}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {bySeverity.map((d) => (
                  <Cell key={d.name} fill={SEVERITY_COLOR[d.name]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className={card}>
          <h3 className="font-semibold mb-4">Findings by class</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={byClass} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#10B981" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className={card}>
          <h3 className="font-semibold mb-4">Sites by status</h3>
          <ul className="space-y-2 text-sm">
            {Object.entries(STATUS_LABEL).map(([k, label]) => (
              <li key={k} className="flex justify-between border-b border-tactical-dark/5 pb-1">
                <span>{label}</span>
                <span className="font-mono font-semibold">{stats?.sites_by_status?.[k] || 0}</span>
              </li>
            ))}
            <li className="flex justify-between pt-2 text-tactical-dark/60">
              <span>Findings without location</span>
              <span className="font-mono">{stats?.findings_without_location ?? 0}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
