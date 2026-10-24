import { Link } from "react-router-dom";
import { Seal, menu } from "./Header.jsx";

export default function Footer() {
  return (
    <footer className="mt-16 border-t border-canvas-line bg-canvas-2 text-sm text-canvas-muted">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 md:grid-cols-[1.4fr_1fr_1fr] md:px-6">
        <div>
          <div className="flex items-center gap-3">
            <Seal size="h-9 w-9" />
            <span className="font-semibold text-canvas-ink">RailVigil</span>
          </div>
          <p className="mt-4 max-w-sm leading-relaxed">
            AI-assisted monitoring of railway right-of-way for physical encroachment and track-zone intrusion.
            Detections are candidates for officer review, not legal determinations.
          </p>
        </div>
        <div>
          <h2 className="mb-3 font-mono text-[11px] uppercase tracking-widest text-canvas-ink">Services</h2>
          <ul className="space-y-2">
            {menu
              .flatMap((g) => g.items)
              .filter(([to]) => to !== "/")
              .map(([to, label]) => (
                <li key={to}>
                  <Link to={to} className="hover:text-canvas-ink">
                    {label}
                  </Link>
                </li>
              ))}
          </ul>
        </div>
        <div>
          <h2 className="mb-3 font-mono text-[11px] uppercase tracking-widest text-canvas-ink">Data &amp; credits</h2>
          <ul className="space-y-2">
            <li>Detection: Ultralytics YOLOv8, YOLO-World</li>
            <li>Tracking: ByteTrack</li>
            <li>Map data © OpenStreetMap contributors</li>
            <li>Railway layer © OpenRailwayMap</li>
            <li>Basemap and imagery © Esri</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-canvas-line">
        <div className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-4 text-xs md:flex-row md:justify-between md:px-6">
          <span>© {new Date().getFullYear()} RailVigil project team · Prototype v2</span>
          <span>Academic project.</span>
        </div>
      </div>
    </footer>
  );
}
