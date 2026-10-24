import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import L from "../../utils/leafletPlugins.js";
import { LayersControl, MapContainer, TileLayer, useMap } from "react-leaflet";
import { fileUrl, getMapFeatures, getStatsSummary } from "../../api/encroachment.js";
import {
  CLASS_LABEL,
  SEVERITIES,
  SEVERITY_COLOR,
  STATUS_LABEL,
  classLabel,
  shortSite,
} from "../../utils/encroachmentFormat.js";
import { shortId } from "../../utils/incidentFormat.js";
import { formatDateTime, timeAgo } from "../../utils/formatDate.js";
import { DARK_BASE, DARK_LABELS, RAILWAYS, SATELLITE } from "../../utils/mapTiles.js";

const INDIA_CENTER = [22.5, 79.0];
const REFRESH_MS = 30000;
const OPEN_STATUSES = "reported,under_review,verified,action_taken";
const SEV_RANK = Object.fromEntries(SEVERITIES.map((s, i) => [s, i])); // 0 = critical
const INTRUSION_COLOR = "#38BDF8";
const HEAT_WEIGHT = { critical: 1, high: 0.75, medium: 0.5, low: 0.3 };

const isSite = (f) => (f.properties.kind || "encroachment_site") === "encroachment_site";
const latLng = (f) => [f.geometry.coordinates[1], f.geometry.coordinates[0]];
const intrusionSeverity = (f) => (f.properties.severity || "low").toLowerCase();

function sitePin(severity, selected) {
  const color = SEVERITY_COLOR[severity] || SEVERITY_COLOR.low;
  return L.divIcon({
    className: "",
    html: `<span class="rv-pin${selected ? " rv-pin-selected" : ""}" style="--c:${color}"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

function intrusionPin(selected) {
  return L.divIcon({
    className: "",
    html: `<span class="rv-diamond${selected ? " rv-pin-selected" : ""}" style="--c:${INTRUSION_COLOR}"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

// Cluster bubble: coloured by the worst severity inside, sized by count.
function clusterIcon(cluster) {
  const markers = cluster.getAllChildMarkers();
  const worst = markers.reduce((best, m) => Math.min(best, m.options.rank ?? 9), 9);
  const color = worst < SEVERITIES.length ? SEVERITY_COLOR[SEVERITIES[worst]] : INTRUSION_COLOR;
  const n = cluster.getChildCount();
  const size = n < 10 ? 34 : n < 50 ? 42 : 52;
  return L.divIcon({
    className: "",
    html: `<span class="rv-cluster" style="--c:${color};width:${size}px;height:${size}px">${n}</span>`,
    iconSize: [size, size],
  });
}

// Imperative layer: marker clusters for sites and intrusion incidents.
function ClusterLayer({ features, selectedId, onSelect }) {
  const map = useMap();
  useEffect(() => {
    const group = L.markerClusterGroup({
      iconCreateFunction: clusterIcon,
      showCoverageOnHover: false,
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true,
    });
    features.forEach((f) => {
      const p = f.properties;
      const site = isSite(f);
      const marker = L.marker(latLng(f), {
        icon: site ? sitePin(p.max_severity, f.id === selectedId) : intrusionPin(f.id === selectedId),
        rank: site ? SEV_RANK[p.max_severity] : SEVERITIES.length,
      });
      const label = site
        ? `${shortSite(p.site_id)} · ${classLabel(p.cls)} · ${p.max_severity.toUpperCase()}`
        : `${shortId(p.incident_id)} · ${p.object_class} · ${intrusionSeverity(f).toUpperCase()}`;
      marker.bindTooltip(label, { direction: "top", offset: [0, -8], className: "rv-tooltip" });
      marker.on("click", () => onSelect(f.id));
      group.addLayer(marker);
    });
    map.addLayer(group);
    return () => map.removeLayer(group);
  }, [map, features, selectedId, onSelect]);
  return null;
}

// Imperative layer: heatmap weighted by severity and finding count.
function HeatLayer({ features }) {
  const map = useMap();
  useEffect(() => {
    if (!features.length) return undefined;
    const points = features.map((f) => {
      const p = f.properties;
      const w = isSite(f) ? (HEAT_WEIGHT[p.max_severity] ?? 0.3) * Math.min(1 + (p.finding_count || 1) / 4, 2) : 0.6;
      return [...latLng(f), w];
    });
    const layer = L.heatLayer(points, {
      radius: 28,
      blur: 22,
      maxZoom: 13,
      gradient: { 0.25: "#34D399", 0.5: "#FACC15", 0.75: "#F97316", 1.0: "#F43F5E" },
    });
    map.addLayer(layer);
    return () => map.removeLayer(layer);
  }, [map, features]);
  return null;
}

// Zooms to the data once, the first time it loads.
function FitToData({ features }) {
  const map = useMap();
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (done || features.length === 0) return;
    map.fitBounds(L.latLngBounds(features.map(latLng)).pad(0.3), { maxZoom: 14 });
    setDone(true);
  }, [features, done, map]);
  return null;
}

function Chip({ active, color, onClick, children, shape = "dot" }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-mono uppercase tracking-wide transition ${
        active ? "border-white/40 bg-white/10 text-white" : "border-white/10 text-white/40 hover:text-white/70"
      }`}
    >
      {color && (
        <span
          className={`h-2 w-2 ${shape === "diamond" ? "rotate-45" : "rounded-full"}`}
          style={{ background: color, boxShadow: `0 0 6px ${color}` }}
        />
      )}
      {children}
    </button>
  );
}

function Stat({ value, label, tone }) {
  return (
    <div className={`rounded-md p-2 ${tone === "danger" ? "bg-rose-500/10" : tone === "info" ? "bg-sky-500/10" : "bg-white/5"}`}>
      <div className={`text-2xl font-bold ${tone === "danger" ? "text-rose-400" : tone === "info" ? "text-sky-300" : "text-white"}`}>
        {value}
      </div>
      <div className="text-[9px] uppercase tracking-wider text-white/50">{label}</div>
    </div>
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
  const [show, setShow] = useState({ sites: true, intrusions: true, heat: false });
  const [lastSync, setLastSync] = useState(null);

  useEffect(() => {
    let cancelled = false;
    function load() {
      const params = { status: openOnly ? OPEN_STATUSES : undefined, cls: cls || undefined, layers: "sites,intrusions" };
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

  const sites = useMemo(() => features.filter(isSite), [features]);
  const intrusions = useMemo(() => features.filter((f) => !isSite(f)), [features]);
  const visibleSites = useMemo(() => sites.filter((f) => severities.has(f.properties.max_severity)), [sites, severities]);
  const markers = useMemo(
    () => [...(show.sites ? visibleSites : []), ...(show.intrusions ? intrusions : [])],
    [show, visibleSites, intrusions],
  );
  const selected = features.find((f) => f.id === selectedId);

  const counts = useMemo(() => {
    const c = Object.fromEntries(SEVERITIES.map((s) => [s, 0]));
    sites.forEach((f) => (c[f.properties.max_severity] += 1));
    return c;
  }, [sites]);

  function toggleSeverity(s) {
    setSeverities((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  }
  const toggle = (key) => setShow((prev) => ({ ...prev, [key]: !prev[key] }));
  const enc = stats?.encroachment;

  return (
    <div className="relative h-[calc(100vh-7.5rem)] min-h-[560px] overflow-hidden bg-black">
      <MapContainer center={INDIA_CENTER} zoom={5} minZoom={4} className="h-full w-full rv-map" zoomControl={false}>
        <LayersControl position="bottomright">
          <LayersControl.BaseLayer checked name="Dark">
            <TileLayer {...DARK_BASE} maxNativeZoom={DARK_BASE.maxZoom} maxZoom={19} />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Satellite">
            <TileLayer {...SATELLITE} />
          </LayersControl.BaseLayer>
          <LayersControl.Overlay checked name="Place names">
            <TileLayer {...DARK_LABELS} maxNativeZoom={DARK_LABELS.maxZoom} maxZoom={19} />
          </LayersControl.Overlay>
          <LayersControl.Overlay checked name="Railway lines">
            <TileLayer {...RAILWAYS} opacity={0.75} />
          </LayersControl.Overlay>
        </LayersControl>

        <FitToData features={features} />
        {show.heat && <HeatLayer features={[...visibleSites, ...(show.intrusions ? intrusions : [])]} />}
        <ClusterLayer features={markers} selectedId={selectedId} onSelect={setSelectedId} />
      </MapContainer>

      <div className="pointer-events-none absolute inset-0 z-[400] rv-scanlines" />

      {/* HUD */}
      <div className="absolute left-4 top-4 z-[500] w-72 rounded-lg border border-white/10 bg-black/75 p-4 font-mono text-white backdrop-blur-md">
        <div className="flex items-center gap-1.5 text-[10px] tracking-[0.2em] text-signal">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-signal" /> LIVE
        </div>
        <h1 className="mt-2 text-sm font-semibold tracking-[0.25em]">RAILVIGIL // GEO-INT</h1>
        <p className="text-[10px] text-white/40">Encroachment sites and intrusion incidents · India</p>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <Stat value={sites.length} label={openOnly ? "Open sites" : "Sites"} />
          <Stat value={enc?.critical_open_sites ?? "–"} label="Critical open" tone="danger" />
          <Stat value={enc?.reports_last_7_days ?? "–"} label="Reports · 7 days" />
          <Stat value={intrusions.length} label="Mapped intrusions" tone="info" />
        </div>

        <div className="mt-3 space-y-1">
          {SEVERITIES.map((s) => {
            const pct = sites.length ? (counts[s] / sites.length) * 100 : 0;
            return (
              <div key={s} className="flex items-center gap-2 text-[10px]">
                <span className="w-14 uppercase text-white/60">{s}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${pct}%`, background: SEVERITY_COLOR[s], boxShadow: `0 0 8px ${SEVERITY_COLOR[s]}` }}
                  />
                </div>
                <span className="w-6 text-right">{counts[s]}</span>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-[9px] leading-snug text-white/30">
          Clusters show the worst severity inside. Intrusions appear when the video has a camera location.
          {lastSync && <> · synced {lastSync.toLocaleTimeString()}</>}
        </p>
        {error && <p className="mt-2 text-[10px] text-rose-400">Backend unreachable: {error}</p>}
      </div>

      {/* Filters and layers */}
      <div className="absolute left-1/2 top-4 z-[500] flex max-w-[62%] -translate-x-1/2 flex-wrap items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-black/70 px-3 py-2 backdrop-blur-md">
        <Chip active={show.sites} onClick={() => toggle("sites")} color="#F8FAFC">
          Sites
        </Chip>
        <Chip active={show.intrusions} onClick={() => toggle("intrusions")} color={INTRUSION_COLOR} shape="diamond">
          Intrusions
        </Chip>
        <Chip active={show.heat} onClick={() => toggle("heat")} color="#F97316">
          Heatmap
        </Chip>
        <span className="mx-1 h-4 w-px bg-white/15" />
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
          aria-label="Class"
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

      {!error && lastSync && features.length === 0 && (
        <div className="absolute bottom-6 left-1/2 z-[500] -translate-x-1/2 rounded-md border border-white/10 bg-black/70 px-4 py-2 font-mono text-xs text-white/70 backdrop-blur">
          Nothing located yet. Upload photos with GPS or a map pin, or videos with a camera location.
        </div>
      )}

      {selected && (
        <aside className="absolute right-4 top-4 z-[500] w-80 overflow-hidden rounded-lg border border-white/15 bg-black/80 text-white backdrop-blur-md">
          {isSite(selected) ? <SitePanel f={selected} onClose={() => setSelectedId(null)} /> : (
            <IntrusionPanel f={selected} onClose={() => setSelectedId(null)} />
          )}
        </aside>
      )}
    </div>
  );
}

function PanelHead({ code, title, onClose }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div>
        <div className="font-mono text-[10px] tracking-widest text-signal">{code}</div>
        <div className="text-base font-semibold">{title}</div>
      </div>
      <button onClick={onClose} className="text-white/50 hover:text-white" aria-label="Close">
        ✕
      </button>
    </div>
  );
}

function Row({ k, v }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-white/50">{k}</dt>
      <dd className="truncate">{v}</dd>
    </div>
  );
}

const panelButton =
  "block rounded-md bg-signal py-2 text-center text-sm font-semibold text-black transition-all duration-200 hover:scale-[1.02] hover:brightness-110 active:scale-[0.98]";

function SitePanel({ f, onClose }) {
  const p = f.properties;
  return (
    <>
      {p.thumbnail_url ? (
        <img src={fileUrl(p.thumbnail_url)} alt="Latest evidence crop" className="h-44 w-full bg-black object-contain" />
      ) : (
        <div className="flex h-24 items-center justify-center text-xs text-white/40">No evidence image</div>
      )}
      <div className="space-y-3 p-4">
        <PanelHead code={shortSite(p.site_id)} title={classLabel(p.cls)} onClose={onClose} />
        <div className="flex flex-wrap gap-1.5 text-[11px]">
          <span className="rounded px-2 py-0.5 font-semibold uppercase text-black" style={{ background: SEVERITY_COLOR[p.max_severity] }}>
            {p.max_severity}
          </span>
          <span className="rounded-full bg-white/10 px-2 py-0.5">{STATUS_LABEL[p.status]}</span>
          <span className="rounded-full bg-white/10 px-2 py-0.5">{p.finding_count} finding(s)</span>
        </div>
        <dl className="space-y-1 font-mono text-[11px]">
          <Row k="Report" v={p.latest_report_no || "—"} />
          <Row k="First seen" v={formatDateTime(p.first_reported_at)} />
          <Row k="Last seen" v={timeAgo(p.last_reported_at)} />
          <Row k="Coords" v={`${f.geometry.coordinates[1].toFixed(5)}, ${f.geometry.coordinates[0].toFixed(5)}`} />
        </dl>
        <Link to={`/sites/${p.site_id}`} className={panelButton}>
          Open site case →
        </Link>
      </div>
    </>
  );
}

function IntrusionPanel({ f, onClose }) {
  const p = f.properties;
  const sev = intrusionSeverity(f);
  return (
    <div className="space-y-3 p-4">
      <PanelHead code={shortId(p.incident_id)} title={`${p.object_class} in track zone`} onClose={onClose} />
      <div className="flex flex-wrap gap-1.5 text-[11px]">
        <span className="rounded px-2 py-0.5 font-semibold uppercase text-black" style={{ background: SEVERITY_COLOR[sev] || INTRUSION_COLOR }}>
          {sev}
        </span>
        <span className="rounded-full bg-white/10 px-2 py-0.5">{p.event_type}</span>
        <span className="rounded-full bg-white/10 px-2 py-0.5">risk {Math.round(p.risk_score)}</span>
      </div>
      <dl className="space-y-1 font-mono text-[11px]">
        <Row k="Camera" v={p.camera_label || "—"} />
        <Row k="Recorded" v={formatDateTime(p.created_at)} />
        <Row k="Coords" v={`${f.geometry.coordinates[1].toFixed(5)}, ${f.geometry.coordinates[0].toFixed(5)}`} />
      </dl>
      <Link to={`/incidents/${p.incident_id}`} className={panelButton}>
        Open incident →
      </Link>
    </div>
  );
}
