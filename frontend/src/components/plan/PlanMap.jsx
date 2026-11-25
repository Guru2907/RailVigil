import { useEffect, useMemo, useState } from "react";
import { Maximize2, Navigation } from "lucide-react";
import "leaflet/dist/leaflet.css";
import { AttributionControl, Circle, CircleMarker, MapContainer, Marker, Polyline, ScaleControl, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "../../utils/leafletGlobal.js";
import { PLAN_BASE, RAILWAYS } from "../../utils/mapTiles.js";
import { SEVERITIES, SEVERITY_COLOR, SEVERITY_LABEL, normaliseSeverity } from "../../utils/severity.js";

// The plan: a real map drawn as a survey sheet. Each mark carries the number of
// its row in the register, so a row and its mark are the same thing.
//   marks:   [{ id, number, lat, lon, severity, label }]  the listed sites
//   others:  [{ id, lat, lon }]   sites in the register that are not on this sheet
//   focusId: the site the reader chose (the plan moves in on it); null shows the whole listed set

const INK = "#22241F";
const SITE_ZOOM = 16;
const SITE_RADIUS_M = 25; // findings of one kind within 25 m form a site
const FAN_PX = 34; // how far a fanned mark sits from its true position
const NEAR_PX = 22; // marks closer than this on screen would hide each other

function markIcon(number, severity, selected) {
  const colour = SEVERITY_COLOR[normaliseSeverity(severity)];
  return L.divIcon({
    className: "",
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    html: `<span class="rv-mark${selected ? " rv-mark-selected" : ""}" style="--c:${colour}">${number}</span>`,
  });
}

// Marks that would sit on top of each other are fanned out on a ring around
// their true position and tied to it by a leader, so every number can be read.
function layOut(map, marks) {
  const points = marks.map((m) => ({ ...m, pt: map.latLngToLayerPoint([m.lat, m.lon]) }));
  const groups = [];
  points.forEach((p) => {
    const group = groups.find((g) => g[0].pt.distanceTo(p.pt) < NEAR_PX);
    if (group) group.push(p);
    else groups.push([p]);
  });
  return groups.flatMap((group) => {
    if (group.length === 1) return [{ ...group[0], at: [group[0].lat, group[0].lon], fanned: false }];
    const centre = group.reduce((acc, p) => acc.add(p.pt), L.point(0, 0)).divideBy(group.length);
    const radius = Math.max(FAN_PX, (group.length * 36) / (2 * Math.PI));
    return group.map((p, i) => {
      const angle = (2 * Math.PI * i) / group.length - Math.PI / 2;
      const spot = map.layerPointToLatLng(centre.add(L.point(radius * Math.cos(angle), radius * Math.sin(angle))));
      return { ...p, at: [spot.lat, spot.lng], fanned: true };
    });
  });
}

function Marks({ marks, selectedId, onSelect, onShared }) {
  const map = useMap();
  const [tick, setTick] = useState(0);
  useMapEvents({ zoomend: () => setTick((t) => t + 1) });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const placed = useMemo(() => layOut(map, marks), [map, marks, tick]);
  const shared = placed.filter((p) => p.fanned).length;
  useEffect(() => onShared(shared), [shared, onShared]);

  return placed.map((m) => (
    <span key={m.id}>
      {m.fanned && (
        <>
          <Polyline positions={[[m.lat, m.lon], m.at]} pathOptions={{ color: INK, weight: 1, interactive: false }} />
          <CircleMarker center={[m.lat, m.lon]} radius={3} pathOptions={{ color: INK, fillColor: INK, fillOpacity: 1, weight: 1, interactive: false }} />
        </>
      )}
      <Marker
        position={m.at}
        icon={markIcon(m.number, m.severity, m.id === selectedId)}
        zIndexOffset={m.id === selectedId ? 1000 : 0}
        title={m.label}
        alt={m.label}
        keyboard
        eventHandlers={{ click: () => onSelect(m.id) }}
      />
    </span>
  ));
}

// The sheet opens on every listed site. Choosing a site moves in on it; the
// move is animated when the site is already in or near view.
function View({ marks, focus, fitKey }) {
  const map = useMap();
  const key = marks.map((m) => m.id).join(",");
  useEffect(() => {
    if (!marks.length) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!focus) {
      map.fitBounds(L.latLngBounds(marks.map((m) => [m.lat, m.lon])).pad(0.35), { maxZoom: SITE_ZOOM, animate: false });
      return;
    }
    const near = map.getBounds().pad(1).contains([focus.lat, focus.lon]);
    if (near && !reduce) map.flyTo([focus.lat, focus.lon], SITE_ZOOM, { duration: 0.6 });
    else map.setView([focus.lat, focus.lon], SITE_ZOOM, { animate: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, focus?.id, fitKey, map]);
  return null;
}

function Legend({ present, shared, className = "" }) {
  return (
    <div className={className}>
      {present.map((s) => (
        <span key={s} className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full" style={{ background: SEVERITY_COLOR[s], boxShadow: `0 0 0 1px ${INK}` }} aria-hidden />
          {SEVERITY_LABEL[s]} site
        </span>
      ))}
      <span className="flex items-center gap-2">
        <span className="h-0 w-3 border-t-[3px] border-ink" aria-hidden />
        Railway track
      </span>
      <span className="flex items-center gap-2">
        <span className="mx-[3px] h-1.5 w-1.5 rounded-full bg-ink" aria-hidden />
        Site on another sheet
      </span>
      {shared > 1 && <span className="text-muted">{shared} listed sites share a recorded position; leaders show where.</span>}
    </div>
  );
}

export default function PlanMap({ marks, others = [], selectedId, focusId, onSelect, onFitAll, sheet, className = "h-[380px]" }) {
  const focus = useMemo(() => marks.find((m) => m.id === focusId) || null, [marks, focusId]);
  const present = SEVERITIES.filter((s) => marks.some((m) => normaliseSeverity(m.severity) === s));
  const [shared, setShared] = useState(0);
  const [fitKey, setFitKey] = useState(0);
  const unplotted = sheet ? sheet.onSheet - marks.length : 0;

  return (
    <div>
      <div className={`relative border-2 border-rule ${className}`}>
        <MapContainer center={[22.5, 79]} zoom={4} className="rv-plan h-full w-full" scrollWheelZoom={false} attributionControl={false} aria-label="Plan of the listed sites">
          <AttributionControl prefix={false} />
          <TileLayer {...PLAN_BASE} className="rv-plan-base" opacity={0.6} maxNativeZoom={PLAN_BASE.maxZoom} maxZoom={18} />
          <TileLayer {...RAILWAYS} className="rv-plan-track" />
          <ScaleControl position="bottomleft" imperial={false} />
          <View marks={marks} focus={focus} fitKey={fitKey} />
          {others.map((o) => (
            <CircleMarker key={o.id} center={[o.lat, o.lon]} radius={2.5} pathOptions={{ color: INK, fillColor: INK, fillOpacity: 0.8, weight: 0, interactive: false }} />
          ))}
          {focus && <Circle center={[focus.lat, focus.lon]} radius={SITE_RADIUS_M} pathOptions={{ color: INK, weight: 1, dashArray: "4 3", fill: false, interactive: false }} />}
          <Marks marks={marks} selectedId={selectedId} onSelect={onSelect} onShared={setShared} />
        </MapContainer>

        {/* Title block, as on a plan sheet: what this sheet holds and how to read it. */}
        <div className="absolute right-0 top-0 z-[500] hidden w-60 border-b-2 border-l-2 border-rule bg-surface text-xs sm:block">
          <div className="flex items-start justify-between gap-3 border-b border-rule px-3 py-2">
            <div>
              <div className="text-[13px] font-bold tracking-tight">Site plan</div>
              {sheet && (
                <div className="text-muted">
                  Sheet {sheet.page} of {sheet.pages} · {sheet.total} sites
                </div>
              )}
            </div>
            <div className="flex flex-col items-center text-[11px] font-bold leading-none" title="North is up">
              <Navigation className="h-4 w-4 fill-ink" aria-hidden />N
            </div>
          </div>
          <Legend present={present} shared={shared} className="flex flex-col gap-1 px-3 py-2 leading-5" />
        </div>

        {marks.length > 0 && (focus || marks.length > 1) && (
          <button
            type="button"
            onClick={() => {
              onFitAll?.();
              setFitKey((k) => k + 1);
            }}
            className="press absolute left-14 top-3 z-[500] inline-flex h-8 items-center gap-2 border border-rule bg-surface px-3 text-xs font-semibold text-ink hover:bg-canvas-2"
          >
            <Maximize2 className="h-3.5 w-3.5" aria-hidden />
            Fit the {marks.length} listed {marks.length === 1 ? "site" : "sites"}
          </button>
        )}

        {marks.length === 0 && (
          <div className="absolute inset-0 z-[500] grid place-items-center bg-surface p-6 text-center text-sm text-muted">
            The listed sites have no recorded position, so there is nothing to plot on this sheet.
          </div>
        )}
      </div>

      {/* Small screens: the legend as a strip under the plan, so marks never rely on colour alone. */}
      <Legend present={present} shared={shared} className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs sm:hidden" />
      {unplotted > 0 && marks.length > 0 && (
        <p className="mt-2 text-xs text-muted">
          {unplotted} listed {unplotted === 1 ? "site has" : "sites have"} no recorded position and {unplotted === 1 ? "is" : "are"} not on the plan.
        </p>
      )}
    </div>
  );
}
