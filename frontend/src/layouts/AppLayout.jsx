import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "../components/layout/Sidebar.jsx";
import TopBar from "../components/layout/TopBar.jsx";

// Full-bleed pages (the GIS map) fill the area beside the sidebar themselves.
const FULL_BLEED = ["/map"];
const STORAGE_KEY = "rv-sidebar";

function readCollapsed() {
  try {
    return localStorage.getItem(STORAGE_KEY) === "collapsed";
  } catch {
    return false;
  }
}

// The working app: sidebar on the left, a slim top bar, the page beside it.
export default function AppLayout() {
  const { pathname } = useLocation();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [menuOpen, setMenuOpen] = useState(false);
  const fullBleed = FULL_BLEED.includes(pathname);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? "collapsed" : "open");
    } catch {
      /* storage unavailable: the choice just does not persist */
    }
  }, [collapsed]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKey = (e) => e.key === "Escape" && setMenuOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  return (
    <div className="min-h-screen bg-canvas font-sans text-canvas-ink antialiased">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[1300] focus:rounded-lg focus:bg-accent focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-accent-ink"
      >
        Skip to main content
      </a>

      {/* Desktop sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-[1100] hidden border-r border-canvas-line md:block ${collapsed ? "w-16" : "w-60"}`}
      >
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      </aside>

      {/* Small screens: the same navigation as an overlay */}
      {menuOpen && (
        <div className="fixed inset-0 z-[1200] md:hidden">
          <div className="absolute inset-0 bg-canvas-2/70" onClick={() => setMenuOpen(false)} aria-hidden />
          <aside className="absolute inset-y-0 left-0 w-64 border-r border-canvas-line" role="dialog" aria-modal="true" aria-label="Navigation">
            <Sidebar onNavigate={() => setMenuOpen(false)} />
          </aside>
        </div>
      )}

      <div className={`flex min-h-screen flex-col ${collapsed ? "md:pl-16" : "md:pl-60"}`}>
        <TopBar onOpenMenu={() => setMenuOpen(true)} />
        <main id="main" className={fullBleed ? "min-h-0 flex-1" : "mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 md:px-8 md:py-8"}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
