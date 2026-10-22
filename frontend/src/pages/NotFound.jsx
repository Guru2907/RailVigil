import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-tactical-canvas p-6 text-center text-white">
      <div className="font-mono text-7xl font-bold text-tactical-mint">404</div>
      <h1 className="text-xl font-semibold">This track doesn't lead anywhere</h1>
      <p className="max-w-sm text-sm text-white/60">The page you asked for doesn't exist or was moved.</p>
      <div className="flex gap-3">
        <Link to="/" className="rounded-full border border-white/20 px-5 py-2 text-sm hover:bg-white/10">
          Home
        </Link>
        <Link to="/dashboard" className="rounded-full bg-tactical-mint px-5 py-2 text-sm font-semibold text-tactical-dark">
          Dashboard
        </Link>
      </div>
    </div>
  );
}
