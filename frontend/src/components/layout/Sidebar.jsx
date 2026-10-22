import { useState } from "react";
import { Link, NavLink } from "react-router-dom";

const iconProps = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8 };

function VideoIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <path d="M23 7l-7 5 7 5V7z" />
      <rect x="1" y="5" width="15" height="14" rx="2" />
    </svg>
  );
}
function AlertIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M12 8v5" />
    </svg>
  );
}
function GridIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  );
}
function MapIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2z" />
      <path d="M9 4v14M15 6v14" />
    </svg>
  );
}
function CameraIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
      <circle cx="12" cy="13" r="3.5" />
    </svg>
  );
}
function PinIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <path d="M12 22s7-7 7-12a7 7 0 10-14 0c0 5 7 12 7 12z" />
      <circle cx="12" cy="10" r="2.5" />
    </svg>
  );
}
function DocIcon(props) {
  return (
    <svg {...iconProps} {...props}>
      <path d="M6 2h9l5 5v15H6z" />
      <path d="M14 2v6h6M9 13h8M9 17h8" />
    </svg>
  );
}
function ChevronIcon(props) {
  return (
    <svg {...iconProps} strokeWidth="2" {...props}>
      <path d="M15 6l-6 6 6 6" />
    </svg>
  );
}

// soon: true = page not built yet, shown as a muted non-link item
// section: starts a labelled group in the sidebar
export const navItems = [
  { to: "/dashboard", label: "Dashboard", Icon: GridIcon, section: "Overview" },
  { to: "/map", label: "GIS Map", Icon: MapIcon },
  { to: "/encroachment/upload", label: "Photo Analysis", Icon: CameraIcon, section: "Encroachment" },
  { to: "/sites", label: "Sites", Icon: PinIcon },
  { to: "/reports", label: "Reports", Icon: DocIcon },
  { to: "/upload", label: "Video Analysis", Icon: VideoIcon, section: "Intrusion" },
  { to: "/incidents", label: "Incidents", Icon: AlertIcon },
];

const STORAGE_KEY = "rv-sidebar-collapsed";

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === "1";
    } catch {
      return false;
    }
  });

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    try {
      localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
    } catch {
      /* ignore */
    }
  }

  const itemBase = "flex items-center gap-3 rounded-full py-3 text-sm whitespace-nowrap overflow-hidden";
  const itemPad = collapsed ? "justify-center px-0" : "px-4";

  return (
    <aside
      className={`hidden lg:block shrink-0 sticky top-0 h-screen p-4 transition-all duration-300 ${
        collapsed ? "w-24" : "w-72"
      }`}
    >
      <div className="h-full flex flex-col rounded-3xl bg-tactical-card text-tactical-dark shadow-lg border border-emerald-200/50 p-3">
        {/* Logo */}
        <Link
          to="/"
          className={`flex items-center gap-3 mb-4 mt-2 ${collapsed ? "justify-center" : "px-2"}`}
        >
          <div className="w-9 h-9 shrink-0 rounded-full bg-tactical-dark flex items-center justify-center font-bold text-tactical-mint text-sm">
            RV
          </div>
          {!collapsed && <span className="text-lg font-semibold tracking-tight">RailVigil</span>}
        </Link>

        {/* Nav */}
        <nav className="space-y-1">
          {navItems.map(({ to, label, Icon, soon, section }) => [
            section && !collapsed && (
              <div key={`s-${section}`} className="px-4 pt-3 pb-1 text-[10px] font-mono uppercase tracking-widest text-tactical-dark/40">
                {section}
              </div>
            ),
            soon ? (
              <div
                key={to}
                title={collapsed ? `${label} (soon)` : undefined}
                className={`${itemBase} ${itemPad} text-tactical-dark/30 cursor-not-allowed`}
              >
                <Icon className="w-5 h-5 shrink-0" />
                {!collapsed && (
                  <>
                    <span>{label}</span>
                    <span className="ml-auto text-[10px] font-mono border border-tactical-dark/15 rounded-full px-2 py-0.5">
                      SOON
                    </span>
                  </>
                )}
              </div>
            ) : (
              <NavLink
                key={to}
                to={to}
                title={collapsed ? label : undefined}
                className={({ isActive }) =>
                  `${itemBase} ${itemPad} font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-tactical-dark text-white"
                      : "text-tactical-dark/70 hover:bg-tactical-dark/5 hover:text-tactical-dark"
                  }`
                }
              >
                <Icon className="w-5 h-5 shrink-0" />
                {!collapsed && label}
              </NavLink>
            ),
          ])}
        </nav>

        {/* Collapse toggle */}
        <button
          onClick={toggle}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={`mt-auto ${itemBase} ${itemPad} text-tactical-dark/60 hover:bg-tactical-dark/5 hover:text-tactical-dark transition-all duration-200`}
        >
          <ChevronIcon
            className={`w-5 h-5 shrink-0 transition-transform duration-300 ${collapsed ? "rotate-180" : ""}`}
          />
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  );
}