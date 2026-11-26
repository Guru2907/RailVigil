import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { format, startOfDay, subDays } from "date-fns";
import { getStatsSummary, listReports, listSites } from "../../api/encroachment.js";
import { listIncidents } from "../../api/incidents.js";
import { listVideos } from "../../api/videos.js";
import PlanMap from "../../components/plan/PlanMap.jsx";
import { ErrorBanner, SeverityBadge, Skeleton, btn } from "../../components/ui/index.jsx";
import { CLASS_LABEL, STATUS_LABEL, classLabel, shortSite } from "../../utils/encroachmentFormat.js";
import { eventLabel, shortId } from "../../utils/incidentFormat.js";
import { SEVERITY_COLOR, normaliseSeverity } from "../../utils/severity.js";
import { timeAgo } from "../../utils/formatDate.js";
import { chartTheme } from "../../utils/preferences.js";

const TREND_DAYS = 30;
const OPEN = "reported,under_review,verified,action_taken";
const STAGES = ["reported", "under_review", "verified", "action_taken", "resolved", "false_positive"];

function Sheet({ title, aside, children, className = "" }) {
  return (
    <section className={`min-w-0 border-2 border-rule bg-surface ${className}`}>
      <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-3">
        <h2 className="text-sm font-bold tracking-tight">{title}</h2>
        {aside}
      </header>
      {children}
    </section>
  );
}

function More({ to, children }) {
  return (
    <Link to={to} className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline">
      {children}
      <ArrowRight className="h-3.5 w-3.5" aria-hidden />
    </Link>
  );
}

function Waiting() {
  return (
    <div className="space-y-3 p-5">
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-4/5" />
      <Skeleton className="h-4 w-3/5" />
    </div>
  );
}

// Counts as ruled rows with a bar: label, bar to scale, figure.
function Bars({ rows, colour = "var(--color-ink)" }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <dl className="divide-y divide-line/70 px-5 py-1 text-sm">
      {rows.map((r) => (
        <div key={r.label} className="grid grid-cols-[9.5rem_1fr_2.5rem] items-center sm:grid-cols-[13.5rem_1fr_2.5rem] gap-3 py-2">
          <dt className="truncate">{r.label}</dt>
          <dd className="h-2 bg-canvas-2" aria-hidden>
            <span className="block h-full" style={{ width: `${(r.value / max) * 100}%`, background: r.colour || colour }} />
          </dd>
          <dd className="tabular text-right font-bold">{r.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function reportsPerDay(reports) {
  const today = startOfDay(new Date());
  const days = Array.from({ length: TREND_DAYS }, (_, i) => subDays(today, TREND_DAYS - 1 - i));
  const counts = Object.fromEntries(days.map((d) => [format(d, "yyyy-MM-dd"), 0]));
  reports.forEach((r) => {
    const key = format(new Date(r.created_at), "yyyy-MM-dd");
    if (key in counts) counts[key] += 1;
  });
  return days.map((d) => ({ day: format(d, "d MMM"), reports: counts[format(d, "yyyy-MM-dd")] }));
}

// What needs attention now, in both modules, and where things stand overall.
export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [critical, setCritical] = useState(null);
  const [incidents, setIncidents] = useState(null);
  const [reports, setReports] = useState([]);
  const [videos, setVideos] = useState([]);
  const [error, setError] = useState("");
  const [chosen, setChosen] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const guard = (set) => (v) => !cancelled && set(v);
    Promise.all([
      getStatsSummary().then(guard(setStats)),
      listSites({ status: OPEN, severity: "critical", limit: 6 }).then(guard(setCritical)),
      listIncidents().then(guard(setIncidents)),
      listReports({ limit: 500 }).then(guard(setReports)),
      listVideos().then(guard(setVideos)),
    ]).catch((e) => {
      if (cancelled) return;
      setError(e.message);
      // Whatever did not arrive is shown as empty, not as a skeleton that never ends.
      setCritical((v) => v ?? []);
      setIncidents((v) => v ?? []);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const enc = stats?.encroachment;
  const intr = stats?.intrusion;
  const sites = useMemo(() => (critical || []).slice(0, 6).map((s, i) => ({ ...s, number: i + 1 })), [critical]);
  const marks = useMemo(
    () =>
      sites
        .filter((s) => s.latitude != null && s.longitude != null)
        .map((s) => ({ id: s.id, number: s.number, lat: s.latitude, lon: s.longitude, severity: s.max_severity, label: `${shortSite(s.id)}, ${classLabel(s.cls)}` })),
    [sites],
  );
  const risky = useMemo(() => [...(incidents || [])].sort((a, b) => b.risk_score - a.risk_score).slice(0, 6), [incidents]);
  const trend = useMemo(() => reportsPerDay(reports), [reports]);
  const trendTotal = trend.reduce((n, d) => n + d.reports, 0);
  const videosDone = intr ? Object.values(intr.videos_by_status).reduce((a, b) => a + b, 0) : null;

  const figures = [
    ["Photos analysed", enc?.photos_by_status?.done, `${enc?.findings_total ?? "–"} findings`, "/encroachment/upload"],
    ["Open sites", enc?.sites_open, `${enc?.sites_total ?? "–"} in the register`, "/sites"],
    ["Critical open sites", enc?.critical_open_sites, "need review first", "/sites?severity=critical", true],
    ["Reports issued", enc?.reports_total, `${enc?.reports_last_7_days ?? "–"} in the last 7 days`, "/reports"],
    ["Videos analysed", videosDone, `${videos.filter((v) => v.status !== "done").length} in progress`, "/upload"],
    ["Intrusion incidents", intr?.incidents_total, `${intr?.incidents_by_severity?.critical ?? 0} critical`, "/incidents"],
  ];

  return (
    <>
      <div className="mb-4">
        <h1 className="text-[32px] font-bold leading-none tracking-tight">Dashboard</h1>
        <p className="mt-1.5 text-sm text-canvas-muted">What needs attention now, and where both modules stand. Every figure is counted from the database.</p>
      </div>

      {error && <ErrorBanner>The dashboard could not be loaded ({error}). Check that the backend is running, then reload.</ErrorBanner>}

      {/* One ruled strip of figures, each a way into its register */}
      <section className="grid grid-cols-2 border-2 border-rule bg-surface sm:grid-cols-3 xl:grid-cols-6" aria-label="Totals">
        {figures.map(([label, value, hint, to, alert]) => (
          <Link key={label} to={to} className="border-b border-r border-line px-5 py-4 transition-colors hover:bg-canvas-2">
            <div className="text-xs text-muted">{label}</div>
            <div className={`tabular mt-1 text-[30px] font-bold leading-none tracking-tight ${alert && value > 0 ? "text-sev-critical" : ""}`}>
              {value ?? <Skeleton className="h-7 w-14" />}
            </div>
            <div className="mt-1.5 text-xs text-muted">{hint}</div>
          </Link>
        ))}
      </section>

      {/* Needs attention: the two modules as equal halves, row for row */}
      <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Sheet title="Encroachment: critical sites awaiting action" aside={<More to="/sites?severity=critical">All critical sites</More>}>
          {critical === null ? (
            <Waiting />
          ) : sites.length === 0 ? (
            <p className="p-5 text-sm text-muted">No critical site is open. New ones appear here as photographs are analysed.</p>
          ) : (
            <ul className="divide-y divide-line">
              {sites.map((s) => (
                <li key={s.id} className={`flex min-h-[62px] flex-wrap items-center gap-x-3 gap-y-2 px-5 py-2.5 text-sm sm:flex-nowrap sm:py-0 ${chosen === s.id ? "bg-wash" : ""}`}>
                  <button type="button" onClick={() => setChosen(s.id)} className="flex min-w-0 flex-1 basis-full items-center gap-3 self-stretch text-left sm:basis-0" aria-label={`Show ${shortSite(s.id)} on the plan below`}>
                    <span className="grid h-[22px] w-[22px] shrink-0 place-items-center rounded-full text-[11px] font-bold text-white" style={{ background: SEVERITY_COLOR.critical }} aria-hidden>
                      {s.number}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-semibold">
                        {shortSite(s.id)} <span className="font-normal">· {classLabel(s.cls)}</span>
                      </span>
                      <span className="block text-xs text-muted">
                        {STATUS_LABEL[s.status]} · {s.finding_count} {s.finding_count === 1 ? "finding" : "findings"} · last seen {timeAgo(s.last_reported_at)}
                      </span>
                    </span>
                  </button>
                  <SeverityBadge value={s.max_severity} />
                  <Link to={`/sites/${s.id}`} className={`${btn.secondary} ${btn.small}`}>
                    Open case
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Sheet>

        <Sheet title="Intrusion: highest-risk incidents" aside={<More to="/incidents">All incidents</More>}>
          {incidents === null ? (
            <Waiting />
          ) : risky.length === 0 ? (
            <p className="p-5 text-sm text-muted">No incident has been recorded. Analyse a video to look for entries into a track zone.</p>
          ) : (
            <ul className="divide-y divide-line">
              {risky.map((i) => (
                <li key={i.id} className="flex min-h-[62px] flex-wrap items-center gap-x-3 gap-y-2 px-5 py-2.5 text-sm sm:flex-nowrap sm:py-0">
                  <span className="hidden w-24 shrink-0 items-center gap-2 sm:flex">
                    <span className="tabular w-6 text-right font-bold">{Math.round(i.risk_score)}</span>
                    <span className="h-1.5 flex-1 bg-canvas-2" aria-hidden>
                      <span className="block h-full" style={{ width: `${Math.min(100, i.risk_score)}%`, background: SEVERITY_COLOR[normaliseSeverity(i.severity)] }} />
                    </span>
                  </span>
                  <span className="min-w-0 flex-1 basis-full sm:basis-0">
                    <span className="block truncate font-semibold">
                      {shortId(i.id)} <span className="font-normal">· {eventLabel(i.event_type)}</span>
                    </span>
                    <span className="block text-xs text-muted">
                      <span className="sm:hidden">Risk {Math.round(i.risk_score)} · </span>
                      {i.dwell_time_sec.toFixed(1)} s in the zone · processed {timeAgo(i.created_at)}
                    </span>
                  </span>
                  <SeverityBadge value={i.severity} />
                  <button type="button" onClick={() => navigate(`/incidents/${i.id}`)} className={`${btn.secondary} ${btn.small}`}>
                    Open incident
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Sheet>
      </div>

      {marks.length > 0 && (
        <div className="mt-5">
          <PlanMap
            className="h-[320px]"
            marks={marks}
            selectedId={chosen || marks[0].id}
            focusId={chosen}
            onSelect={setChosen}
            onFitAll={() => setChosen(null)}
            sheet={{ page: 1, pages: 1, total: marks.length, onSheet: sites.length }}
          />
        </div>
      )}

      {/* Where things stand */}
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Sheet title="Sites by review stage" aside={<More to="/sites?all=1">Register</More>}>
          {enc ? <Bars rows={STAGES.map((s) => ({ label: STATUS_LABEL[s], value: enc.sites_by_status[s] || 0 }))} /> : <Skeleton className="m-5 h-40" />}
        </Sheet>
        <Sheet title="Findings by class">
          {enc ? (
            <Bars rows={Object.entries(CLASS_LABEL).map(([k, label]) => ({ label, value: enc.findings_by_class[k] || 0 }))} colour="var(--color-accent)" />
          ) : (
            <Skeleton className="m-5 h-40" />
          )}
        </Sheet>
        <Sheet title="Incidents by event">
          {intr ? (
            Object.keys(intr.incidents_by_type).length ? (
              <Bars rows={Object.entries(intr.incidents_by_type).map(([k, value]) => ({ label: eventLabel(k), value }))} colour="var(--color-info)" />
            ) : (
              <p className="p-5 text-sm text-muted">No incidents yet.</p>
            )
          ) : (
            <Skeleton className="m-5 h-40" />
          )}
        </Sheet>
      </div>

      <Sheet className="mt-5" title={`Reports issued per day, last ${TREND_DAYS} days`} aside={<span className="text-xs text-muted">{trendTotal} in this period</span>}>
        {trendTotal === 0 ? (
          <p className="p-5 text-sm text-muted">
            No report was issued in the last {TREND_DAYS} days{reports[0] ? `; the latest was ${timeAgo(reports[0].created_at)}` : ""}.
          </p>
        ) : (
          <div className="h-52 p-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trend} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
                <CartesianGrid stroke={chartTheme.grid} vertical={false} />
                <XAxis dataKey="day" tick={chartTheme.tick} interval={4} tickLine={false} axisLine={{ stroke: "var(--color-rule)" }} />
                <YAxis allowDecimals={false} tick={chartTheme.tick} tickLine={false} axisLine={false} />
                <Tooltip {...chartTheme.tooltip} />
                <Bar dataKey="reports" fill="var(--color-ink)" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Sheet>
    </>
  );
}
