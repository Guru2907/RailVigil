import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listVideos } from "../../api/videos.js";
import { listIncidents } from "../../api/incidents.js";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from "recharts";
import { fmtTime, sevClass, shortId } from "../../utils/incidentFormat.js";

function sevColor(name) {
  if (name === "HIGH" || name === "CRITICAL") return "#E11D48";
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
  done: "bg-emerald-100 text-emerald-700",
  processing: "bg-amber-100 text-amber-700",
  uploaded: "bg-amber-100 text-amber-700",
  failed: "bg-tactical-alert/15 text-tactical-alert",
};

export default function Dashboard() {
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

  const videosAnalyzed = videos.filter((v) => v.status === "done").length;
  const highRisk = incidents.filter((i) =>
    ["HIGH", "CRITICAL"].includes((i.severity || "").toUpperCase()),
  ).length;
  const persistent = incidents.filter((i) => i.is_persistent).length;

  const recentIncidents = [...incidents]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 5);

  const recentVideos = [...videos]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 5);

  const incidentCount = (videoId) =>
    incidents.filter((i) => i.video_id === videoId).length;

  const sevOrder = ["CRITICAL", "HIGH", "MEDIUM", "MED", "LOW"];
  const bySeverity = countBy(incidents, (i) => (i.severity || "UNKNOWN").toUpperCase()).sort(
    (a, b) =>
      (sevOrder.indexOf(a.name) === -1 ? 99 : sevOrder.indexOf(a.name)) -
      (sevOrder.indexOf(b.name) === -1 ? 99 : sevOrder.indexOf(b.name))
  );
  const byType = countBy(incidents, (i) => i.event_type || "unknown").sort((a, b) => b.value - a.value);

  const stats = [
    ["Videos analyzed", videosAnalyzed],
    ["Confirmed incidents", incidents.length],
    ["High-risk incidents", highRisk],
    ["Persistent encroachments", persistent],
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="mb-8">
        <div className="text-xs font-mono text-tactical-mint mb-2">
          DASHBOARD
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Overview</h1>
        <p className="mt-2 text-white/60 max-w-md">
          What RailVigil has detected across every video you&apos;ve analyzed.
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-2xl bg-tactical-alert/15 text-tactical-alert text-sm font-mono px-5 py-3">
          Could not load data: {error}
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map(([label, value]) => (
          <div
            key={label}
            className="rounded-3xl bg-tactical-card text-tactical-dark p-6 shadow-lg border border-emerald-200/50 hover:-translate-y-1 transition-all duration-300"
          >
            <div className="text-3xl font-semibold font-mono">
              {loading ? "…" : value}
            </div>
            <div className="mt-1 text-sm text-tactical-dark/60">{label}</div>
          </div>
        ))}
      </div>

      {/* Recent incidents + recent videos */}
      <div className="mt-6 grid lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 rounded-3xl bg-tactical-card text-tactical-dark p-6 shadow-lg border border-emerald-200/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Recent incidents</h3>
            <Link to="/incidents" className="text-sm font-medium text-emerald-700 hover:underline">
              View all →
            </Link>
          </div>
          {loading ? (
            <p className="text-sm text-tactical-dark/60">Loading…</p>
          ) : recentIncidents.length === 0 ? (
            <p className="text-sm text-tactical-dark/60">No incidents yet. Analyze a video to record some.</p>
          ) : (
            <div className="rounded-2xl bg-white border border-black/5 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="text-left text-[11px] font-mono text-tactical-dark/50">
                  <tr>
                    {["ID", "TIME", "OBJECT", "RISK", "SEVERITY"].map((h) => (
                      <th key={h} className="px-4 py-3 font-normal">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="font-mono">
                  {recentIncidents.map((i) => (
                    <tr
                      key={i.id}
                      onClick={() => navigate(`/incidents/${i.id}`)}
                      className="cursor-pointer border-t border-black/5 hover:bg-emerald-50 transition-all duration-200"
                    >
                      <td className="px-4 py-3">{shortId(i.id)}</td>
                      <td className="px-4 py-3">{fmtTime(i.start_ts)}</td>
                      <td className="px-4 py-3">
                        {i.object_class} #{i.track_id}
                      </td>
                      <td className="px-4 py-3">{Math.round(i.risk_score)}</td>
                      <td className="px-4 py-3">
                        <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${sevClass(i.severity)}`}>
                          {(i.severity || "").toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="lg:col-span-2 rounded-3xl bg-tactical-card text-tactical-dark p-6 shadow-lg border border-emerald-200/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Recent analysis</h3>
            <Link to="/upload" className="text-sm font-medium text-emerald-700 hover:underline">
              New analysis →
            </Link>
          </div>
          {loading ? (
            <p className="text-sm text-tactical-dark/60">Loading…</p>
          ) : recentVideos.length === 0 ? (
            <p className="text-sm text-tactical-dark/60">No videos analyzed yet.</p>
          ) : (
            <ul className="space-y-3">
              {recentVideos.map((v) => (
                <li key={v.id} className="rounded-2xl bg-white border border-black/5 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium truncate">{v.original_filename || v.filename}</span>
                    <span
                      className={`shrink-0 text-[10px] font-mono font-semibold px-2.5 py-1 rounded-full ${
                        statusStyle[v.status] || "bg-black/5 text-tactical-dark/60"
                      }`}
                    >
                      {v.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-xs font-mono text-tactical-dark/50">
                    <span>{new Date(v.created_at).toLocaleString()}</span>
                    <span>{v.status === "done" ? `${incidentCount(v.id)} incidents` : "—"}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

           {/* Incident overview charts */}
      <div className="mt-6 grid lg:grid-cols-2 gap-6">
        {[
          ["Incidents by severity", bySeverity, true],
          ["Incidents by type", byType, false],
        ].map(([title, data, colorBySeverity]) => (
          <div
            key={title}
            className="min-w-0 rounded-3xl bg-tactical-card text-tactical-dark p-6 shadow-lg border border-emerald-200/50"
          >
            <h3 className="font-semibold mb-4">{title}</h3>
            {loading ? (
              <p className="text-sm text-tactical-dark/60">Loading…</p>
            ) : data.length === 0 ? (
              <p className="text-sm text-tactical-dark/60">No incident data yet.</p>
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.08)" />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: "ui-monospace, monospace" }} tickLine={false} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11, fontFamily: "ui-monospace, monospace" }} tickLine={false} axisLine={false} />
                    <Tooltip
                      cursor={{ fill: "rgba(0,0,0,0.04)" }}
                      contentStyle={{ borderRadius: 12, border: "1px solid rgba(0,0,0,0.08)", fontSize: 12 }}
                    />
                    <Bar dataKey="value" name="Incidents" radius={[8, 8, 0, 0]}>
                      {data.map((d) => (
                        <Cell key={d.name} fill={colorBySeverity ? sevColor(d.name) : "#18181B"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
