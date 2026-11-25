import { Link, NavLink } from "react-router-dom";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { menu } from "./nav.js";
import { Seal } from "./Seal.jsx";

// Left navigation. `collapsed` shows icons only (desktop); on small screens the
// same component is shown full-width inside an overlay by AppLayout.
export default function Sidebar({ collapsed = false, onToggle, onNavigate }) {
  return (
    <nav aria-label="Main" className="flex h-full flex-col bg-canvas-2 text-sm">
      <Link
        to="/"
        onClick={onNavigate}
        className={`flex h-14 shrink-0 items-center gap-2.5 border-b border-canvas-line ${collapsed ? "justify-center px-0" : "px-4"}`}
        aria-label="RailVigil home"
      >
        <Seal size="h-8 w-8" />
        {!collapsed && <span className="text-[15px] font-semibold tracking-tight text-canvas-ink">RailVigil</span>}
      </Link>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3">
        {menu.map(({ group, items }, gi) => (
          <div key={group || "main"} className={gi > 0 ? "mt-5" : ""}>
            {group &&
              (collapsed ? (
                <div className="mx-3 mb-2 border-t border-canvas-line" aria-hidden />
              ) : (
                <h2 className="mb-1 px-3 text-xs font-medium text-canvas-muted">{group}</h2>
              ))}
            <ul className="space-y-0.5">
              {items.map(({ to, label, icon: Icon }) => (
                <li key={to}>
                  <NavLink
                    to={to}
                    onClick={onNavigate}
                    title={collapsed ? label : undefined}
                    aria-label={collapsed ? label : undefined}
                    className={({ isActive }) =>
                      `press group flex h-10 items-center gap-3 rounded-lg ${collapsed ? "justify-center px-0" : "px-3"} font-medium ${
                        isActive ? "bg-accent/12 text-canvas-ink" : "text-canvas-muted hover:bg-canvas-line/60 hover:text-canvas-ink"
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <Icon className={`h-[18px] w-[18px] shrink-0 ${isActive ? "text-accent" : ""}`} aria-hidden />
                        {!collapsed && <span className="truncate">{label}</span>}
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="shrink-0 border-t border-canvas-line p-2">
        {!collapsed && (
          <p className="px-3 pb-2 pt-1 text-xs leading-relaxed text-canvas-muted">
            Academic prototype. Detections are candidates for officer review.
          </p>
        )}
        {onToggle && (
          <button
            type="button"
            onClick={onToggle}
            aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
            aria-expanded={!collapsed}
            className={`press hidden h-10 w-full items-center gap-3 rounded-lg text-canvas-muted hover:bg-canvas-line/60 hover:text-canvas-ink md:flex ${
              collapsed ? "justify-center" : "px-3"
            }`}
          >
            {collapsed ? <PanelLeftOpen className="h-[18px] w-[18px]" aria-hidden /> : <PanelLeftClose className="h-[18px] w-[18px]" aria-hidden />}
            {!collapsed && <span className="text-sm font-medium">Collapse</span>}
          </button>
        )}
      </div>
    </nav>
  );
}
