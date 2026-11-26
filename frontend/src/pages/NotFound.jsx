import { Link, useLocation } from "react-router-dom";
import { btn } from "../components/ui/index.jsx";

export default function NotFound() {
  const { pathname } = useLocation();
  return (
    <div className="border-2 border-rule bg-surface px-6 py-14 text-center text-ink">
      <h1 className="text-[32px] font-bold leading-none tracking-tight">No page at this address</h1>
      <p className="mx-auto mt-3 max-w-[52ch] break-words text-sm text-muted">
        Nothing is kept at <span className="font-semibold text-ink">{pathname}</span>. The link may be old, or the address may have been typed wrongly.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Link to="/dashboard" className={btn.primary}>
          Open the dashboard
        </Link>
        <Link to="/" className={btn.secondary}>
          Go to the home page
        </Link>
      </div>
    </div>
  );
}
