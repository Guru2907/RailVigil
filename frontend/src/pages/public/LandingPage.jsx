import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Camera,
  ClipboardCheck,
  FileText,
  Layers,
  Map as MapIcon,
  MapPin,
  ScanSearch,
  ShieldAlert,
  Video,
} from "lucide-react";
import { getStatsSummary, listReports } from "../../api/encroachment.js";
import { listIncidents } from "../../api/incidents.js";
import { REASON_LABEL, SEVERITIES, SEVERITY_COLOR } from "../../utils/encroachmentFormat.js";
import { shortId } from "../../utils/incidentFormat.js";
import { timeAgo } from "../../utils/formatDate.js";

const modules = [
  {
    Icon: Camera,
    tag: "Encroachment · photos",
    title: "Find what shouldn't be on railway land",
    points: [
      "Huts, sheds, buildings, vegetation, dumped material and parked vehicles",
      "Severity from how much of each object lies inside the right-of-way",
      "Repeat findings within 25 m grouped into one site with a report number",
    ],
    to: "/encroachment/upload",
    cta: "Analyse photos",
  },
  {
    Icon: Video,
    tag: "Intrusion · video",
    title: "Confirm people and vehicles entering the track zone",
    points: [
      "YOLOv8 detection with ByteTrack tracking across frames",
      "Time-based confirmation filters out one-frame false alarms",
      "Risk score from depth into the zone, dwell time and object type",
    ],
    to: "/upload",
    cta: "Analyse a video",
  },
];

const steps = [
  { Icon: Layers, title: "Upload", desc: "Photos or video, with the railway land outlined once." },
  { Icon: ScanSearch, title: "Detect", desc: "YOLOv8-family models find candidate objects." },
  { Icon: ShieldAlert, title: "Score", desc: "Overlap with railway land and category give a severity." },
  { Icon: MapPin, title: "Map & review", desc: "Sites appear on the GIS map for officers to verify." },
];

const stack = ["YOLOv8", "YOLO-World", "ByteTrack", "FastAPI", "PostgreSQL + PostGIS", "React", "Leaflet", "OpenRailwayMap"];

function useLiveData() {
  const [data, setData] = useState(null);
  const [offline, setOffline] = useState(false);
  useEffect(() => {
    let cancelled = false;
    Promise.all([getStatsSummary(), listReports({ limit: 4 }), listIncidents()])
      .then(([stats, reports, incidents]) => {
        if (cancelled) return;
        const activity = [
          ...reports.map((r) => ({ at: r.created_at, id: r.report_no, msg: REASON_LABEL[r.reason] || r.reason, kind: "Encroachment" })),
          ...incidents.map((i) => ({ at: i.created_at, id: shortId(i.id), msg: `${i.object_class} in track zone`, kind: "Intrusion" })),
        ]
          .sort((a, b) => new Date(b.at) - new Date(a.at))
          .slice(0, 4);
        setData({ stats, activity });
      })
      .catch(() => !cancelled && setOffline(true));
    return () => {
      cancelled = true;
    };
  }, []);
  return { data, offline };
}

function OpsPanel({ data, offline }) {
  const enc = data?.stats.encroachment;
  const total = enc?.findings_total || 0;
  return (
    <div className="rounded-2xl border border-line bg-surface/80 p-5 backdrop-blur">
      <div className="flex items-center justify-between font-mono text-[11px] tracking-widest">
        <span className="flex items-center gap-2 text-muted">
          <span className={`h-1.5 w-1.5 rounded-full ${offline ? "bg-danger" : "animate-pulse bg-emerald-400"}`} />
          {offline ? "BACKEND OFFLINE" : "LIVE OPERATIONS"}
        </span>
        <span className="text-muted/70">RAILVIGIL</span>
      </div>

      <div className="mt-5">
        <div className="mb-2 text-xs text-muted">Findings by severity</div>
        <div className="flex h-2.5 overflow-hidden rounded-full bg-surface-2">
          {SEVERITIES.map((s) => {
            const n = enc?.findings_by_severity?.[s] || 0;
            return total ? <div key={s} style={{ width: `${(n / total) * 100}%`, background: SEVERITY_COLOR[s] }} /> : null;
          })}
        </div>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted">
          {SEVERITIES.map((s) => (
            <span key={s} className="flex items-center gap-1.5 capitalize">
              <span className="h-2 w-2 rounded-full" style={{ background: SEVERITY_COLOR[s] }} />
              {s} <b className="font-mono text-ink">{enc?.findings_by_severity?.[s] ?? 0}</b>
            </span>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <div className="mb-2 text-xs text-muted">Latest activity</div>
        {data?.activity?.length ? (
          <ul className="divide-y divide-line">
            {data.activity.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <div className="truncate text-sm text-ink first-letter:uppercase">{a.msg}</div>
                  <div className="font-mono text-[11px] text-muted">{a.id}</div>
                </div>
                <div className="shrink-0 text-right">
                  <div
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      a.kind === "Encroachment" ? "bg-accent/15 text-accent-hover" : "bg-amber-500/15 text-amber-300"
                    }`}
                  >
                    {a.kind}
                  </div>
                  <div className="mt-1 text-[11px] text-muted">{timeAgo(a.at)}</div>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="py-6 text-center text-sm text-muted">
            {offline ? "Start the backend to see live data." : data ? "No activity yet. Upload a photo to begin." : "Loading…"}
          </p>
        )}
      </div>
    </div>
  );
}

export default function LandingPage() {
  const { data, offline } = useLiveData();
  const enc = data?.stats.encroachment;
  const intr = data?.stats.intrusion;
  const v = (x) => (data ? x ?? 0 : "—");
  const kpis = [
    ["Photos analysed", v(enc?.photos_by_status?.done)],
    ["Open sites", v(enc?.sites_open)],
    ["Reports issued", v(enc?.reports_total)],
    ["Intrusion incidents", v(intr?.incidents_total)],
  ];

  return (
    <div className="min-h-screen overflow-x-hidden bg-canvas text-ink">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-line/60 bg-canvas/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-xs font-bold text-white">RV</div>
            <span className="font-semibold tracking-tight">RailVigil</span>
          </Link>
          <nav className="hidden items-center gap-8 text-sm text-muted md:flex">
            <a href="#modules" className="hover:text-ink">
              Modules
            </a>
            <a href="#how" className="hover:text-ink">
              How it works
            </a>
            <Link to="/map" className="hover:text-ink">
              Live map
            </Link>
          </nav>
          <Link to="/dashboard" className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-accent-hover">
            Open dashboard
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_70%_0%,rgba(76,141,255,0.16),transparent)]" />
        <div className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:linear-gradient(#8B96AD_1px,transparent_1px),linear-gradient(90deg,#8B96AD_1px,transparent_1px)] [background-size:48px_48px]" />
        <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-6 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:py-28">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-xs text-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              Railway land monitoring · YOLOv8 + GIS
            </div>
            <h1 className="mt-6 text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
              See encroachment on railway land <span className="text-accent">before it spreads.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
              RailVigil turns track-side photos and CCTV video into geolocated, severity-ranked cases on a map of India,
              ready for an officer to verify and act on.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/map"
                className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-3 font-medium text-white transition hover:bg-accent-hover"
              >
                <MapIcon className="h-4 w-4" /> Open live map
              </Link>
              <Link
                to="/encroachment/upload"
                className="inline-flex items-center gap-2 rounded-lg border border-line bg-surface px-5 py-3 font-medium text-ink transition hover:bg-surface-2"
              >
                Analyse a photo <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
          <OpsPanel data={data} offline={offline} />
        </div>
      </section>

      {/* KPIs */}
      <section className="border-y border-line bg-surface/50">
        <div className="mx-auto grid max-w-6xl grid-cols-2 divide-line px-6 md:grid-cols-4 md:divide-x">
          {kpis.map(([label, value]) => (
            <div key={label} className="px-2 py-8 md:px-6">
              <div className="font-mono text-3xl font-semibold">{value}</div>
              <div className="mt-1 text-sm text-muted">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Modules */}
      <section id="modules" className="mx-auto max-w-6xl scroll-mt-20 px-6 py-24">
        <div className="max-w-2xl">
          <div className="text-sm font-medium text-accent">Two modules, one dashboard</div>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight">Encroachment and intrusion, side by side</h2>
        </div>
        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {modules.map(({ Icon, tag, title, points, to, cta }) => (
            <div key={tag} className="flex flex-col rounded-2xl border border-line bg-surface p-6 transition hover:border-accent/50">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/15 text-accent">
                  <Icon className="h-5 w-5" />
                </div>
                <span className="text-sm text-muted">{tag}</span>
              </div>
              <h3 className="mt-5 text-xl font-semibold">{title}</h3>
              <ul className="mt-4 flex-1 space-y-2.5 text-sm text-muted">
                {points.map((p) => (
                  <li key={p} className="flex gap-2.5">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent" />
                    {p}
                  </li>
                ))}
              </ul>
              <Link to={to} className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent-hover">
                {cta} <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="scroll-mt-20 border-t border-line bg-surface/40">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <div className="text-sm font-medium text-accent">How it works</div>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight">From photo to reviewed case</h2>
          <ol className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map(({ Icon, title, desc }, i) => (
              <li key={title} className="rounded-2xl border border-line bg-surface p-6">
                <div className="flex items-center justify-between">
                  <Icon className="h-5 w-5 text-accent" />
                  <span className="font-mono text-xs text-muted">0{i + 1}</span>
                </div>
                <h3 className="mt-4 font-semibold">{title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{desc}</p>
              </li>
            ))}
          </ol>

          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {[
              [ClipboardCheck, "Human in the loop", "Every finding is a candidate. Officers verify, act on or dismiss it, and each step is logged."],
              [FileText, "Traceable reports", "Each site gets numbered reports (RV-ENC-YYYY-NNNNNN) linked to its evidence."],
              [MapPin, "Located on the map", "GPS from the photo, or a map pin, places each site on the railway network."],
            ].map(([Icon, title, desc]) => (
              <div key={title} className="flex gap-4">
                <Icon className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
                <div>
                  <h3 className="font-semibold">{title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stack + CTA */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="rounded-2xl border border-line bg-gradient-to-br from-accent/15 to-surface p-8 md:p-12">
          <h2 className="text-2xl font-semibold tracking-tight md:text-3xl">Explore the live system</h2>
          <p className="mt-2 max-w-xl text-muted">Open the dashboard to see current sites, reports and incidents.</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/dashboard" className="rounded-lg bg-accent px-5 py-3 font-medium text-white hover:bg-accent-hover">
              Open dashboard
            </Link>
            <Link to="/map" className="rounded-lg border border-line bg-surface px-5 py-3 font-medium hover:bg-surface-2">
              View map
            </Link>
          </div>
          <div className="mt-10 flex flex-wrap gap-2">
            {stack.map((s) => (
              <span key={s} className="rounded-md border border-line bg-canvas/60 px-2.5 py-1 font-mono text-xs text-muted">
                {s}
              </span>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-8 text-sm text-muted md:flex-row md:items-center md:justify-between">
          <span>RailVigil · Automated railway track encroachment detection</span>
          <span>Detections are candidates for officer review, not legal determinations.</span>
        </div>
      </footer>
    </div>
  );
}
