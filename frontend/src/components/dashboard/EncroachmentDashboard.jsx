import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, TileLayer } from "react-leaflet";
import { format, startOfDay, subDays } from "date-fns";
import { getMapFeatures, getStatsSummary, listReports } from "../../api/encroachment.js";
import { Card, EmptyState, ErrorBanner, StatCard, btn } from "../ui/index.jsx";
import { CLASS_LABEL, REASON_LABEL, SEVERITIES, SEVERITY_COLOR, STATUS_LABEL, shortSite } from "../../utils/encroachmentFormat.js";
import { timeAgo } from "../../utils/formatDate.js";
import { chartTheme } from "../../utils/preferences.js";
import { DARK_BASE, RAILWAYS } from "../../utils/mapTiles.js";

const TREND_DAYS = 14;

// Reports issued per day over the last TREND_DAYS days (from real report dates).
function reportTrend(reports) {
  const today = startOfDay(new Date());
  const days = Array.from({ length: TREND_DAYS }, (_, i) => subDays(today, TREND_DAYS - 1 - i));
  const counts = Object.fromEntries(days.map((d) => [format(d, "yyyy-MM-dd"), 0]));
  reports.forEach((r) => {
    const key = format(new Date(r.created_at), "yyyy-MM-dd");
    if (key in counts) counts[key] += 1;
  });
  return days.map((d) => ({ day: format(d, "dd MMM"), reports: counts[format(d, "yyyy-MM-dd")] }));
}

export default function EncroachmentDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [reports, setReports] = useState([]);
  const [features, setFeatures] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([getStatsSummary(), listReports({ limit: 500 }), getMapFeatures()])
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

  const trend = useMemo(() => reportTrend(reports), [reports]);
  const loading = !stats && !error;

  const bySeverity = SEVERITIES.map((s) => ({ name: s, value: stats?.findings_by_severity?.[s] || 0 }));
  const byClass = Object.entries(CLASS_LABEL)
    .map(([k, label]) => ({ name: label, value: stats?.findings_by_class?.[k] || 0 }))
    .sort((a, b) => b.value - a.value);

  const center = features.length ? [features[0].geometry.coordinates[1], features[0].geometry.coordinates[0]] : [22.5, 79.0];

  return (
    <div className="space-y-6">
      {error && <ErrorBanner>Could not load data: {error}</ErrorBanner>}

      <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
        <StatCard label="Photos analysed" value={stats?.photos_by_status?.done ?? 0} hint={`${stats?.findings_total ?? 0} findings`} loading={loading} />
        <StatCard label="Open sites" value={stats?.sites_open} hint={`${stats?.sites_total ?? 0} sites in total`} loading={loading} />
        <StatCard label="Critical open sites" value={stats?.critical_open_sites} tone="danger" hint="Need priority review" loading={loading} />
        <StatCard label="Reports · last 7 days" value={stats?.reports_last_7_days} hint={`${stats?.reports_today ?? 0} today`} loading={loading} />
      </div>

      {/* 60 / 40: map and register */}
      <div className="grid gap-6 lg:grid-cols-5">
        <Card
          className="overflow-hidden lg:col-span-3"
          title="Site map"
          subtitle={`${features.length} located sites`}
          action={
            <Link to="/map" className={`${btn.primary} ${btn.small}`}>
              Open GIS map
            </Link>
          }
          bodyClass=""
        >
          <MapContainer key={features.length} center={center} zoom={features.length ? 13 : 4} className="rv-map h-80 w-full" scrollWheelZoom={false}>
            <TileLayer {...DARK_BASE} maxNativeZoom={DARK_BASE.maxZoom} maxZoom={19} />
            <TileLayer {...RAILWAYS} opacity={0.7} />
            {features.map((f) => (
              <CircleMarker
                key={f.id}
                center={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
                radius={8}
                pathOptions={{ color: SEVERITY_COLOR[f.properties.max_severity], fillOpacity: 0.75, weight: 2 }}
                eventHandlers={{ click: () => navigate(`/sites/${f.id}`) }}
              />
            ))}
          </MapContainer>
        </Card>

        <Card
          className="lg:col-span-2"
          title="Latest reports"
          action={
            <Link to="/reports" className={`${btn.secondary} ${btn.small}`}>
              Register
            </Link>
          }
          bodyClass="p-0"
        >
          {reports.length === 0 ? (
            <EmptyState>{loading ? "Loading…" : "No reports yet."}</EmptyState>
          ) : (
            <ul className="divide-y divide-line">
              {reports.slice(0, 6).map((r) => (
                <li key={r.report_no}>
                  <button
                    onClick={() => r.site_id && navigate(`/sites/${r.site_id}`)}
                    className="flex w-full items-center justify-between gap-3 px-6 py-3 text-left transition-colors hover:bg-surface-2"
                  >
                    <div className="min-w-0">
                      <div className="font-mono text-xs font-semibold">{r.report_no}</div>
                      <div className="text-xs text-muted">
                        {REASON_LABEL[r.reason]} · {r.site_id ? shortSite(r.site_id) : "no location"}
                      </div>
                    </div>
                    <span className="shrink-0 font-mono text-[11px] text-muted">{timeAgo(r.created_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Reports issued" subtitle={`Last ${TREND_DAYS} days`}>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
              <CartesianGrid stroke={chartTheme.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" tick={chartTheme.tick} tickLine={false} axisLine={{ stroke: chartTheme.grid }} interval="preserveStartEnd" />
              <YAxis allowDecimals={false} tick={chartTheme.tick} tickLine={false} axisLine={false} />
              <Tooltip {...chartTheme.tooltip} />
              <Line type="monotone" dataKey="reports" name="Reports" stroke={chartTheme.bar} strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Findings by severity">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bySeverity} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid stroke={chartTheme.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={chartTheme.tick} tickLine={false} axisLine={{ stroke: chartTheme.grid }} />
                <YAxis allowDecimals={false} tick={chartTheme.tick} tickLine={false} axisLine={false} />
                <Tooltip {...chartTheme.tooltip} />
                <Bar dataKey="value" name="Findings" radius={[4, 4, 0, 0]}>
                  {bySeverity.map((d) => (
                    <Cell key={d.name} fill={SEVERITY_COLOR[d.name]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Encroachment types">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byClass} layout="vertical" margin={{ top: 0, right: 12, left: 8, bottom: 0 }}>
                <CartesianGrid stroke={chartTheme.grid} strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={chartTheme.tick} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="name" width={130} tick={chartTheme.tick} tickLine={false} axisLine={false} />
                <Tooltip {...chartTheme.tooltip} />
                <Bar dataKey="value" name="Findings" fill={chartTheme.bar} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Sites by review status">
          <dl className="divide-y divide-line rounded-md border border-line bg-paper text-sm">
            {Object.entries(STATUS_LABEL).map(([k, label]) => (
              <div key={k} className="flex items-center justify-between px-4 py-2.5">
                <dt>{label}</dt>
                <dd className="tabular font-mono font-semibold">{stats?.sites_by_status?.[k] || 0}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs text-muted">
            {stats?.findings_without_location ?? 0} findings have no location and are not on the map.
          </p>
        </Card>
      </div>
    </div>
  );
}
