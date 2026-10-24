import { Link } from "react-router-dom";
import { Seal } from "../components/layout/Header.jsx";
import { btn } from "../components/ui/index.jsx";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-5 bg-canvas p-6 text-center text-canvas-ink">
      <Seal />
      <div className="font-mono text-6xl font-bold text-signal">404</div>
      <h1 className="text-xl font-semibold">This track doesn&apos;t lead anywhere</h1>
      <p className="max-w-sm text-sm text-canvas-muted">The page you asked for doesn&apos;t exist or has moved.</p>
      <div className="flex gap-3">
        <Link to="/" className={btn.outline}>
          Home
        </Link>
        <Link to="/dashboard" className={`${btn.primary} ring-1 ring-canvas-line`}>
          Command dashboard
        </Link>
      </div>
    </div>
  );
}
