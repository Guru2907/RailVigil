import { Link, NavLink } from "react-router-dom";
import { navItems } from "./Sidebar.jsx";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-20 h-16 border-b border-white/10 bg-tactical-canvas/80 backdrop-blur-md">
      <div className="h-full px-6 flex items-center justify-between gap-4">
        {/* Logo on small screens (sidebar is hidden there) */}
        <Link to="/" className="flex items-center gap-2 lg:hidden">
          <div className="w-8 h-8 rounded-full bg-tactical-mint flex items-center justify-center font-bold text-tactical-canvas text-xs">
            RV
          </div>
          <span className="font-semibold tracking-tight">RailVigil</span>
        </Link>

        {/* Telemetry pill */}
        <div className="hidden lg:block w-24" />
        <div className="inline-flex items-center gap-2 rounded-full border border-tactical-mint/30 bg-tactical-mint/10 text-tactical-mint text-xs font-mono px-4 py-2">
          <span className="w-1.5 h-1.5 rounded-full bg-tactical-mint animate-pulse" />
          SYSTEM ONLINE · 30 FPS
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
