import { useEffect, useState } from "react";
import { Link, Outlet } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import Footer from "../components/layout/Footer.jsx";
import { Seal } from "../components/layout/Seal.jsx";
import { btn } from "../components/ui/index.jsx";

const links = [
  ["/dashboard", "Dashboard"],
  ["/map", "GIS Map"],
  ["/sites", "Sites"],
  ["/incidents", "Incidents"],
];

// The landing page: a simple top navigation that gains a solid background once
// the page scrolls, the page itself, and the footer.
export default function PublicLayout() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-canvas font-sans text-canvas-ink antialiased">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[1300] focus:rounded-lg focus:bg-accent focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-accent-ink"
      >
        Skip to main content
      </a>
      <header
        className={`sticky top-0 z-[1000] border-b transition-colors duration-200 ${
          scrolled ? "border-canvas-line bg-canvas/85 backdrop-blur-md" : "border-transparent bg-canvas"
        }`}
      >
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-8 px-4 md:px-6">
          <Link to="/" className="flex items-center gap-2.5" aria-label="RailVigil home">
            <Seal size="h-8 w-8" />
            <span className="text-[15px] font-semibold tracking-tight">RailVigil</span>
          </Link>
          <nav aria-label="Sections" className="hidden items-center gap-6 text-sm text-canvas-muted md:flex">
            {links.map(([to, label]) => (
              <Link key={to} to={to} className="transition-colors hover:text-canvas-ink">
                {label}
              </Link>
            ))}
          </nav>
          <Link to="/dashboard" className={`${btn.primary} ${btn.small} ml-auto !h-9`}>
            Open dashboard
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 md:px-6">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
