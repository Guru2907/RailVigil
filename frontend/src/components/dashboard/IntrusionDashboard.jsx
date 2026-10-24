import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { listVideos } from "../../api/videos.js";
import { listIncidents } from "../../api/incidents.js";
import { Card, EmptyState, ErrorBanner, StatCard, Table, btn, cellClass, rowClass } from "../ui/index.jsx";
import { fmtTime, sevClass, shortId } from "../../utils/incidentFormat.js";
import { formatDateTime } from "../../utils/formatDate.js";
import { chartTheme } from "../../utils/preferences.js";

function sevColor(name) {
  if (name === "CRITICAL") return "#E11D48";
  if (name === "HIGH") return "#F97316";
  if (name === "MEDIUM" || name === "MED") return "#F59E0B";
  return "#10B981";
}

function countBy(list, keyFn) {
  const counts = {};
  list.forEach((item) => {
    const key = keyFn(item);
    counts[key] = (counts[key] || 0) + 1;
  });
  return Object.entries(counts).map(([name, value]) => ({ name, value }));
}

const statusStyle = {
  done: "bg-emerald-500/12 text-emerald-800 obsidian:text-emerald-300",
  processing: "bg-amber-400/15 text-amber-800 obsidian:text-amber-300",
  queued: "bg-amber-400/15 text-amber-800 obsidian:text-amber-300",
  failed: "bg-danger/10 text-danger",
};

const SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "MED", "LOW"];

export default function IntrusionDashboard() {
  const navigate = useNavigate();
  const [videos, setVideos] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([listVideos(), listIncidents()])
      .then(([v, i]) => {
        if (cancelled) return;
        setVideos(v);
        setIncidents(i);
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const byDate = (a, b) => new Date(b.created_at) - new Date(a.created_at);
  const recentIncidents = [...incidents].sort(byDate).slice(0, 6);
  const recentVideos = [...videos].sort(byDate).slice(0, 5);
  const incidentCount = (videoId) => incidents.filter((i) => i.video_id === videoId).length;
  const rank = (n) => (SEV_ORDER.indexOf(n) === -1 ? 99 : SEV_ORDER.indexOf(n));
  const bySeverity = countBy(incidents, (i) => (i.severity || "UNKNOWN").toUpperCase()).sort((a, b) => rank(a.name) - rank(b.name));
  const byType = countBy(incidents, (i) => i.event_type || "unknown").sort((a, b) => b.value - a.value);

  return (
    <div className="space-y-6">
      {error && <ErrorBanner>Could not load data: {error}</ErrorBanner>}

      <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
        <StatCard label="Videos analysed" value={videos.filter((v) => v.status === "done").length} loading={loading} />
        <StatCard label="Confirmed incidents" value={incidents.length} loading={loading} />
        <StatCard
          label="High-risk incidents"
          value={incidents.filter((i) => ["HIGH", "CRITICAL"].includes((i.severity || "").toUpperCase())).length}
          tone="danger"
          loading={loading}
        />
        <StatCard label="Persistent intrusions" value={incidents.filter((i) => i.is_persistent).length} loading={loading} />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card
          className="lg:col-span-3"
          title="Recent incidents"
          action={
            <Link to="/incidents" className={`${btn.secondary} ${btn.small}`}>
              All incidents
            </Link>
          }
          bodyClass=""
        >
          {loading ? (
            <EmptyState>Loading…</EmptyState>
          ) : recentIncidents.length === 0 ? (
            <EmptyState>No incidents yet. Analyse a video to record some.</EmptyState>
          ) : (
            <Table head={["ID", "Time", "Object", "Risk", "Severity"]}>
              {recentIncidents.map((i) => (
                <tr key={i.id} onClick={() => navigate(`/incidents/${i.id}`)} className={rowClass}>
                  <td className={`${cellClass} font-mono font-semibold`}>{shortId(i.id)}</td>
                  <td className={`${cellClass} tabular font-mono`}>{fmtTime(i.start_ts)}</td>
                  <td className={cellClass}>
                    {i.object_class} <span className="font-mono text-muted">#{i.track_id}</span>
                  </td>
                  <td className={`${cellClass} tabular font-mono`}>{Math.round(i.risk_score)}</td>
                  <td className={cellClass}>
                    <span className={`px-2 py-0.5 text-[10px] font-bold ${sevClass(i.severity)}`}>{i.severity}</span>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card
          className="lg:col-span-2"
          title="Recent video analyses"
          action={
            <Link to="/upload" className={`${btn.primary} ${btn.small}`}>
              New analysis
            </Link>
          }
        >
          {loading ? (
            <EmptyState>Loading…</EmptyState>
          ) : recentVideos.length === 0 ? (
            <EmptyState>No videos analysed yet.</EmptyState>
          ) : (
            <ul className="divide-y divide-line rounded-md border border-line bg-paper">
              {recentVideos.map((v) => (
                <li key={v.id} className="px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate text-sm font-medium">{v.original_filename || v.filename}</span>
                    <span className={`shrink-0 rounded px-2 py-0.5 font-mono text-[10px] font-semibold uppercase ${statusStyle[v.status] || "text-muted"}`}>
                      {v.status}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-between font-mono text-xs text-muted">
                    <span>{formatDateTime(v.created_at)}</span>
                    <span>{v.status === "done" ? `${incidentCount(v.id)} incidents` : "—"}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {[
          ["Incidents by severity", bySeverity, true],
          ["Incidents by type", byType, false],
        ].map(([title, data, colorBySeverity]) => (
          <Card key={title} title={title}>
            {loading ? (
              <EmptyState>Loading…</EmptyState>
            ) : data.length === 0 ? (
              <EmptyState>No incident data yet.</EmptyState>
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                    <CartesianGrid stroke={chartTheme.grid} strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tick={chartTheme.tick} tickLine={false} axisLine={{ stroke: chartTheme.grid }} />
                    <YAxis allowDecimals={false} tick={chartTheme.tick} tickLine={false} axisLine={false} />
                    <Tooltip {...chartTheme.tooltip} />
                    <Bar dataKey="value" name="Incidents" radius={[4, 4, 0, 0]}>
                      {data.map((d) => (
                        <Cell key={d.name} fill={colorBySeverity ? sevColor(d.name) : chartTheme.bar} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
