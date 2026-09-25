import { Link } from "react-router-dom";

const iconProps = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8 };

function CameraIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <path d="M23 7l-7 5 7 5V7z" />
      <rect x="1" y="5" width="15" height="14" rx="2" />
    </svg>
  );
}
function PinIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}
function PulseIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  );
}
function ShieldIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M12 8v5" />
    </svg>
  );
}
function ArrowIcon(props) {
  return (
    <svg {...iconProps} strokeWidth="2" {...props}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

const steps = [
  { n: "01", title: "Detect", desc: "YOLOv8 finds people and vehicles in every frame.", Icon: CameraIcon },
  { n: "02", title: "Analyze", desc: "Each detection is tested against the safety corridor.", Icon: PinIcon },
  { n: "03", title: "Confirm", desc: "Dwell-time logic filters out one-frame false alarms.", Icon: PulseIcon },
  { n: "04", title: "Act", desc: "Confirmed events become incidents with evidence.", Icon: ShieldIcon },
];

const log = [
  { t: "00:14:32", id: "INC-1024", msg: "Person inside corridor", sev: "HIGH" },
  { t: "00:11:05", id: "INC-1023", msg: "Vehicle near rail bed", sev: "MED" },
  { t: "00:09:47", id: "INC-1022", msg: "Debris on track edge", sev: "LOW" },
  { t: "00:04:18", id: "INC-1021", msg: "Person crossing, cleared", sev: "LOW" },
];

const sevStyle = {
  HIGH: "bg-tactical-alert/15 text-tactical-alert animate-pulse",
  MED: "bg-amber-100 text-amber-700",
  LOW: "bg-emerald-100 text-emerald-700",
};

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-tactical-canvas text-white font-sans antialiased overflow-x-hidden">
      {/* Floating pill nav */}
      <div className="fixed top-5 inset-x-0 z-30 px-4">
        <header className="max-w-3xl mx-auto flex items-center justify-between rounded-full border border-white/10 bg-white/5 backdrop-blur-xl pl-3 pr-2 py-2 shadow-lg">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-tactical-mint flex items-center justify-center font-bold text-tactical-canvas text-xs">
              RV
            </div>
            <span className="font-semibold tracking-tight">RailVigil</span>
          </Link>
          <nav className="hidden md:flex items-center gap-7 text-sm text-white/70">
            <a href="#console" className="hover:text-white transition-all duration-200">Live console</a>
            <a href="#pipeline" className="hover:text-white transition-all duration-200">Pipeline</a>
            <a href="#features" className="hover:text-white transition-all duration-200">Features</a>
          </nav>
          <div className="flex items-center gap-1">
            <Link to="/login" className="text-sm text-white/80 hover:text-white px-4 py-2 transition-all duration-200">
              Log in
            </Link>
            <Link
              to="/signup"
              className="bg-tactical-mint text-tactical-canvas text-sm font-semibold px-5 py-2 rounded-full hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
            >
              Sign up
            </Link>
          </div>
        </header>
      </div>

      {/* Hero */}
      <section className="relative pt-40 pb-20 px-6 text-center">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-[520px] bg-[radial-gradient(ellipse_at_top,rgba(52,211,153,0.18),transparent_65%)]" />
        <div className="relative max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 rounded-full border border-tactical-mint/30 bg-tactical-mint/10 text-tactical-mint text-xs font-mono px-4 py-2 mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-tactical-mint animate-pulse" />
            SYSTEM ONLINE · 30 FPS
          </div>
          <h1 className="text-5xl sm:text-7xl font-semibold tracking-tight leading-[1.02]">
            See the track.
            <br />
            <span className="text-tactical-mint">Stop the risk.</span>
          </h1>
          <p className="mt-7 text-lg text-white/60 leading-relaxed max-w-xl mx-auto">
            AI video analytics for railway right-of-way. RailVigil spots encroachment in the danger zone and
            confirms it before raising an alarm.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/upload"
              className="inline-flex items-center gap-2 bg-tactical-mint text-tactical-canvas font-semibold px-7 py-4 rounded-full shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
            >
              Launch video studio
              <ArrowIcon className="w-4 h-4" />
            </Link>
            <Link
              to="/dashboard"
              className="rounded-full border border-white/20 text-white font-medium px-7 py-4 hover:bg-white/5 transition-all duration-200"
            >
              View dashboard
            </Link>
          </div>
        </div>
      </section>

      {/* Live console: 60/40 */}
      <section id="console" className="max-w-6xl mx-auto px-6 pb-28">
        <div className="grid lg:grid-cols-5 gap-6">
          {/* Video 60% */}
          <div className="lg:col-span-3 rounded-3xl border border-white/10 bg-black/40 overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 text-xs font-mono text-white/50">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-white/15" />
                <span className="w-2.5 h-2.5 rounded-full bg-white/15" />
                <span className="w-2.5 h-2.5 rounded-full bg-white/15" />
              </div>
              <span>CAM-07 · KM 142.6</span>
              <span className="flex items-center gap-1.5 text-tactical-alert">
                <span className="w-1.5 h-1.5 rounded-full bg-tactical-alert animate-pulse" /> REC
              </span>
            </div>

            <div className="relative aspect-video">
              <svg viewBox="0 0 800 450" className="absolute inset-0 w-full h-full">
                <defs>
                  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0" stopColor="#022C22" />
                    <stop offset="1" stopColor="#04382b" />
                  </linearGradient>
                </defs>
                <rect width="800" height="450" fill="url(#sky)" />
                {/* Ballast bed */}
                <polygon points="200,450 355,140 445,140 600,450" fill="rgba(255,255,255,0.04)" />
                {/* Sleepers */}
                {[160, 185, 215, 250, 295, 350, 420].map((y) => {
                  const k = (y - 140) / 310;
                  const half = 45 + k * 155;
                  return (
                    <line key={y} x1={400 - half} x2={400 + half} y1={y} y2={y} stroke="rgba(255,255,255,0.14)" strokeWidth={1 + k * 3} />
                  );
                })}
                {/* Rails */}
                <line x1="300" y1="450" x2="385" y2="140" stroke="#34D399" strokeWidth="3" opacity="0.9" />
                <line x1="500" y1="450" x2="415" y2="140" stroke="#34D399" strokeWidth="3" opacity="0.9" />
                {/* Safety corridor */}
                <polygon
                  points="180,450 340,140 460,140 620,450"
                  fill="rgba(225,29,72,0.12)"
                  stroke="#E11D48"
                  strokeWidth="2"
                  strokeDasharray="8 6"
                />
                {/* Person */}
                <circle cx="480" cy="268" r="11" fill="#fff" opacity="0.85" />
                <rect x="467" y="282" width="26" height="70" rx="10" fill="#fff" opacity="0.85" />
                {/* Bounding box */}
                <rect x="450" y="248" width="60" height="118" fill="none" stroke="#E11D48" strokeWidth="2.5" />
                <rect x="450" y="222" width="236" height="24" rx="4" fill="#E11D48" />
                <text x="459" y="238" fill="#fff" fontSize="12" fontWeight="600" fontFamily="ui-monospace, monospace">
                  PERSON | 94.2% | BREACH DETECTED
                </text>
              </svg>

              {/* Timeline scrubber */}
              <div className="absolute bottom-4 inset-x-5 flex items-center gap-3 text-[10px] font-mono text-white/50">
                <span>00:14</span>
                <div className="relative flex-1 h-1 rounded-full bg-white/15">
                  <div className="absolute left-0 top-0 h-1 w-[46%] rounded-full bg-tactical-mint" />
                  <div className="absolute left-[46%] -top-1 w-3 h-3 rounded-full bg-white" />
                  <div className="absolute left-[30%] top-0 h-1 w-1.5 rounded-full bg-tactical-alert" />
                  <div className="absolute left-[46%] top-0 h-1 w-1.5 rounded-full bg-tactical-alert" />
                </div>
                <span>00:32</span>
              </div>
            </div>
          </div>

          {/* Log 40% */}
          <div className="lg:col-span-2 rounded-3xl bg-tactical-card text-tactical-dark p-6 shadow-lg border border-emerald-200/50 flex flex-col">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-semibold">Live incident log</h3>
              <span className="text-xs font-mono text-emerald-600">4 events</span>
            </div>
            <ul className="flex-1 space-y-3">
              {log.map((r) => (
                <li key={r.id} className="rounded-2xl bg-white border border-black/5 p-4 hover:-translate-y-0.5 transition-all duration-200">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-tactical-dark/50">{r.id} · {r.t}</span>
                    <span className={`text-[10px] font-mono font-semibold px-2.5 py-1 rounded-full ${sevStyle[r.sev]}`}>
                      {r.sev}
                    </span>
                  </div>
                  <div className="mt-1.5 text-sm font-medium">{r.msg}</div>
                </li>
              ))}
            </ul>
            <div className="mt-5 grid grid-cols-3 gap-3 text-center">
              {[["18", "Objects"], ["3", "Incidents"], ["1", "High risk"]].map(([v, l]) => (
                <div key={l} className="rounded-2xl bg-emerald-100/60 py-3">
                  <div className="text-xl font-semibold font-mono">{v}</div>
                  <div className="text-[11px] text-tactical-dark/60">{l}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Pipeline timeline */}
      <section id="pipeline" className="max-w-6xl mx-auto px-6 pb-28">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight">From frame to incident</h2>
          <p className="mt-3 text-white/60">Four stages, fully automatic.</p>
        </div>
        <div className="relative grid md:grid-cols-4 gap-10">
          <div className="hidden md:block absolute top-7 left-[12%] right-[12%] h-px bg-gradient-to-r from-transparent via-tactical-mint/50 to-transparent" />
          {steps.map(({ n, title, desc, Icon }) => (
            <div key={n} className="relative text-center">
              <div className="mx-auto w-14 h-14 rounded-full bg-tactical-canvas border border-tactical-mint/40 flex items-center justify-center text-tactical-mint shadow-[0_0_0_6px_rgba(52,211,153,0.08)]">
                <Icon className="w-6 h-6" />
              </div>
              <div className="mt-5 text-xs font-mono text-tactical-mint">{n}</div>
              <div className="mt-1 text-lg font-semibold">{title}</div>
              <p className="mt-2 text-sm text-white/60 leading-relaxed max-w-[220px] mx-auto">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Bento features */}
      <section id="features" className="max-w-6xl mx-auto px-6 pb-28">
        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-2 rounded-3xl bg-tactical-card text-tactical-dark p-8 shadow-lg border border-emerald-200/50 hover:-translate-y-1 transition-all duration-300">
            <div className="text-xs font-mono text-emerald-600 mb-3">SAFETY CORRIDORS</div>
            <h3 className="text-2xl font-semibold tracking-tight max-w-sm">Draw the danger zone once. Watch it forever.</h3>
            <p className="mt-3 text-tactical-dark/60 max-w-md">
              Define a polygon around the track and RailVigil checks every detection against it, frame by frame.
            </p>
            <svg viewBox="0 0 400 90" className="mt-6 w-full h-20">
              <polygon points="20,80 120,10 300,10 380,80" fill="rgba(225,29,72,0.10)" stroke="#E11D48" strokeWidth="2" strokeDasharray="6 5" />
              <line x1="70" y1="80" x2="150" y2="10" stroke="#059669" strokeWidth="2.5" />
              <line x1="330" y1="80" x2="270" y2="10" stroke="#059669" strokeWidth="2.5" />
            </svg>
          </div>

          <div className="rounded-3xl bg-tactical-dark text-white p-8 shadow-lg border border-white/10 hover:-translate-y-1 transition-all duration-300">
            <div className="text-xs font-mono text-tactical-mint mb-3">RISK SCORE</div>
            <h3 className="text-2xl font-semibold tracking-tight">Know what matters first.</h3>
            <p className="mt-3 text-white/60 text-sm">Every incident is scored so HIGH events rise to the top.</p>
            <div className="mt-6 inline-block text-xs font-mono font-semibold px-3 py-1.5 rounded-full bg-tactical-alert/20 text-tactical-alert animate-pulse">
              HIGH · 0.91
            </div>
          </div>

          <div className="rounded-3xl bg-tactical-card text-tactical-dark p-8 shadow-lg border border-emerald-200/50 hover:-translate-y-1 transition-all duration-300">
            <div className="text-xs font-mono text-emerald-600 mb-3">TEMPORAL CONFIRMATION</div>
            <h3 className="text-xl font-semibold tracking-tight">No more false alarms.</h3>
            <p className="mt-3 text-tactical-dark/60 text-sm">An object must stay in the zone before it counts as an incident.</p>
          </div>

          <div className="md:col-span-2 rounded-3xl bg-tactical-card text-tactical-dark p-8 shadow-lg border border-emerald-200/50 hover:-translate-y-1 transition-all duration-300">
            <div className="text-xs font-mono text-emerald-600 mb-3">EVIDENCE &amp; MAP</div>
            <h3 className="text-xl font-semibold tracking-tight">Every incident, with a snapshot and a location.</h3>
            <p className="mt-3 text-tactical-dark/60 max-w-md text-sm">
              Confirmed events are stored with evidence frames, timestamps and GPS coordinates for the incident map.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="rounded-3xl bg-tactical-mint text-tactical-canvas px-8 py-16 text-center shadow-lg">
          <h3 className="text-3xl sm:text-5xl font-semibold tracking-tight">Ready to watch the line?</h3>
          <p className="mt-4 text-tactical-canvas/70 max-w-md mx-auto">
            Upload a track video and see encroachments flagged in minutes.
          </p>
          <Link
            to="/upload"
            className="mt-8 inline-flex items-center gap-2 bg-tactical-dark text-white font-semibold px-8 py-4 rounded-full hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
          >
            Analyze a video
            <ArrowIcon className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <footer className="pb-10">
        <div className="max-w-6xl mx-auto px-6 text-xs text-white/40 font-mono">
          PRJ_35 · CSE7102 Mini Project · Presidency University
        </div>
      </footer>
    </div>
  );
}