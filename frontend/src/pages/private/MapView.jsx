import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, SlidersHorizontal, X } from "lucide-react";
import "leaflet/dist/leaflet.css";
import L from "../../utils/leafletPlugins.js";
import { AttributionControl, MapContainer, ScaleControl, TileLayer, ZoomControl, useMap } from "react-leaflet";
import { getMapFeatures } from "../../api/encroachment.js";
import CasePanel from "../../components/encroachment/CasePanel.jsx";
import { FilterChips, KeyValue, Segmented, SeverityBadge, btn, selectClass } from "../../components/ui/index.jsx";
import { CLASS_LABEL, classLabel, shortSite } from "../../utils/encroachmentFormat.js";
import { eventLabel, shortId } from "../../utils/incidentFormat.js";
import { formatDateTime } from "../../utils/formatDate.js";
import { PLAN_BASE, RAILWAYS, SATELLITE } from "../../utils/mapTiles.js";
import { INFO_COLOR, SEVERITIES, SEVERITY_COLOR, SEVERITY_LABEL, normaliseSeverity } from "../../utils/severity.js";

const INDIA_CENTER = [22.5, 79.0];
const REFRESH_MS = 30000;
const OPEN_STATUSES = "reported,under_review,verified,action_taken";
const SEV_RANK = Object.fromEntries(SEVERITIES.map((s, i) => [s, i])); // 0 = critical
const HEAT_WEIGHT = { critical: 1, high: 0.75, medium: 0.5, low: 0.3 };

const isSite = (f) => (f.properties.kind || "encroachment_site") === "encroachment_site";
const latLng = (f) => [f.geometry.coordinates[1], f.geometry.coordinates[0]];

function sitePin(severity, selected) {
  return L.divIcon({
    className: "",
    html: `<span class="rv-dot${selected ? " rv-dot-selected" : ""}" style="--c:${SEVERITY_COLOR[normaliseSeverity(severity)]}"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

function intrusionPin(selected) {
  return L.divIcon({
    className: "",
    html: `<span class="rv-square${selected ? " rv-dot-selected" : ""}" style="--c:${INFO_COLOR}"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

// A group of marks: the count, in the colour of the worst severity inside.
function clusterIcon(cluster) {
  const worst = cluster.getAllChildMarkers().reduce((best, m) => Math.min(best, m.options.rank ?? 9), 9);
  const colour = worst < SEVERITIES.length ? SEVERITY_COLOR[SEVERITIES[worst]] : INFO_COLOR;
  const n = cluster.getChildCount();
  const size = n < 10 ? 32 : n < 50 ? 40 : 48;
  return L.divIcon({
    className: "",
    html: `<span class="rv-cluster" style="--c:${colour};width:${size}px;height:${size}px">${n}</span>`,
    iconSize: [size, size],
  });
}

function ClusterLayer({ features, selectedId, onSelect }) {
  const map = useMap();
  useEffect(() => {
    const group = L.markerClusterGroup({ iconCreateFunction: clusterIcon, showCoverageOnHover: false, maxClusterRadius: 46, spiderfyOnMaxZoom: true });
    features.forEach((f) => {
      const p = f.properties;
      const site = isSite(f);
      const marker = L.marker(latLng(f), {
        icon: site ? sitePin(p.max_severity, f.id === selectedId) : intrusionPin(f.id === selectedId),
        rank: site ? SEV_RANK[normaliseSeverity(p.max_severity)] : SEVERITIES.length,
        title: site ? `${shortSite(p.site_id)}, ${classLabel(p.cls)}` : `${shortId(p.incident_id)}, ${p.object_class}`,
      });
      marker.bindTooltip(
        site ? `${shortSite(p.site_id)} · ${classLabel(p.cls)} · ${SEVERITY_LABEL[normaliseSeverity(p.max_severity)]}` : `${shortId(p.incident_id)} · ${eventLabel(p.event_type)}`,
        { direction: "top", offset: [0, -8], className: "rv-tooltip" },
      );
      marker.on("click", () => onSelect(f.id));
      group.addLayer(marker);
    });
    map.addLayer(group);
    return () => map.removeLayer(group);
  }, [map, features, selectedId, onSelect]);
  return null;
}

// Density of sites, weighted by severity and number of findings.
function HeatLayer({ features }) {
  const map = useMap();
  useEffect(() => {
    if (!features.length) return undefined;
    const points = features.map((f) => {
      const p = f.properties;
      const w = isSite(f) ? (HEAT_WEIGHT[normaliseSeverity(p.max_severity)] ?? 0.3) * Math.min(1 + (p.finding_count || 1) / 4, 2) : 0.6;
      return [...latLng(f), w];
    });
    const layer = L.heatLayer(points, { radius: 28, blur: 22, maxZoom: 13, gradient: { 0.3: "#2F6B45", 0.55: "#B26B00", 1.0: "#B8321F" } });
    map.addLayer(layer);
    return () => map.removeLayer(layer);
  }, [map, features]);
  return null;
}

// Fits the sheet to the data once, the first time it loads.
function FitToData({ features }) {
  const map = useMap();
  const [done, setDone] = useState(false);
  useEffect(() => {
    if (done || features.length === 0) return;
    map.fitBounds(L.latLngBounds(features.map(latLng)).pad(0.25), { maxZoom: 14 });
    setDone(true);
  }, [features, done, map]);
  return null;
}

function Group({ title, children }) {
  return (
    <div className="border-b border-line px-5 py-4">
      <h2 className="mb-2.5 text-xs font-bold">{title}</h2>
      {children}
    </div>
  );
}

// Every located site and incident on one sheet. Filters sit in a docked panel;
// choosing a mark opens the same case panel as the Sites page.
export default function MapView() {
  const [features, setFeatures] = useState(null);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [severity, setSeverity] = useState([]);
  const [openOnly, setOpenOnly] = useState(true);
  const [cls, setCls] = useState("");
  const [layers, setLayers] = useState(["sites", "intrusions"]);
  const [base, setBase] = useState("plan");
  const [lastSync, setLastSync] = useState(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    function load() {
      getMapFeatures({ status: openOnly ? OPEN_STATUSES : undefined, cls: cls || undefined, layers: "sites,intrusions" })
        .then((geo) => {
          if (cancelled) return;
          setFeatures(geo.features || []);
          setLastSync(new Date());
          setError("");
        })
        .catch((e) => !cancelled && setError(e.message));
    }
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [openOnly, cls]);

  const all = features || [];
  const sites = useMemo(() => all.filter(isSite), [all]);
  const intrusions = useMemo(() => all.filter((f) => !isSite(f)), [all]);
  const visibleSites = useMemo(
    () => sites.filter((f) => !severity.length || severity.includes(normaliseSeverity(f.properties.max_severity))),
    [sites, severity],
  );
  const marks = useMemo(
    () => [...(layers.includes("sites") ? visibleSites : []), ...(layers.includes("intrusions") ? intrusions : [])],
    [layers, visibleSites, intrusions],
  );
  const counts = useMemo(() => {
    const c = Object.fromEntries(SEVERITIES.map((s) => [s, 0]));
    sites.forEach((f) => (c[normaliseSeverity(f.properties.max_severity)] += 1));
    return c;
  }, [sites]);
  const selected = all.find((f) => f.id === selectedId);
  const selectedSite = selected && isSite(selected);
  const sp = selected?.properties;

  const filters = (
    <>
      <div className="border-b border-rule px-5 py-4">
        <h1 className="text-xl font-bold leading-none tracking-tight">GIS map</h1>
        <p className="mt-1.5 text-xs text-muted">
          {features === null && !error
            ? "Loading located sites and incidents"
            : `${visibleSites.length} ${openOnly ? "open " : ""}sites and ${intrusions.length} incidents with a recorded position`}
        </p>
      </div>
      <Group title="Show on the sheet">
        <FilterChips label="" options={[["sites", "Sites"], ["intrusions", "Incidents"], ["heat", "Density"]]} value={layers} onChange={setLayers} />
      </Group>
      <Group title="Sites by severity">
        <FilterChips label="" options={SEVERITIES.map((s) => [s, `${SEVERITY_LABEL[s]} ${counts[s]}`])} value={severity} onChange={setSeverity} />
        <p className="mt-2 text-xs text-muted">None chosen shows every severity.</p>
      </Group>
      <Group title="Sites by stage and class">
        <FilterChips label="" single options={[["open", "Open only"]]} value={openOnly ? "open" : ""} onChange={(v) => setOpenOnly(Boolean(v))} />
        <select aria-label="Class" className={`${selectClass} mt-2 w-full text-sm`} value={cls} onChange={(e) => setCls(e.target.value)}>
          <option value="">All classes</option>
          {Object.entries(CLASS_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
      </Group>
      <Group title="Base">
        <Segmented label="Base map" options={[["plan", "Plan"], ["satellite", "Satellite"]]} value={base} onChange={setBase} />
      </Group>
      <div className="space-y-1.5 px-5 py-4 text-xs leading-relaxed">
        <div className="flex items-center gap-2">
          <span className="rv-dot !static" style={{ "--c": SEVERITY_COLOR.critical }} aria-hidden /> Site, coloured by severity
        </div>
        <div className="flex items-center gap-2">
          <span className="rv-square !static" style={{ "--c": INFO_COLOR }} aria-hidden /> Intrusion incident
        </div>
        <div className="flex items-center gap-2">
          <span className="rv-cluster !static !h-5 !w-5 !text-[10px]" style={{ "--c": SEVERITY_COLOR.high }} aria-hidden>
            3
          </span>
          Several marks; colour of the worst inside
        </div>
        <p className="pt-1 text-muted">
          An incident appears only when its video was given a camera position.
          {lastSync && ` Updated ${lastSync.toLocaleTimeString()}; refreshes every 30 s.`}
        </p>
        {error && <p className="font-semibold text-sev-critical">The backend cannot be reached ({error}).</p>}
      </div>
    </>
  );

  return (
    <div className="relative flex h-[calc(100vh-78px)] min-h-[520px]">
      <aside className="hidden w-[300px] shrink-0 overflow-y-auto border-r-2 border-rule bg-surface lg:block">{filters}</aside>

      <div className="relative min-w-0 flex-1">
        <MapContainer center={INDIA_CENTER} zoom={5} minZoom={4} className="rv-plan h-full w-full" zoomControl={false} attributionControl={false}>
          <AttributionControl prefix={false} />
          <ZoomControl position="topright" />
          <ScaleControl position="bottomleft" imperial={false} />
          {base === "plan" ? (
            <>
              <TileLayer {...PLAN_BASE} attribution="&copy; Esri, &copy; OpenStreetMap" className="rv-plan-base" opacity={0.6} maxNativeZoom={PLAN_BASE.maxZoom} maxZoom={19} />
              <TileLayer {...RAILWAYS} attribution="&copy; OpenRailwayMap" className="rv-plan-track" minZoom={8} />
            </>
          ) : (
            <TileLayer {...SATELLITE} attribution="&copy; Esri, Maxar" />
          )}
          <FitToData features={all} />
          {layers.includes("heat") && <HeatLayer features={[...visibleSites, ...(layers.includes("intrusions") ? intrusions : [])]} />}
          <ClusterLayer features={marks} selectedId={selectedId} onSelect={setSelectedId} />
        </MapContainer>

        <button
          type="button"
          onClick={() => setFiltersOpen(true)}
          className={`${btn.secondary} ${btn.small} absolute left-3 top-3 z-[500] lg:hidden`}
        >
          <SlidersHorizontal className="h-4 w-4" aria-hidden />
          Filters
        </button>

        {features !== null && !error && all.length === 0 && (
          <div className="absolute inset-x-4 bottom-10 z-[500] mx-auto max-w-md border-2 border-rule bg-surface px-4 py-3 text-center text-sm">
            Nothing has a recorded position yet. Upload photos that carry GPS or a map pin, or a video with a camera position.
          </div>
        )}
      </div>

      {filtersOpen && (
        <div className="absolute inset-0 z-[1100] lg:hidden">
          <div className="absolute inset-0 bg-ink/30" onClick={() => setFiltersOpen(false)} aria-hidden />
          <aside className="absolute inset-y-0 left-0 w-[300px] max-w-[88%] overflow-y-auto border-r-2 border-rule bg-surface" role="dialog" aria-label="Map filters">
            <button type="button" onClick={() => setFiltersOpen(false)} aria-label="Close filters" className="press absolute right-2 top-2 flex h-10 w-10 items-center justify-center rounded-sm hover:bg-canvas-2">
              <X className="h-4 w-4" aria-hidden />
            </button>
            {filters}
          </aside>
        </div>
      )}

      {selected && (
        <aside className="absolute inset-y-0 right-0 z-[1000] w-full max-w-[400px] overflow-y-auto border-l-2 border-rule bg-canvas p-3" aria-label="Selected mark">
          <div className="mb-2 flex justify-end">
            <button type="button" onClick={() => setSelectedId(null)} className={`${btn.secondary} ${btn.small}`}>
              <X className="h-4 w-4" aria-hidden />
              Close
            </button>
          </div>
          {selectedSite ? (
            <CasePanel
              site={{
                id: sp.site_id,
                cls: sp.cls,
                status: sp.status,
                max_severity: sp.max_severity,
                finding_count: sp.finding_count,
                latest_report_no: sp.latest_report_no,
                first_reported_at: sp.first_reported_at,
                last_reported_at: sp.last_reported_at,
                latitude: selected.geometry.coordinates[1],
                longitude: selected.geometry.coordinates[0],
              }}
            />
          ) : (
            <section className="border-2 border-rule bg-surface">
              <header className="border-b border-line px-5 py-4">
                <h2 className="text-lg font-bold tracking-tight">{shortId(sp.incident_id)}</h2>
                <p className="mt-1 text-sm text-muted">{eventLabel(sp.event_type)}</p>
              </header>
              <div className="p-5">
                <KeyValue
                  rows={[
                    ["Severity", <SeverityBadge key="s" value={sp.severity} />],
                    ["Risk score", `${Math.round(sp.risk_score)} of 100`],
                    ["Object", sp.object_class],
                    ["Camera", sp.camera_label || "Not named"],
                    ["Processed", formatDateTime(sp.created_at)],
                    ["Position", `${selected.geometry.coordinates[1].toFixed(5)}, ${selected.geometry.coordinates[0].toFixed(5)}`],
                  ]}
                />
                <Link to={`/incidents/${sp.incident_id}`} className={`${btn.primary} mt-4 w-full`}>
                  Open incident and clip
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
              </div>
            </section>
          )}
        </aside>
      )}
    </div>
  );
}
