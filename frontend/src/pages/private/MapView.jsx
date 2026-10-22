import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { LayersControl, MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import { fileUrl, getMapFeatures, getStatsSummary } from "../../api/encroachment.js";
import {
  CLASS_LABEL,
  SEVERITIES,
  SEVERITY_COLOR,
  STATUS_LABEL,
  classLabel,
  severityBadge,
  shortSite,
} from "../../utils/encroachmentFormat.js";
import { formatDateTime, timeAgo } from "../../utils/formatDate.js";

const INDIA_CENTER = [22.5, 79.0];
const REFRESH_MS = 30000;
const OPEN_STATUSES = "reported,under_review,verified,action_taken";

const iconCache = {};
function pinIcon(severity, selected) {
  const key = `${severity}-${selected}`;
  if (!iconCache[key]) {
    const color = SEVERITY_COLOR[severity] || SEVERITY_COLOR.low;
    iconCache[key] = L.divIcon({
      className: "",
      html: `<span class="rv-pin${selected ? " rv-pin-selected" : ""}" style="--c:${color}"></span>`,
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    });
  }
  return iconCache[key];
}

// Zooms to the sites once, the first time they load.
function FitToSites({ features }) {
  const map = useMap();
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (done || features.length === 0) return;
    const bounds = L.latLngBounds(features.map((f) => [f.geometry.coordinates[1], f.geometry.coordinates[0]]));
    map.fitBounds(bounds.pad(0.5), { maxZoom: 15 });
    setDone(true);
  }, [features, done, map]);
  return null;
}

function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return <span>{now.toISOString().slice(11, 19)} UTC</span>;
}

function Chip({ active, color, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-mono uppercase tracking-wide transition ${
        active ? "border-white/40 bg-white/10 text-white" : "border-white/10 text-white/40 hover:text-white/70"
      }`}
    >
      {color && <span className="h-2 w-2 rounded-full" style={{ background: color, boxShadow: `0 0 6px ${color}` }} />}
      {children}
    </button>
  );
}

export default function MapView() {
  const [features, setFeatures] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [severities, setSeverities] = useState(() => new Set(SEVERITIES));
  const [openOnly, setOpenOnly] = useState(true);
  const [cls, setCls] = useState("");
  const [lastSync, setLastSync] = useState(null);

  useEffect(() => {
    let cancelled = false;
    function load() {
      const params = { status: openOnly ? OPEN_STATUSES : undefined, cls: cls || undefined };
      Promise.all([getMapFeatures(params), getStatsSummary()])
        .then(([geo, s]) => {
          if (cancelled) return;
          setFeatures(geo.features || []);
          setStats(s);
          setLastSync(new Date());
          setError("");
        })
        .catch((e) => !cancelled && setError(e.message));
    }
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [openOnly, cls]);

  const visible = useMemo(
    () => features.filter((f) => severities.has(f.properties.max_severity)),
    [features, severities],
  );
  const selected = features.find((f) => f.id === selectedId);

  const counts = useMemo(() => {
    const c = Object.fromEntries(SEVERITIES.map((s) => [s, 0]));
    features.forEach((f) => (c[f.properties.max_severity] = (c[f.properties.max_severity] || 0) + 1));
    return c;
  }, [features]);

  function toggleSeverity(s) {
    setSeverities((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  }

  const enc = stats?.encroachment;
  const intr = stats?.intrusion;

  return (
    <div className="relative m-4 mt-0 h-[calc(100vh-6.5rem)] overflow-hidden rounded-3xl border border-emerald-400/20 bg-black shadow-2xl">
      <MapContainer center={INDIA_CENTER} zoom={5} minZoom={4} className="h-full w-full rv-map" zoomControl={false}>
        <LayersControl position="bottomright">
          <LayersControl.BaseLayer checked name="Dark">
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
              subdomains="abcd"
              maxZoom={20}
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Satellite">
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution="Tiles &copy; Esri"
              maxZoom={19}
            />
          </LayersControl.BaseLayer>
          <LayersControl.Overlay checked name="Railway lines">
            <TileLayer
              url="https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openrailwaymap.org/">OpenRailwayMap</a> (CC-BY-SA)'
              subdomains="abc"
              maxZoom={19}
              opacity={0.75}
            />
          </LayersControl.Overlay>
        </LayersControl>

        <FitToSites features={features} />

        {visible.map((f) => {
          const [lon, lat] = f.geometry.coordinates;
          const p = f.properties;
          return (
            <Marker
              key={f.id}
              position={[lat, lon]}
              icon={pinIcon(p.max_severity, f.id === selectedId)}
              eventHandlers={{ click: () => setSelectedId(f.id) }}
            >
              <Tooltip direction="top" offset={[0, -8]} className="rv-tooltip">
                <span className="font-mono text-[11px]">
                  {shortSite(p.site_id)} · {classLabel(p.cls)} · {p.max_severity.toUpperCase()}
                </span>
              </Tooltip>
            </Marker>
          );
        })}
      </MapContainer>

      {/* scanline overlay for the "ops room" look */}
      <div className="pointer-events-none absolute inset-0 z-[400] rv-scanlines" />

      {/* HUD: title + counters */}
      <div className="absolute left-4 top-4 z-[500] w-72 rounded-2xl border border-emerald-400/20 bg-black/70 p-4 font-mono text-white backdrop-blur-md">
        <div className="flex items-center justify-between text-[10px] tracking-[0.2em] text-emerald-300/80">
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" /> LIVE
          </span>
          <Clock />
        </div>
        <h1 className="mt-2 text-sm font-semibold tracking-[0.25em]">RAILVIGIL // GEO-INT</h1>
        <p className="text-[10px] text-white/40">Railway corridor encroachment watch · India</p>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <div className="rounded-xl bg-white/5 p-2">
            <div className="text-2xl font-bold text-white">{features.length}</div>
            <div className="text-[9px] uppercase tracking-wider text-white/50">{openOnly ? "Open sites" : "Sites"}</div>
          </div>
          <div className="rounded-xl bg-rose-500/10 p-2">
            <div className="text-2xl font-bold text-rose-400">{enc?.critical_open_sites ?? "–"}</div>
            <div className="text-[9px] uppercase tracking-wider text-white/50">Critical open</div>
          </div>
          <div className="rounded-xl bg-white/5 p-2">
            <div className="text-2xl font-bold">{enc?.reports_last_7_days ?? "–"}</div>
            <div className="text-[9px] uppercase tracking-wider text-white/50">Reports · 7 days</div>
          </div>
          <div className="rounded-xl bg-white/5 p-2">
            <div className="text-2xl font-bold">{intr?.incidents_total ?? "–"}</div>
            <div className="text-[9px] uppercase tracking-wider text-white/50">Intrusions*</div>
          </div>
        </div>

        <div className="mt-3 space-y-1">
          {SEVERITIES.map((s) => {
            const pct = features.length ? (counts[s] / features.length) * 100 : 0;
            return (
              <div key={s} className="flex items-center gap-2 text-[10px]">
                <span className="w-14 uppercase text-white/60">{s}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${pct}%`, background: SEVERITY_COLOR[s], boxShadow: `0 0 8px ${SEVERITY_COLOR[s]}` }}
                  />
                </div>
                <span className="w-5 text-right">{counts[s]}</span>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-[9px] leading-snug text-white/30">
          * Intrusion incidents come from videos and have no map location yet.
          {lastSync && <> · synced {lastSync.toLocaleTimeString()}</>}
        </p>
        {error && <p className="mt-2 text-[10px] text-rose-400">Backend unreachable: {error}</p>}
      </div>

      {/* Filters */}
      <div className="absolute left-1/2 top-4 z-[500] flex max-w-[60%] -translate-x-1/2 flex-wrap items-center justify-center gap-1.5 rounded-2xl border border-white/10 bg-black/70 px-3 py-2 backdrop-blur-md">
        {SEVERITIES.map((s) => (
          <Chip key={s} active={severities.has(s)} color={SEVERITY_COLOR[s]} onClick={() => toggleSeverity(s)}>
            {s}
          </Chip>
        ))}
        <span className="mx-1 h-4 w-px bg-white/15" />
        <Chip active={openOnly} onClick={() => setOpenOnly((v) => !v)}>
          {openOnly ? "Open only" : "All statuses"}
        </Chip>
        <select
          value={cls}
          onChange={(e) => setCls(e.target.value)}
          className="rounded-full border border-white/10 bg-black/60 px-2.5 py-1 font-mono text-[11px] uppercase text-white/80 outline-none"
        >
          <option value="">All classes</option>
          {Object.entries(CLASS_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
      </div>

      {/* Empty state */}
      {!error && lastSync && features.length === 0 && (
        <div className="absolute bottom-6 left-1/2 z-[500] -translate-x-1/2 rounded-xl border border-white/10 bg-black/70 px-4 py-2 font-mono text-xs text-white/70 backdrop-blur">
          No located sites yet. Upload photos with GPS or a map pin to see them here.
        </div>
      )}

      {/* Side panel */}
      {selected && (
        <aside className="absolute right-4 top-4 z-[500] w-80 overflow-hidden rounded-2xl border border-white/15 bg-black/80 text-white backdrop-blur-md">
          {selected.properties.thumbnail_url ? (
            <img
              src={fileUrl(selected.properties.thumbnail_url)}
              alt="Latest evidence crop"
              className="h-44 w-full bg-black object-contain"
            />
          ) : (
            <div className="flex h-24 items-center justify-center text-xs text-white/40">No evidence image</div>
          )}
          <div className="space-y-3 p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="font-mono text-[10px] tracking-widest text-emerald-300/80">
                  {shortSite(selected.properties.site_id)}
                </div>
                <div className="text-base font-semibold">{classLabel(selected.properties.cls)}</div>
              </div>
              <button onClick={() => setSelectedId(null)} className="text-white/50 hover:text-white" aria-label="Close">
                ✕
              </button>
            </div>
            <div className="flex flex-wrap gap-1.5 text-[11px]">
              <span className={`rounded-full px-2 py-0.5 font-semibold uppercase ${severityBadge(selected.properties.max_severity)}`}>
                {selected.properties.max_severity}
              </span>
              <span className="rounded-full bg-white/10 px-2 py-0.5">{STATUS_LABEL[selected.properties.status]}</span>
              <span className="rounded-full bg-white/10 px-2 py-0.5">{selected.properties.finding_count} finding(s)</span>
            </div>
            <dl className="space-y-1 font-mono text-[11px]">
              <div className="flex justify-between">
                <dt className="text-white/50">Report</dt>
                <dd>{selected.properties.latest_report_no || "—"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-white/50">First seen</dt>
                <dd>{formatDateTime(selected.properties.first_reported_at)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-white/50">Last seen</dt>
                <dd>{timeAgo(selected.properties.last_reported_at)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-white/50">Coords</dt>
                <dd>
                  {selected.geometry.coordinates[1].toFixed(5)}, {selected.geometry.coordinates[0].toFixed(5)}
                </dd>
              </div>
            </dl>
            <Link
              to={`/sites/${selected.properties.site_id}`}
              className="block rounded-xl bg-emerald-400 py-2 text-center text-sm font-semibold text-black hover:bg-emerald-300"
            >
              Open site case →
            </Link>
          </div>
        </aside>
      )}
    </div>
  );
}
