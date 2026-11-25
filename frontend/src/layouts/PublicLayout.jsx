import { Outlet } from "react-router-dom";
import Footer from "../components/layout/Footer.jsx";
import TopBar from "../components/layout/TopBar.jsx";

// The landing page: the same green bar as the app, the page, and the full footer.
export default function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-canvas font-sans text-canvas-ink antialiased">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[1300] focus:rounded-sm focus:bg-ink focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-surface"
      >
        Skip to main content
      </a>
      <TopBar />
      <main id="main" className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-8 md:px-8">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
