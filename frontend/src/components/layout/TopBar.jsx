import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { ImagePlus, Menu, Video, X } from "lucide-react";
import { getStatsSummary } from "../../api/encroachment.js";
import { useHealth } from "../../hooks/useHealth.js";
import { menu } from "./nav.js";
import { Seal } from "./Seal.jsx";

const COUNT_REFRESH_MS = 60000;

// Live backend status: a dot, a word and the round-trip time. Never colour alone.
export function SystemStatus({ className = "" }) {
  const { online, ms } = useHealth();
  const down = online === false;
  return (
    <div className={`flex items-center gap-2 whitespace-nowrap text-[13px] ${className}`} role="status" aria-live="polite">
      <span className={`h-2 w-2 rounded-full ${down ? "border border-white" : online ? "bg-white" : "bg-white/50"}`} aria-hidden />
      <span className={down ? "font-semibold" : ""}>{online === null ? "Connecting" : down ? "Backend offline" : "Online"}</span>
      {ms != null && <span className="hidden 2xl:inline">{ms} ms</span>}
    </div>
  );
}

// How much each register holds, shown beside its link.
function useCounts() {
  const [counts, setCounts] = useState({});
  useEffect(() => {
    let cancelled = false;
    const load = () =>
      getStatsSummary()
        .then((s) => !cancelled && setCounts({ "/sites": s.encroachment.sites_open, "/reports": s.encroachment.reports_total, "/incidents": s.intrusion.incidents_total }))
        .catch(() => {});
    load();
    const timer = setInterval(load, COUNT_REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);
  return counts;
}

const action = "press inline-flex h-10 items-center gap-2 whitespace-nowrap rounded-sm border border-white/60 px-3.5 text-sm font-semibold text-white hover:bg-white/10 sm:h-9";

// The shell: one green bar. Each module is a labelled group of tabs, so
// Encroachment and Intrusion read as two equal halves; the current page is a
// tab cut out of the bar in paper, and each register shows how much it holds.
export default function TopBar() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const counts = useCounts();

  useEffect(() => {
    setOpen(false);
  }, [pathname]);
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header className="sticky top-0 z-[1000] border-b-[3px] border-pop bg-accent text-accent-ink print:hidden">
      <div className="flex h-[65px] items-stretch gap-1 px-4 md:px-8">
        <Link to="/" className="mr-4 flex items-center gap-2.5 self-center" aria-label="RailVigil home">
          <Seal size="h-9 w-9" onAccent />
          <span className="text-xl font-bold tracking-tight">RailVigil</span>
        </Link>

        <nav aria-label="Main" className="hidden items-stretch xl:flex">
          {menu.map(({ group, items }, gi) => (
            <div
              key={group || "main"}
              role="group"
              aria-label={group || "Overview"}
              className={`flex flex-col justify-end ${gi > 0 ? "ml-3 border-l border-white/25 pl-3" : ""}`}
            >
              <span className="px-3 pb-0.5 pt-2 text-[11px] font-semibold leading-none text-white/65">{group || "Overview"}</span>
              <div className="flex items-stretch">
                {items.map(({ to, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    className={({ isActive }) =>
                      `flex h-10 items-center gap-1.5 whitespace-nowrap rounded-t-sm px-3 text-[14.5px] -outline-offset-2 transition-colors focus-visible:outline-white ${
                        isActive ? "bg-canvas font-semibold text-canvas-ink" : "font-medium text-white/90 hover:bg-white/10 hover:text-white"
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {label}
                        {counts[to] != null && (
                          <span className={`tabular rounded-sm px-1.5 text-xs font-semibold leading-5 ${isActive ? "bg-ink text-surface" : "bg-pop text-ink"}`}>
                            {counts[to]}
                          </span>
                        )}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <SystemStatus className="mr-2 hidden text-white/90 sm:flex" />
          <Link to="/upload" className={action} aria-label="Analyse a video" title="Analyse a video">
            <Video className="h-4 w-4" aria-hidden />
            <span className="hidden min-[1400px]:inline">Analyse video</span>
          </Link>
          <Link to="/encroachment/upload" className={action} aria-label="Analyse a photo" title="Analyse a photo">
            <ImagePlus className="h-4 w-4" aria-hidden />
            <span className="hidden min-[1400px]:inline">Analyse photo</span>
          </Link>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? "Close navigation" : "Open navigation"}
            aria-expanded={open}
            className="press -mr-2 flex h-10 w-10 items-center justify-center rounded-sm hover:bg-white/10 xl:hidden"
          >
            {open ? <X className="h-5 w-5" aria-hidden /> : <Menu className="h-5 w-5" aria-hidden />}
          </button>
        </div>
      </div>

      {/* Small screens: the same navigation as a sheet under the bar */}
      {open && (
        <nav aria-label="Main" className="border-t border-white/20 bg-accent px-4 pb-4 xl:hidden">
          {menu.map(({ group, items }) => (
            <div key={group || "main"} className="pt-3">
              <h2 className="px-3 pb-1 text-xs font-semibold text-white/70">{group || "Overview"}</h2>
              {items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `flex h-11 items-center gap-3 rounded-sm px-3 text-[15px] ${
                      isActive ? "bg-canvas font-semibold text-canvas-ink" : "font-medium text-white/90 hover:bg-white/10"
                    }`
                  }
                >
                  <Icon className="h-[18px] w-[18px]" aria-hidden />
                  <span className="flex-1">{label}</span>
                  {counts[to] != null && <span className="tabular text-sm opacity-80">{counts[to]}</span>}
                </NavLink>
              ))}
            </div>
          ))}
          <SystemStatus className="px-3 pt-4 text-white/90" />
        </nav>
      )}
    </header>
  );
}
