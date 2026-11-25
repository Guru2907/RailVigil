import { Link } from "react-router-dom";
import { ImagePlus, Menu, Video } from "lucide-react";
import { useHealth } from "../../hooks/useHealth.js";
import { btn } from "../ui/index.jsx";

// Live backend status: a dot, a word and the round-trip time. Never colour alone.
export function SystemStatus() {
  const { online, ms } = useHealth();
  const down = online === false;
  const dot = down ? "bg-sev-critical" : online ? "bg-sev-low" : "bg-canvas-muted";
  return (
    <div className="flex items-center gap-2 text-xs text-canvas-muted" role="status" aria-live="polite">
      <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden />
      <span className={down ? "font-medium text-sev-critical" : ""}>
        {online === null ? "Connecting" : down ? "Backend offline" : "Online"}
      </span>
      {ms != null && <span className="tabular hidden sm:inline">{ms} ms</span>}
    </div>
  );
}

export default function TopBar({ onOpenMenu }) {
  return (
    <header className="sticky top-0 z-[1000] flex h-14 shrink-0 items-center gap-3 border-b border-canvas-line bg-canvas px-4 md:px-8">
      <button
        type="button"
        onClick={onOpenMenu}
        aria-label="Open navigation"
        className="press -ml-2 flex h-10 w-10 items-center justify-center rounded-lg text-canvas-muted hover:bg-canvas-line/60 hover:text-canvas-ink md:hidden"
      >
        <Menu className="h-5 w-5" aria-hidden />
      </button>
      <SystemStatus />
      <div className="ml-auto flex items-center gap-2">
        <Link to="/upload" className={`${btn.secondary} ${btn.small} !h-10 sm:!h-9`} aria-label="Analyse a video">
          <Video className="h-4 w-4" aria-hidden />
          <span className="hidden sm:inline">Analyse video</span>
        </Link>
        <Link to="/encroachment/upload" className={`${btn.primary} ${btn.small} !h-10 sm:!h-9`} aria-label="Analyse a photo">
          <ImagePlus className="h-4 w-4" aria-hidden />
          <span className="hidden sm:inline">Analyse photo</span>
        </Link>
      </div>
    </header>
  );
}
