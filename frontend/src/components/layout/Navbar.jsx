import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import axiosClient from "../../api/axiosClient.js";
import { navItems } from "./Sidebar.jsx";

const HEALTH_POLL_MS = 15000;

// Real backend status instead of a decorative label.
function useApiOnline() {
  const [online, setOnline] = useState(null);
  useEffect(() => {
    let cancelled = false;
    const check = () =>
      axiosClient
        .get("/health", { timeout: 4000 })
        .then(() => !cancelled && setOnline(true))
        .catch(() => !cancelled && setOnline(false));
    check();
    const t = setInterval(check, HEALTH_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);
  return online;
}

export default function Navbar() {
  const online = useApiOnline();
  return (
    <header className="sticky top-0 z-20 h-16 border-b border-white/10 bg-canvas/80 backdrop-blur-md">
      <div className="h-full px-6 flex items-center justify-between gap-4">
        {/* Logo on small screens (sidebar is hidden there) */}
        <Link to="/" className="flex items-center gap-2 lg:hidden">
          <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center font-bold text-white text-xs">
            RV
          </div>
          <span className="font-semibold tracking-tight">RailVigil</span>
        </Link>

        {/* Telemetry pill */}
        <div className="hidden lg:block w-24" />
        <div
          className={`inline-flex items-center gap-2 rounded-full border text-xs font-mono px-4 py-2 ${
            online === false
              ? "border-danger/40 bg-danger/10 text-rose-300"
              : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${online === false ? "bg-danger" : "bg-emerald-400 animate-pulse"}`} />
          {online === null ? "CONNECTING…" : online ? "BACKEND ONLINE" : "BACKEND OFFLINE"}
        </div>

        {/* Right side */}
        <div className="flex items-center gap-1 text-sm">
          {navItems
            .filter((n) => !n.soon)
            .map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `lg:hidden rounded-full px-3 py-2 transition-all duration-200 ${
                    isActive ? "bg-white/10 text-white" : "text-white/70"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          <Link
            to="/"
            className="rounded-full px-4 py-2 text-white/70 hover:text-white hover:bg-white/5 transition-all duration-200"
          >
            Home
          </Link>
        </div>
      </div>
    </header>
  );
}
