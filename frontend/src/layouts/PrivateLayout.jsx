import { Outlet, useLocation } from "react-router-dom";
import Header from "../components/layout/Header.jsx";
import Footer from "../components/layout/Footer.jsx";

// Full-bleed pages (the GIS map) manage their own width and have no footer.
const FULL_BLEED = ["/map"];

export default function PrivateLayout() {
  const { pathname } = useLocation();
  const fullBleed = FULL_BLEED.includes(pathname);
  return (
    <div className="flex min-h-screen flex-col bg-canvas font-sans text-canvas-ink antialiased">
      <Header />
      <main id="main" className={fullBleed ? "flex-1" : "mx-auto w-full max-w-7xl flex-1 px-4 py-8 md:px-6"}>
        <Outlet />
      </main>
      {!fullBleed && <Footer />}
    </div>
  );
}
