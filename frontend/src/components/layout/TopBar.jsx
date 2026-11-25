import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { ImagePlus, Menu, Video, X } from "lucide-react";
import { useHealth } from "../../hooks/useHealth.js";
import { menu } from "./nav.js";
import { Seal } from "./Seal.jsx";

// Live backend status: a dot, a word and the round-trip time. Never colour alone.
export function SystemStatus({ className = "" }) {
  const { online, ms } = useHealth();
  const down = online === false;
  return (
    <div className={`flex items-center gap-2 whitespace-nowrap text-[13px] ${className}`} role="status" aria-live="polite">
      <span className={`h-2 w-2 rounded-full ${down ? "bg-wash" : online ? "bg-white" : "bg-white/50"}`} aria-hidden />
      <span className={down ? "font-semibold" : ""}>{online === null ? "Connecting" : down ? "Backend offline" : "Online"}</span>
      {ms != null && <span className="hidden xl:inline">{ms} ms</span>}
    </div>
  );
}

const action = "press inline-flex h-10 items-center gap-2 whitespace-nowrap rounded-sm px-3.5 text-sm font-semibold sm:h-9";

// The shell: one green bar. The two modules sit side by side as equal groups;
// the current page is a tab cut out of the bar in paper.
export default function TopBar() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header className="sticky top-0 z-[1000] bg-accent text-accent-ink">
      <div className="flex h-[60px] items-stretch gap-2 px-4 md:px-8">
        <Link to="/" className="mr-3 flex items-center gap-2.5" aria-label="RailVigil home">
          <Seal size="h-8 w-8" onAccent />
          <span className="text-lg font-bold tracking-tight">RailVigil</span>
        </Link>

        <nav aria-label="Main" className="hidden items-stretch lg:flex">
          {menu.map(({ group, items }, gi) => (
            <div key={group || "main"} className="flex items-stretch" role="group" aria-label={group || "Overview"}>
              {gi > 0 && <span className="mx-2 my-auto h-6 w-px bg-white/30" aria-hidden />}
              {items.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `flex items-center whitespace-nowrap px-3.5 text-[14.5px] transition-colors ${
                      isActive ? "bg-canvas font-semibold text-canvas-ink" : "font-medium text-white/85 hover:bg-white/10 hover:text-white"
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <SystemStatus className="mr-2 hidden text-white/90 sm:flex" />
          <Link to="/upload" className={`${action} border border-white/60 text-white hover:bg-white/10`} aria-label="Analyse a video">
            <Video className="h-4 w-4" aria-hidden />
            <span className="hidden md:inline">Analyse video</span>
          </Link>
          <Link to="/encroachment/upload" className={`${action} border border-white/60 text-white hover:bg-white/10`} aria-label="Analyse a photo">
            <ImagePlus className="h-4 w-4" aria-hidden />
            <span className="hidden md:inline">Analyse photo</span>
          </Link>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? "Close navigation" : "Open navigation"}
            aria-expanded={open}
            className="press -mr-2 flex h-10 w-10 items-center justify-center rounded-sm hover:bg-white/10 lg:hidden"
          >
            {open ? <X className="h-5 w-5" aria-hidden /> : <Menu className="h-5 w-5" aria-hidden />}
          </button>
        </div>
      </div>

      {/* Small screens: the same navigation as a sheet under the bar */}
      {open && (
        <nav aria-label="Main" className="border-t border-white/20 bg-accent px-4 pb-4 lg:hidden">
          {menu.map(({ group, items }) => (
            <div key={group || "main"} className="pt-3">
              {group && <h2 className="px-3 pb-1 text-xs font-semibold text-white/70">{group}</h2>}
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
                  {label}
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
