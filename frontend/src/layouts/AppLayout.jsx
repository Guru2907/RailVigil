import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import TopBar from "../components/layout/TopBar.jsx";

// Full-bleed pages (the GIS map) fill the area under the bar themselves.
const FULL_BLEED = ["/map"];

const skip =
  "sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[1300] focus:rounded-sm focus:bg-ink focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-surface";

// The working app: the green bar on top, the page on paper beneath it.
export default function AppLayout() {
  const { pathname } = useLocation();
  const fullBleed = FULL_BLEED.includes(pathname);
  // A new page starts at its top, not where the last one was scrolled to.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return (
    <div className="flex min-h-screen flex-col bg-canvas font-sans text-canvas-ink antialiased">
      <a href="#main" className={skip}>
        Skip to main content
      </a>
      <TopBar />
      <main id="main" className={fullBleed ? "min-h-0 flex-1" : "mx-auto w-full max-w-[1440px] flex-1 px-4 py-6 md:px-8"}>
        <Outlet />
      </main>
      {!fullBleed && (
        <footer className="mx-auto w-full max-w-[1440px] px-4 pb-6 text-xs text-canvas-muted print:hidden md:px-8">
          <div className="border-t border-canvas-line pt-3">
            RailVigil is an academic prototype. Detections are candidates for officer review, not determinations.
          </div>
        </footer>
      )}
    </div>
  );
}
