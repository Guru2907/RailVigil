import { useEffect, useMemo, useState } from "react";
import { Maximize2, Navigation2 } from "lucide-react";
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
const LOCAL_KM = 50; // a sheet shows one locality; listed sites further away are named, not squeezed in
const SURFACE = "#F7F8F3";

// Recorded positions, compared as stored (5 decimals is about a metre).
const spot = (m) => `${m.lat.toFixed(5)},${m.lon.toFixed(5)}`;

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

function Marks({ marks, selectedId, onSelect }) {
  const map = useMap();
  const [tick, setTick] = useState(0);
  // Lay the marks out again whenever the scale of the sheet changes, including
  // the first fit, which happens just after these marks mount.
  useMapEvents({ zoomend: () => setTick((t) => t + 1), viewreset: () => setTick((t) => t + 1) });
  useEffect(() => {
    const id = requestAnimationFrame(() => setTick((t) => t + 1));
    return () => cancelAnimationFrame(id);
  }, [marks]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const placed = useMemo(() => layOut(map, marks), [map, marks, tick]);

  return placed.map((m) => (
    <span key={m.id}>
      {m.fanned && (
        <>
          <Polyline positions={[[m.lat, m.lon], m.at]} pathOptions={{ color: SURFACE, weight: 4, interactive: false }} />
          <Polyline positions={[[m.lat, m.lon], m.at]} pathOptions={{ color: INK, weight: 1.25, interactive: false }} />
          <CircleMarker center={[m.lat, m.lon]} radius={3.5} pathOptions={{ color: SURFACE, fillColor: INK, fillOpacity: 1, weight: 1.5, interactive: false }} />
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

// The sheet opens on the locality of the first listed site (sites within
// LOCAL_KM of it), because a plan that spans a continent shows nothing.
// "Fit all" pulls back to every listed site; choosing a site moves in on it.
function View({ marks, local, focus, fitAll, fitKey }) {
  const map = useMap();
  const key = marks.map((m) => m.id).join(",");
  useEffect(() => {
    if (!marks.length) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!focus) {
      const frame = fitAll || !local.length ? marks : local;
      map.fitBounds(L.latLngBounds(frame.map((m) => [m.lat, m.lon])).pad(0.4), { maxZoom: SITE_ZOOM - 1, animate: false });
      return;
    }
    const near = map.getBounds().pad(1).contains([focus.lat, focus.lon]);
    if (near && !reduce) map.flyTo([focus.lat, focus.lon], SITE_ZOOM, { duration: 0.6 });
    else map.setView([focus.lat, focus.lon], SITE_ZOOM, { animate: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, focus?.id, fitAll, fitKey, map]);
  return null;
}

// How many "other sheet" ticks are inside the frame, so the legend only names what can be seen.
function OthersInView({ others, onCount }) {
  const map = useMap();
  const count = () => onCount(others.filter((o) => map.getBounds().contains([o.lat, o.lon])).length);
  useMapEvents({ moveend: count });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(count, [others]);
  return null;
}

function Legend({ present, shared, away, othersInView, className = "" }) {
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
      {othersInView > 0 && (
        <span className="flex items-center gap-2">
          <span className="mx-[2px] h-2 w-2 rounded-full border-[1.5px] border-ink bg-surface" aria-hidden />
          Site on another sheet
        </span>
      )}
      {shared > 1 && <span className="text-muted">{shared} listed sites share a recorded position with another; leaders show where.</span>}
      {away > 0 && (
        <span className="text-muted">
          {away} listed {away === 1 ? "site lies" : "sites lie"} more than {LOCAL_KM} km from here. Choose a row to move there.
        </span>
      )}
    </div>
  );
}

export default function PlanMap({ marks, others = [], selectedId, focusId, onSelect, onFitAll, sheet, className = "h-[380px]" }) {
  const focus = useMemo(() => marks.find((m) => m.id === focusId) || null, [marks, focusId]);
  const present = SEVERITIES.filter((s) => marks.some((m) => normaliseSeverity(m.severity) === s));
  const [fitKey, setFitKey] = useState(0);
  const [fitAll, setFitAll] = useState(false);
  const [othersInView, setOthersInView] = useState(0);

  // Facts about the listed sites, from their recorded coordinates (not from the zoom level).
  const anchor = marks.find((m) => m.id === selectedId) || marks[0];
  const local = useMemo(
    () => (anchor ? marks.filter((m) => L.latLng(m.lat, m.lon).distanceTo([anchor.lat, anchor.lon]) <= LOCAL_KM * 1000) : []),
    [marks, anchor],
  );
  const shared = useMemo(() => {
    const counts = {};
    marks.forEach((m) => (counts[spot(m)] = (counts[spot(m)] || 0) + 1));
    return marks.filter((m) => counts[spot(m)] > 1).length;
  }, [marks]);
  const away = fitAll ? 0 : marks.length - local.length;
  useEffect(() => setFitAll(false), [focusId, marks]);
  const unplotted = sheet ? sheet.onSheet - marks.length : 0;

  return (
    <div>
      <div className={`relative border-2 border-rule ${className}`}>
        <MapContainer center={[22.5, 79]} zoom={4} className="rv-plan h-full w-full" scrollWheelZoom={false} attributionControl={false} aria-label="Plan of the listed sites">
          <AttributionControl prefix={false} />
          <TileLayer {...PLAN_BASE} attribution="&copy; Esri, &copy; OpenStreetMap" className="rv-plan-base" opacity={0.45} maxNativeZoom={PLAN_BASE.maxZoom} maxZoom={18} />
          {/* The track is drawn only where it can be read as a line, not as a web over a continent. */}
          <TileLayer {...RAILWAYS} attribution="&copy; OpenRailwayMap" className="rv-plan-track" minZoom={9} />
          <ScaleControl position="bottomleft" imperial={false} />
          <View marks={marks} local={local} focus={focus} fitAll={fitAll} fitKey={fitKey} />
          <OthersInView others={others} onCount={setOthersInView} />
          {others.map((o) => (
            <CircleMarker key={o.id} center={[o.lat, o.lon]} radius={3.5} pathOptions={{ color: INK, fillColor: SURFACE, fillOpacity: 1, weight: 1.5, interactive: false }} />
          ))}
          {focus && <Circle center={[focus.lat, focus.lon]} radius={SITE_RADIUS_M} pathOptions={{ color: INK, weight: 1, dashArray: "4 3", fill: false, interactive: false }} />}
          <Marks marks={marks} selectedId={selectedId} onSelect={onSelect} />
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
              <Navigation2 className="h-4 w-4 fill-ink" aria-hidden />N
            </div>
          </div>
          <Legend present={present} shared={shared} away={away} othersInView={othersInView} className="flex flex-col gap-1 px-3 py-2 leading-5" />
        </div>

        {marks.length > 0 && (focus || marks.length > 1) && (
          <button
            type="button"
            onClick={() => {
              onFitAll?.();
              setFitAll(true);
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
      <Legend present={present} shared={shared} away={away} othersInView={othersInView} className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs sm:hidden" />
      {unplotted > 0 && marks.length > 0 && (
        <p className="mt-2 text-xs text-muted">
          {unplotted} listed {unplotted === 1 ? "site has" : "sites have"} no recorded position and {unplotted === 1 ? "is" : "are"} not on the plan.
        </p>
      )}
    </div>
  );
}
