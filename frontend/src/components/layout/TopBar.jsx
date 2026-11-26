import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { ImagePlus, Menu, Video, X } from "lucide-react";
import { getStatsSummary } from "../../api/encroachment.js";
import { useHealth } from "../../hooks/useHealth.js";
import { menu } from "./nav.js";
import { Seal } from "./Seal.jsx";

const COUNT_REFRESH_MS = 60000;

// Backend status, shown only while the backend cannot be reached.
export function SystemStatus({ className = "" }) {
  const { online } = useHealth();
  // Said only when something is wrong: a working backend needs no label.
  if (online !== false) return null;
  return (
    <div className={`flex items-center gap-2 whitespace-nowrap text-[13px] font-semibold text-sev-critical ${className}`} role="status" aria-live="polite">
      <span className="h-2 w-2 rounded-full bg-sev-critical" aria-hidden />
      Backend offline
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

const actionBase = "press inline-flex h-10 items-center gap-2 whitespace-nowrap rounded-full px-4 text-sm font-semibold sm:h-9";
const action = `${actionBase} border border-ink/30 text-ink hover:bg-canvas-2`;
const actionMain = `${actionBase} bg-ink text-surface hover:bg-accent-hover`;

// The shell: a light bar that floats above the page. Each module is a labelled
// group of links, so Encroachment and Intrusion read as two equal halves; the
// current page is an ink pill, and each register shows how much it holds.
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
    <header className="sticky top-0 z-[1000] px-3 pt-3 md:px-8 print:hidden">
      <div className="mx-auto max-w-[1376px] rounded-2xl border border-line bg-surface/95 text-ink shadow-[0_6px_24px_-12px_rgb(17_17_17/0.35)] backdrop-blur">
      <div className="flex h-16 items-stretch gap-1 px-4 md:px-5">
        <Link to="/" className="mr-4 flex items-center gap-2.5 self-center" aria-label="RailVigil home">
          <Seal size="h-9 w-9" />
          <span className="text-xl font-bold tracking-tight">RailVigil</span>
        </Link>

        <nav aria-label="Main" className="hidden items-stretch xl:flex">
          {menu.map(({ group, items }, gi) => (
            <div
              key={group || "main"}
              role="group"
              aria-label={group || "Overview"}
              className={`flex flex-col justify-center ${gi > 0 ? "ml-3 border-l border-line pl-3" : ""}`}
            >
              <span className="px-3 pb-1 text-[11px] font-semibold leading-none text-muted">{group || "Overview"}</span>
              <div className="flex items-stretch">
                {items.map(({ to, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    className={({ isActive }) =>
                      `flex h-8 items-center gap-1.5 whitespace-nowrap rounded-full px-3 text-[14.5px] transition-colors ${
                        isActive ? "bg-ink font-semibold text-surface" : "font-medium text-ink hover:bg-canvas-2"
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {label}
                        {counts[to] != null && (
                          <span className={`tabular rounded-sm px-1.5 text-xs font-semibold leading-5 ${isActive ? "bg-pop text-ink" : "bg-canvas-2 text-ink"}`}>
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
          <SystemStatus className="mr-2 hidden sm:flex" />
          <Link to="/upload" className={action} aria-label="Analyse a video" title="Analyse a video">
            <Video className="h-4 w-4" aria-hidden />
            <span className="hidden min-[1400px]:inline">Analyse video</span>
          </Link>
          <Link to="/encroachment/upload" className={actionMain} aria-label="Analyse a photo" title="Analyse a photo">
            <ImagePlus className="h-4 w-4" aria-hidden />
            <span className="hidden min-[1400px]:inline">Analyse photo</span>
          </Link>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? "Close navigation" : "Open navigation"}
            aria-expanded={open}
            className="press -mr-1 flex h-10 w-10 items-center justify-center rounded-full hover:bg-canvas-2 xl:hidden"
          >
            {open ? <X className="h-5 w-5" aria-hidden /> : <Menu className="h-5 w-5" aria-hidden />}
          </button>
        </div>
      </div>

      {/* Small screens: the same navigation as a sheet under the bar */}
      {open && (
        <nav aria-label="Main" className="max-h-[calc(100vh-110px)] overflow-y-auto border-t border-line px-3 pb-4 xl:hidden">
          {menu.map(({ group, items }) => (
            <div key={group || "main"} className="pt-3">
              <h2 className="px-3 pb-1 text-xs font-semibold text-muted">{group || "Overview"}</h2>
              {items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `flex h-11 items-center gap-3 rounded-full px-3 text-[15px] ${
                      isActive ? "bg-ink font-semibold text-surface" : "font-medium text-ink hover:bg-canvas-2"
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
          <SystemStatus className="px-3 pt-4" />
        </nav>
      )}
      </div>
    </header>
  );
}
