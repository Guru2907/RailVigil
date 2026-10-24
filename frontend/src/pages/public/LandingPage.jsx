import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Camera, ClipboardCheck, Layers, Map as MapIcon, ScanSearch, ShieldAlert, Video } from "lucide-react";
import { fileUrl, getPhoto, getStatsSummary, listPhotos, listReports } from "../../api/encroachment.js";
import { Card, StatCard, Table, btn, cellClass, rowClass } from "../../components/ui/index.jsx";
import { REASON_LABEL, SEVERITIES, SEVERITY_COLOR, classLabel, shortSite } from "../../utils/encroachmentFormat.js";
import { formatDateTime } from "../../utils/formatDate.js";


const SEV_RANK = Object.fromEntries(SEVERITIES.map((s, i) => [s, i]));

const pipeline = [
  { Icon: Layers, title: "Upload", desc: "Track-side photo or CCTV video, with the right-of-way outlined once." },
  { Icon: ScanSearch, title: "Detect", desc: "YOLOv8-family models locate structures, vegetation, dumps, vehicles and people." },
  { Icon: ShieldAlert, title: "Score", desc: "Overlap with railway land and object category set the severity." },
  { Icon: ClipboardCheck, title: "Review", desc: "Geolocated sites are verified, actioned or dismissed by an officer." },
];

const modules = [
  {
    Icon: Camera,
    code: "MODULE A",
    title: "Physical encroachment",
    desc: "Photographs of the corridor are checked for unauthorised structures, vegetation, waste, material dumps and parked vehicles on railway land.",
    points: ["Six-class railway taxonomy", "Severity from overlap with the right-of-way", "Repeat findings within 25 m grouped into one site"],
    to: "/encroachment/upload",
    cta: "Open photo analysis",
  },
  {
    Icon: Video,
    code: "MODULE B",
    title: "Track-zone intrusion",
    desc: "CCTV video is checked for people and vehicles entering the safety zone, confirmed over time to avoid one-frame false alarms.",
    points: ["YOLOv8 detection with ByteTrack", "Dwell-time confirmation", "Risk from depth, duration and object type"],
    to: "/upload",
    cta: "Open video analysis",
  },
];

// Latest analysed photo with its most severe finding, used as the hero visual.
function useLatestEvidence() {
  const [evidence, setEvidence] = useState(null);
  useEffect(() => {
    let cancelled = false;
    listPhotos({ status: "done", limit: 10 })
      .then((photos) => Promise.all(photos.map((p) => getPhoto(p.id))))
      .then((details) => {
        // Most severe evidence first; more findings breaks a tie.
        const score = (d) => Math.min(...d.findings.map((f) => SEV_RANK[f.severity])) * 100 - d.findings.length;
        return details.filter((d) => d.findings.length && d.annotated_url).sort((a, b) => score(a) - score(b))[0] || null;
      })
      .then((d) => !cancelled && setEvidence(d))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);
  if (!evidence) return null;
  const worst = [...evidence.findings].sort((a, b) => SEV_RANK[a.severity] - SEV_RANK[b.severity])[0];
  return { photo: evidence, worst };
}

function EvidenceFrame({ evidence }) {
  return (
    <figure className="overflow-hidden rounded-lg border border-canvas-line bg-black shadow-2xl shadow-black/40">
      <div className="flex items-center justify-between border-b border-white/10 bg-black px-4 py-2 font-mono text-[10px] tracking-widest text-white/60">
        <span className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-danger" /> LATEST EVIDENCE
        </span>
        <span className="truncate pl-4">{evidence ? evidence.photo.original_filename : "AWAITING DATA"}</span>
      </div>
      <div className="relative aspect-[4/3]">
        {evidence ? (
          <img src={fileUrl(evidence.photo.annotated_url)} alt="Latest analysed photo with detections" className="h-full w-full object-cover" />
        ) : (
          <svg viewBox="0 0 400 300" className="h-full w-full" aria-hidden>
            <rect width="400" height="300" fill="#05100c" />
            <polygon points="60,300 180,60 220,60 340,300" fill="rgba(225,29,72,0.12)" stroke="#E11D48" strokeDasharray="6 5" />
            <path d="M150 300 L195 60 M250 300 L205 60" stroke="#34D399" strokeWidth="2" opacity="0.7" />
          </svg>
        )}
        {evidence && (
          <figcaption className="absolute inset-x-3 bottom-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md bg-black/80 px-3 py-2 font-mono text-[11px] text-white backdrop-blur">
            <span className="font-semibold uppercase">{classLabel(evidence.worst.cls)}</span>
            <span className="text-white/40">|</span>
            <span className="tabular">{(evidence.worst.confidence * 100).toFixed(1)}%</span>
            <span className="text-white/40">|</span>
            <span className="tabular">ON RAILWAY LAND {Math.round(evidence.worst.overlap_ratio * 100)}%</span>
            <span
              className="ml-auto rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-black"
              style={{ background: SEVERITY_COLOR[evidence.worst.severity] }}
            >
              {evidence.worst.severity}
            </span>
          </figcaption>
        )}
      </div>
    </figure>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();
  const evidence = useLatestEvidence();
  const [stats, setStats] = useState(null);
  const [reports, setReports] = useState([]);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getStatsSummary(), listReports({ limit: 5 })])
      .then(([s, r]) => {
        if (cancelled) return;
        setStats(s);
        setReports(r);
      })
      .catch(() => !cancelled && setOffline(true));
    return () => {
      cancelled = true;
    };
  }, []);

  const enc = stats?.encroachment;
  const loading = !stats && !offline;
  const v = (x) => (offline ? "—" : x ?? 0);

  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="grid items-center gap-10 pt-4 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">Railway right-of-way monitoring</div>
          <h1 className="mt-4 text-4xl font-semibold leading-[1.1] tracking-tight text-canvas-ink md:text-5xl">
            Intelligent Railway Track-Side Encroachment Detection
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-canvas-muted md:text-lg">
            YOLOv8 analysis of track-side photographs and CCTV video, scored against spatial safety corridors and tracked as
            geolocated cases for officer review.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/dashboard" className={`${btn.primary} px-5 py-3 ring-1 ring-canvas-line`}>
              Open command dashboard <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/map" className={`${btn.outline} px-5 py-3`}>
              <MapIcon className="h-4 w-4" /> View GIS map
            </Link>
          </div>
          {offline && (
            <p className="mt-6 font-mono text-xs text-rose-300">Backend offline: start the API server to load live data.</p>
          )}
        </div>
        <EvidenceFrame evidence={evidence} />
      </section>

      {/* KPIs */}
      <section aria-label="Current status" className="grid grid-cols-2 gap-6 lg:grid-cols-4">
        <StatCard label="Photos analysed" value={v(enc?.photos_by_status?.done)} loading={loading} />
        <StatCard label="Open sites" value={v(enc?.sites_open)} loading={loading} />
        <StatCard label="Critical open sites" value={v(enc?.critical_open_sites)} tone="danger" loading={loading} />
        <StatCard label="Intrusion incidents" value={v(stats?.intrusion?.incidents_total)} loading={loading} />
      </section>

      {/* Methodology */}
      <section aria-labelledby="method">
        <div className="mb-6 flex items-end justify-between gap-4 border-b border-canvas-line pb-4">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal">Methodology</div>
            <h2 id="method" className="mt-2 text-2xl font-semibold tracking-tight">From evidence to action</h2>
          </div>
        </div>
        <ol className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {pipeline.map(({ Icon, title, desc }, i) => (
            <li key={title} className="relative rounded-lg border border-line bg-surface p-6 text-ink shadow-lg shadow-black/20">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold text-muted">0{i + 1}</span>
                <Icon className="h-5 w-5" aria-hidden />
              </div>
              <h3 className="mt-4 font-semibold">{title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{desc}</p>
              {i < pipeline.length - 1 && (
                <ArrowRight className="absolute -right-5 top-1/2 hidden h-4 w-4 -translate-y-1/2 text-canvas-muted lg:block" aria-hidden />
              )}
            </li>
          ))}
        </ol>
      </section>

      {/* Modules */}
      <section aria-label="Modules" className="grid gap-6 lg:grid-cols-2">
        {modules.map(({ Icon, code, title, desc, points, to, cta }) => (
          <Card key={code} bodyClass="flex h-full flex-col p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-accent text-accent-ink">
                <Icon className="h-5 w-5" aria-hidden />
              </div>
              <div>
                <div className="font-mono text-[10px] font-semibold tracking-widest text-muted">{code}</div>
                <h3 className="text-lg font-semibold">{title}</h3>
              </div>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-muted">{desc}</p>
            <ul className="mt-4 flex-1 space-y-2 text-sm">
              {points.map((p) => (
                <li key={p} className="flex gap-2.5">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-sm bg-signal" aria-hidden />
                  {p}
                </li>
              ))}
            </ul>
            <div className="mt-6">
              <Link to={to} className={btn.primary}>
                {cta} <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </Card>
        ))}
      </section>

      {/* Public register */}
      <Card
        title="Register of latest encroachment reports"
        subtitle="Issued automatically for a new site, a re-encroached site or a critical finding"
        action={
          <Link to="/reports" className={`${btn.secondary} ${btn.small}`}>
            Full register
          </Link>
        }
        bodyClass=""
      >
        {reports.length ? (
          <Table head={["Report no.", "Reason", "Site", "Issued"]}>
            {reports.map((r) => (
              <tr key={r.report_no} className={rowClass} onClick={() => r.site_id && navigate(`/sites/${r.site_id}`)}>
                <td className={`${cellClass} font-mono font-semibold`}>{r.report_no}</td>
                <td className={cellClass}>{REASON_LABEL[r.reason] || r.reason}</td>
                <td className={`${cellClass} font-mono text-xs`}>{r.site_id ? shortSite(r.site_id) : "No location"}</td>
                <td className={`${cellClass} font-mono text-xs text-muted`}>{formatDateTime(r.created_at)}</td>
              </tr>
            ))}
          </Table>
        ) : (
          <p className="px-6 py-8 text-center text-sm text-muted">{offline ? "Backend offline." : "No reports issued yet."}</p>
        )}
      </Card>
    </div>
  );
}
