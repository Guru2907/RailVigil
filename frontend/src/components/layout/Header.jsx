import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import axiosClient from "../../api/axiosClient.js";
import { THEMES, TEXT_SIZES, setTextSize, setThemeAttr, usePreference } from "../../utils/preferences.js";

const HEALTH_POLL_MS = 15000;

// Grouped like a government portal menu bar.
export const menu = [
  { group: null, items: [["/", "Home", true], ["/dashboard", "Dashboard"], ["/map", "GIS Map"]] },
  { group: "Encroachment", items: [["/encroachment/upload", "Photo Analysis"], ["/sites", "Sites"], ["/reports", "Reports"]] },
  { group: "Intrusion", items: [["/upload", "Video Analysis"], ["/incidents", "Incidents"]] },
];

function useIstClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return now.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false });
}

// Real backend health and round-trip time, not a decorative label.
function useTelemetry() {
  const [state, setState] = useState({ online: null, ms: null });
  useEffect(() => {
    let cancelled = false;
    const check = () => {
      const t0 = performance.now();
      axiosClient
        .get("/health", { timeout: 4000 })
        .then(() => !cancelled && setState({ online: true, ms: Math.round(performance.now() - t0) }))
        .catch(() => !cancelled && setState({ online: false, ms: null }));
    };
    check();
    const t = setInterval(check, HEALTH_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);
  return state;
}

function UtilityBar() {
  const clock = useIstClock();
  const [theme, setTheme] = usePreference("rv-theme", "tactical", setThemeAttr);
  const [size, setSize] = usePreference("rv-text", "md", setTextSize);
  const pill = "rounded px-1.5 py-0.5 transition";
  return (
    <div className="border-b border-canvas-line bg-canvas-2 text-[11px] text-canvas-muted">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2 focus:text-ink"
      >
        Skip to main content
      </a>
      <div className="mx-auto flex h-9 max-w-7xl items-center justify-between gap-4 px-4 md:px-6">
        <span className="hidden truncate sm:block">
          Railway Right-of-Way Monitoring System · <span className="text-canvas-ink/80">Academic prototype</span>
        </span>
        <div className="ml-auto flex items-center gap-4">
          <div className="flex items-center gap-1" role="group" aria-label="Text size">
            {TEXT_SIZES.map(([key, label]) => (
              <button
                key={key}
                onClick={() => setSize(key)}
                aria-pressed={size === key}
                className={`${pill} ${size === key ? "bg-canvas-line text-canvas-ink" : "hover:text-canvas-ink"}`}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="h-3 w-px bg-canvas-line" aria-hidden />
          <div className="flex items-center gap-1" role="group" aria-label="Colour theme">
            {THEMES.map(([key, label]) => (
              <button
                key={key}
                onClick={() => setTheme(key)}
                aria-pressed={theme === key}
                className={`${pill} ${theme === key ? "bg-canvas-line text-canvas-ink" : "hover:text-canvas-ink"}`}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="h-3 w-px bg-canvas-line" aria-hidden />
          <span className="tabular font-mono text-canvas-ink/80">{clock} IST</span>
        </div>
      </div>
    </div>
  );
}

function Telemetry() {
  const { online, ms } = useTelemetry();
  const down = online === false;
  return (
    <div
      className={`hidden items-center gap-2.5 rounded-full border px-4 py-1.5 font-mono text-[11px] tracking-wider md:inline-flex ${
        down ? "border-danger/50 bg-danger/10 text-rose-300" : "border-signal/40 bg-signal/10 text-signal"
      }`}
      aria-live="polite"
    >
      <span className={`h-1.5 w-1.5 rounded-full ${down ? "bg-danger" : "animate-pulse bg-signal"}`} />
      {online === null ? "CONNECTING" : down ? "BACKEND OFFLINE" : "SYSTEM ONLINE"}
      {ms != null && (
        <>
          <span className="opacity-40">●</span>
          <span className="tabular">API {ms} ms</span>
        </>
      )}
    </div>
  );
}

export function Seal({ size = "h-11 w-11" }) {
  return (
    <div className={`relative flex ${size} shrink-0 items-center justify-center rounded-md border-2 border-signal/70 bg-canvas-2`}>
      <svg viewBox="0 0 32 32" className="h-6 w-6 text-signal" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d="M11 3 7 29M21 3l4 26" />
        <path d="M9.5 10h13M8.5 17h15M7.5 24h17" strokeWidth="1.6" />
      </svg>
    </div>
  );
}

function Masthead() {
  return (
    <div className="border-b border-canvas-line bg-canvas">
      <div className="mx-auto flex h-[4.5rem] max-w-7xl items-center justify-between gap-4 px-4 md:px-6">
        <Link to="/" className="flex min-w-0 items-center gap-3">
          <Seal />
          <div className="min-w-0 leading-tight">
            <div className="text-lg font-semibold tracking-tight text-canvas-ink">RailVigil</div>
            <div className="truncate text-xs text-canvas-muted">Encroachment &amp; Intrusion Command Centre</div>
          </div>
        </Link>
        <Telemetry />
        <Link
          to="/encroachment/upload"
          className="inline-flex items-center gap-2 rounded-md border border-signal/60 px-3.5 py-2 text-sm font-semibold text-signal transition-all duration-200 hover:scale-[1.02] hover:bg-signal/10 active:scale-[0.98]"
        >
          New analysis
        </Link>
      </div>
    </div>
  );
}

function MenuBar() {
  return (
    <nav aria-label="Main" className="sticky top-0 z-[1000] border-b border-canvas-line bg-canvas-2/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-stretch gap-1 overflow-x-auto px-4 md:px-6">
        {menu.map(({ group, items }, gi) => (
          <div key={gi} className="flex items-stretch">
            {gi > 0 && <span className="mx-2 my-3 w-px bg-canvas-line" aria-hidden />}
            {group && (
              <span className="flex items-center pr-2 font-mono text-[10px] uppercase tracking-widest text-canvas-muted/70">
                {group}
              </span>
            )}
            {items.map(([to, label, end]) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `flex items-center whitespace-nowrap border-b-2 px-3 py-3 text-sm font-medium transition-colors ${
                    isActive
                      ? "border-signal text-canvas-ink"
                      : "border-transparent text-canvas-muted hover:border-canvas-line hover:text-canvas-ink"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
        ))}
      </div>
    </nav>
  );
}

export default function Header() {
  return (
    <>
      <header>
        <UtilityBar />
        <Masthead />
      </header>
      <MenuBar />
    </>
  );
}
