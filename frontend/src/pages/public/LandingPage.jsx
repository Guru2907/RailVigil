import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ImagePlus, Video } from "lucide-react";
import { getSite, getStatsSummary, listReports, listSites } from "../../api/encroachment.js";
import EvidencePlan from "../../components/encroachment/EvidencePlan.jsx";
import PlanMap from "../../components/plan/PlanMap.jsx";
import { SeverityBadge, Skeleton, btn } from "../../components/ui/index.jsx";
import { CountUp, Reveal } from "../../components/ui/motion.jsx";
import { REASON_LABEL, classLabel, shortSite } from "../../utils/encroachmentFormat.js";
import { timeAgo } from "../../utils/formatDate.js";

const OPEN = "reported,under_review,verified,action_taken";
// The site shown on the first screen. Set VITE_FEATURED_SITE_ID to choose one;
// otherwise it is the open site whose evidence the detector is most sure of.
const FEATURED = import.meta.env.VITE_FEATURED_SITE_ID;

const STEPS = [
  ["Photograph the track side", "Upload a photo and outline the railway land on it. The outline is the pink wash you see on every piece of evidence."],
  ["The detector marks what stands there", "Structures, vegetation, dumped material and parked vehicles are boxed, and each box is measured against the outlined land."],
  ["Findings become a site", "Findings of one kind within 25 m are one site, placed on the plan and given a numbered report."],
  ["An officer reviews it", "The site moves through review, verification and action, with a note at each step kept in its history."],
];

// Results measured on the project's own test sets (docs/EVALUATION.md, 26 Nov 2026).
const RESULTS = [
  ["13 of 13", "intrusions caught on 15 labelled test clips, at the setting the app runs with"],
  ["1.16 s", "average time from entering the track zone to the alert, at that setting"],
  ["0.160 vs 0.001", "box AP50 on shacks and stalls: the model trained here against the pretrained detectors"],
  ["0.48", "agreement between two people labelling the same photos, which is the ceiling for any model on them"],
];

function Section({ title, lede, children }) {
  return (
    <section className="border-t-2 border-rule py-14">
      <Reveal>
        <h2 className="max-w-[24ch] text-[34px] font-bold leading-[1.05] tracking-tight">{title}</h2>
        {lede && <p className="mt-3 max-w-[62ch] text-[17px] leading-relaxed text-canvas-muted">{lede}</p>}
      </Reveal>
      <div className="mt-8">{children}</div>
    </section>
  );
}

// The front door. Its first screen shows the product doing its job on real data:
// one photograph drawn as a land plan, and the same site as a mark on the plan.
export default function LandingPage() {
  const [stats, setStats] = useState(null);
  const [site, setSite] = useState(null);
  const [reports, setReports] = useState(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getStatsSummary()
      .then((s) => !cancelled && setStats(s))
      .catch(() => !cancelled && setOffline(true));
    listReports({ limit: 5 })
      .then((r) => !cancelled && setReports(r))
      .catch(() => !cancelled && setReports([]));
    const fallback = () => listSites({ status: OPEN, severity: "critical,high", limit: 1 }).then((list) => (list[0] ? getSite(list[0].id) : null));
    (FEATURED ? getSite(FEATURED).catch(fallback) : fallback())
      .then((s) => !cancelled && setSite(s || false))
      .catch(() => !cancelled && setSite(false));
    return () => {
      cancelled = true;
    };
  }, []);

  // The photograph holding the site's most severe finding, with every finding of the site on it.
  const onPhoto = useMemo(() => {
    const ranked = [...(site?.findings || [])].sort((a, b) => b.severity_score - a.severity_score);
    return ranked.filter((f) => f.media_id === ranked[0]?.media_id);
  }, [site]);
  const located = site && site.latitude != null && site.longitude != null;
  const enc = stats?.encroachment;
  const figures = [
    ["Photographs analysed", enc?.photos_by_status?.done],
    ["Open sites", enc?.sites_open],
    ["Critical sites awaiting review", enc?.critical_open_sites],
    ["Intrusion incidents recorded", stats?.intrusion?.incidents_total],
  ];

  return (
    <>
      <section className="pb-12 pt-6 text-center sm:pt-10">
        <h1 className="mx-auto max-w-[20ch] text-[40px] font-bold leading-[1.02] tracking-tight sm:text-[60px]">
          See what stands on railway land, and who steps onto the track.
        </h1>
        <p className="mx-auto mt-5 max-w-[60ch] text-[17px] leading-relaxed text-canvas-muted">
          RailVigil reads track-side photographs for structures, vegetation and vehicles on railway land, and CCTV video for people, vehicles and animals
          inside the track zone. Each detection becomes a case with its evidence, for an officer to review.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <Link to="/dashboard" className={`${btn.primary} !h-12 px-6 text-base`}>
            Open the dashboard
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <Link to="/encroachment/upload" className={`${btn.secondary} !h-12 px-6 text-base`}>
            <ImagePlus className="h-4 w-4" aria-hidden />
            Analyse a photo
          </Link>
        </div>
        {offline && <p className="mt-4 text-sm font-semibold text-sev-critical">The backend is not running, so live figures and evidence cannot be shown.</p>}

        <dl className="mx-auto mt-10 grid max-w-5xl grid-cols-2 border-2 border-rule bg-surface text-left lg:grid-cols-4">
          {figures.map(([label, value]) => (
            <div key={label} className="border-b border-r border-line px-5 py-4">
              <dd className="text-[34px] font-bold leading-none tracking-tight">
                <CountUp value={value} />
              </dd>
              <dt className="mt-1.5 text-sm text-muted">{label}</dt>
            </div>
          ))}
        </dl>
        <p className="mt-2 text-xs text-canvas-muted">Counted live from this installation's database.</p>
      </section>

      {/* The mechanism, on real data: a photograph as a land plan, and its mark on the plan */}
      <section aria-label="A site from the register" className="grid grid-cols-1 border-2 border-rule bg-surface lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <div className="min-w-0 border-b-2 border-rule p-4 lg:border-b-0 lg:border-r-2">
          {site === null ? <Skeleton className="aspect-[16/9] w-full !rounded-none" /> : site ? <EvidencePlan findings={onPhoto} /> : <EmptyHero />}
        </div>
        <div className="flex min-w-0 flex-col">
          {site ? (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
                <div>
                  <p className="text-lg font-bold tracking-tight">{shortSite(site.id)}</p>
                  <p className="text-sm text-muted">
                    {classLabel(site.cls)} · {site.finding_count} {site.finding_count === 1 ? "finding" : "findings"} · {Math.round((onPhoto[0]?.overlap_ratio || 0) * 100)} % on railway land
                  </p>
                </div>
                <SeverityBadge value={site.max_severity} />
              </div>
              {located && (
                <PlanMap
                  compact
                  className="h-[240px] !border-0"
                  marks={[{ id: site.id, number: 1, lat: site.latitude, lon: site.longitude, severity: site.max_severity, label: shortSite(site.id) }]}
                  selectedId={site.id}
                  focusId={site.id}
                  onSelect={() => {}}
                />
              )}
              <div className="mt-auto border-t border-line p-4">
                <Link to={`/sites/${site.id}`} className={`${btn.secondary} w-full`}>
                  Open this case file
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
              </div>
            </>
          ) : (
            site === null && <Skeleton className="m-5 h-40" />
          )}
        </div>
      </section>
      <p className="mt-2 text-xs text-canvas-muted">A site from the register, as an officer sees it. Pink wash: railway land outlined on the photo. Boxes: findings.</p>

      <div className="mt-14">
        <Section title="From a photograph to a case, in four steps">
          <ol className="grid gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map(([title, text], i) => (
              <Reveal key={title} delay={i * 0.06}>
                <li className="border-t border-rule pt-4">
                  <span className="text-sm font-bold text-accent">Step {i + 1}</span>
                  <h3 className="mt-1 text-lg font-bold leading-snug tracking-tight">{title}</h3>
                  <p className="mt-2 text-[15px] leading-relaxed text-canvas-muted">{text}</p>
                </li>
              </Reveal>
            ))}
          </ol>
        </Section>

        <Section title="Two modules, one register" lede="Both work on footage you already have. Neither needs new cameras or sensors.">
          <div className="grid gap-5 lg:grid-cols-2">
            <Reveal>
              <article className="flex h-full flex-col border-2 border-rule bg-surface p-6">
                <ImagePlus className="h-6 w-6 text-accent" aria-hidden />
                <h3 className="mt-3 text-2xl font-bold tracking-tight">Encroachment, from photographs</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-muted">
                  Permanent and temporary structures, vegetation, dumped material and parked vehicles on railway land. Severity comes from how much of the
                  object sits on the outlined land. Sites carry a review stage, a history and numbered reports.
                </p>
                <div className="mt-auto flex flex-wrap gap-3 pt-5">
                  <Link to="/encroachment/upload" className={btn.primary}>
                    Analyse a photo
                  </Link>
                  <Link to="/sites" className={btn.secondary}>
                    Open the sites
                  </Link>
                </div>
              </article>
            </Reveal>
            <Reveal delay={0.06}>
              <article className="flex h-full flex-col border-2 border-rule bg-surface p-6">
                <Video className="h-6 w-6 text-accent" aria-hidden />
                <h3 className="mt-3 text-2xl font-bold tracking-tight">Intrusion, from video</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-muted">
                  People, vehicles and animals inside a track zone you draw on the video. An incident is recorded once the object has stayed in the zone,
                  with a risk score from how long and how deep, a saved frame and the clip.
                </p>
                <div className="mt-auto flex flex-wrap gap-3 pt-5">
                  <Link to="/upload" className={btn.primary}>
                    Analyse a video
                  </Link>
                  <Link to="/incidents" className={btn.secondary}>
                    Open the incidents
                  </Link>
                </div>
              </article>
            </Reveal>
          </div>
        </Section>

        <Section
          title="Measured, not claimed"
          lede="Every figure below was produced by the evaluation scripts in the repository, on test photos labelled without seeing any model's output and on labelled test clips. The sets are small, and the write-up says so."
        >
          <dl className="grid gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
            {RESULTS.map(([figure, text], i) => (
              <Reveal key={figure} delay={i * 0.06}>
                <div className="border-t border-rule pt-4">
                  <dd className="text-[32px] font-bold leading-none tracking-tight">{figure}</dd>
                  <dt className="mt-2 text-[15px] leading-relaxed text-canvas-muted">{text}</dt>
                </div>
              </Reveal>
            ))}
          </dl>
          <p className="mt-6 max-w-[80ch] text-sm leading-relaxed text-canvas-muted">
            Evaluation of 26 November 2026. The detector was trained and tested on 561 photographs from India and 13 other countries (412 for
            training, 75 for validation, 66 held back for the test) and 15 test clips. The figures at the top of this page count only what has been
            analysed through this installation.
          </p>
        </Section>

        <Section title="Latest reports">
          {reports === null ? (
            <Skeleton className="h-40 w-full" />
          ) : reports.length === 0 ? (
            <p className="text-canvas-muted">No report has been issued yet. One is raised when an analysed photo creates a site or shows a critical finding.</p>
          ) : (
            <ul className="border-2 border-rule bg-surface">
              {reports.map((r) => (
                <li key={r.report_no} className="border-b border-line last:border-b-0">
                  <Link to={`/reports/${r.report_no}`} className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1 px-5 py-3.5 transition-colors hover:bg-canvas-2">
                    <span className="font-bold">{r.report_no}</span>
                    <span className="text-sm text-muted">
                      {REASON_LABEL[r.reason] || r.reason}
                      {r.site_id ? ` · ${shortSite(r.site_id)}` : ""} · {timeAgo(r.created_at)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Link to="/reports" className={`${btn.secondary} mt-5`}>
            Open the report register
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </Section>
      </div>
    </>
  );
}

function EmptyHero() {
  return (
    <div className="grid aspect-[16/9] place-items-center bg-canvas-2 p-8 text-center text-sm text-muted">
      <span className="max-w-[44ch]">No critical site is open at the moment. Analyse a photo to see its findings drawn on the railway land here.</span>
    </div>
  );
}
