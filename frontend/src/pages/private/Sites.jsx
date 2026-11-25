import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { MapPinned } from "lucide-react";
import { listSites } from "../../api/encroachment.js";
import CasePanel from "../../components/encroachment/CasePanel.jsx";
import PlanMap from "../../components/plan/PlanMap.jsx";
import {
  EmptyState,
  ErrorBanner,
  FilterChips,
  Pagination,
  SeverityBadge,
  SkeletonRows,
  StatusBadge,
  Table,
  btn,
  cellClass,
  selectClass,
} from "../../components/ui/index.jsx";
import { CLASS_LABEL, STATUS_LABEL, classLabel, shortSite } from "../../utils/encroachmentFormat.js";
import { SEVERITIES, SEVERITY_COLOR, SEVERITY_LABEL, normaliseSeverity } from "../../utils/severity.js";
import { formatDateTime, timeAgo } from "../../utils/formatDate.js";

const PAGE = 8;
const OPEN_STATUSES = "reported,under_review,verified,action_taken";
const SEVERITY_OPTIONS = SEVERITIES.map((s) => [s, SEVERITY_LABEL[s]]);
const located = (s) => s.latitude != null && s.longitude != null;

function Disc({ site }) {
  return (
    <span
      className="grid h-[22px] w-[22px] shrink-0 place-items-center rounded-full text-[11px] font-bold text-white"
      style={{ background: SEVERITY_COLOR[normaliseSeverity(site.max_severity)] }}
      aria-hidden
    >
      {site.number}
    </span>
  );
}

// The register and the plan are one thing: each row carries the number of its
// mark, and selecting either selects both. Filters live in the URL.
export default function Sites() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const openOnly = params.get("all") !== "1";
  const severity = params.get("severity") || "";
  const cls = params.get("class") || "";
  const offset = Number(params.get("offset")) || 0;

  const [sites, setSites] = useState(null);
  const [error, setError] = useState("");
  // The site the reader chose. Until they choose, the first row is shown and the plan holds the whole sheet.
  const [chosenId, setChosenId] = useState(null);

  const update = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    if (!("offset" in changes)) next.delete("offset");
    setChosenId(null);
    setParams(next, { replace: true });
  };

  useEffect(() => {
    let cancelled = false;
    setSites(null);
    setError("");
    listSites({ status: openOnly ? OPEN_STATUSES : undefined, severity: severity || undefined, cls: cls || undefined })
      .then((s) => !cancelled && setSites(s))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [openOnly, severity, cls]);

  const loading = sites === null && !error;
  const rows = useMemo(() => (sites || []).slice(offset, offset + PAGE).map((s, i) => ({ ...s, number: i + 1 })), [sites, offset]);
  const marks = useMemo(
    () =>
      rows.filter(located).map((s) => ({
        id: s.id,
        number: s.number,
        lat: s.latitude,
        lon: s.longitude,
        severity: s.max_severity,
        label: `${shortSite(s.id)}, ${classLabel(s.cls)}, ${SEVERITY_LABEL[normaliseSeverity(s.max_severity)]}`,
      })),
    [rows],
  );
  const others = useMemo(() => {
    const onSheet = new Set(rows.map((r) => r.id));
    return (sites || []).filter((s) => located(s) && !onSheet.has(s.id)).map((s) => ({ id: s.id, lat: s.latitude, lon: s.longitude }));
  }, [sites, rows]);

  const selected = rows.find((s) => s.id === chosenId) || rows[0] || null;
  const critical = (sites || []).filter((s) => normaliseSeverity(s.max_severity) === "critical").length;
  const empty = !loading && !error && rows.length === 0;
  const active = [
    !openOnly && "closed sites included",
    severity && `severity ${severity.split(",").map((s) => SEVERITY_LABEL[s]).join(" or ")}`,
    cls && `class ${CLASS_LABEL[cls]}`,
  ].filter(Boolean);
  const choose = (id) => setChosenId(id);

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div>
          <h1 className="text-[32px] font-bold leading-none tracking-tight">Encroachment sites</h1>
          <p className="mt-1.5 text-sm text-canvas-muted">
            {loading ? "Loading the register" : `${sites?.length ?? 0} ${openOnly ? "open " : ""}sites · ${critical} critical · findings of one kind within 25 m form a site`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <FilterChips label="Show" single options={[["open", "Open only"]]} value={openOnly ? "open" : ""} onChange={(v) => update({ all: v ? "" : "1" })} />
          <FilterChips label="Severity" options={SEVERITY_OPTIONS} value={severity ? severity.split(",") : []} onChange={(v) => update({ severity: v.join(",") })} />
          <select aria-label="Class" className={`${selectClass} !h-8 text-xs`} value={cls} onChange={(e) => update({ class: e.target.value })}>
            <option value="">All classes</option>
            {Object.entries(CLASS_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorBanner>The register could not be loaded ({error}). Check that the backend is running, then reload.</ErrorBanner>}

      {empty ? (
        <section className="border-2 border-rule bg-surface" aria-label="Site register">
          <EmptyState
            icon={MapPinned}
            title="No sites match these filters"
            action={
              active.length > 0 && (
                <button type="button" className={`${btn.secondary} ${btn.small}`} onClick={() => setParams({}, { replace: true })}>
                  Clear filters
                </button>
              )
            }
          >
            {active.length > 0
              ? `Filters in use: ${active.join(", ")}.`
              : "A site appears here when an analysed photo shows an encroachment on marked railway land."}
          </EmptyState>
        </section>
      ) : (
        <>
          {!error && (
            <PlanMap
              marks={marks}
              others={others}
              selectedId={selected?.id}
              focusId={chosenId}
              onSelect={choose}
              onFitAll={() => setChosenId(null)}
              sheet={sites?.length ? { page: Math.floor(offset / PAGE) + 1, pages: Math.ceil(sites.length / PAGE), total: sites.length, onSheet: rows.length } : null}
            />
          )}

          <div className="mt-4 grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
            <section className="order-2 min-w-0 border-2 border-rule bg-surface lg:order-1" aria-label="Site register">
              {/* Wide screens: the ruled register */}
              <div className="hidden sm:block">
                <Table head={["Site", "Class", "Severity", "Stage", "Finds", "Latest report", "Last seen"]}>
                  {loading ? (
                    <SkeletonRows rows={PAGE} cols={7} />
                  ) : (
                    rows.map((s) => {
                      const on = s.id === selected?.id;
                      return (
                        <tr
                          key={s.id}
                          onClick={() => choose(s.id)}
                          onDoubleClick={() => navigate(`/sites/${s.id}`)}
                          aria-selected={on}
                          className={`cursor-pointer transition-colors ${on ? "bg-wash" : "hover:bg-canvas-2"}`}
                        >
                          <td className={cellClass}>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                choose(s.id);
                              }}
                              className="flex items-center gap-2.5 font-semibold"
                              aria-label={`Select ${shortSite(s.id)} and show it on the plan`}
                            >
                              <Disc site={s} />
                              {shortSite(s.id)}
                            </button>
                          </td>
                          <td className={cellClass}>{classLabel(s.cls)}</td>
                          <td className={cellClass}>
                            <SeverityBadge value={s.max_severity} />
                          </td>
                          <td className={cellClass}>
                            <StatusBadge value={s.status} />
                          </td>
                          <td className={`${cellClass} tabular`}>{s.finding_count}</td>
                          <td className={cellClass}>{s.latest_report_no || "–"}</td>
                          <td className={`${cellClass} text-muted`}>{formatDateTime(s.last_reported_at)}</td>
                        </tr>
                      );
                    })
                  )}
                </Table>
              </div>

              {/* Small screens: two-line rows, so the severity word is always in view */}
              <ul className="divide-y divide-line sm:hidden">
                {loading
                  ? Array.from({ length: PAGE }, (_, i) => (
                      <li key={i} className="px-4 py-3">
                        <span className="skeleton block h-4 w-40" />
                        <span className="skeleton mt-2 block h-3 w-56" />
                      </li>
                    ))
                  : rows.map((s) => {
                      const on = s.id === selected?.id;
                      return (
                        <li key={s.id}>
                          <button type="button" onClick={() => choose(s.id)} aria-pressed={on} className={`block w-full px-4 py-3 text-left ${on ? "bg-wash" : ""}`}>
                            <span className="flex items-center gap-2.5">
                              <Disc site={s} />
                              <span className="font-semibold">{shortSite(s.id)}</span>
                              <SeverityBadge value={s.max_severity} className="ml-auto" />
                            </span>
                            <span className="mt-1 block pl-[32px] text-xs text-muted">
                              {classLabel(s.cls)} · {STATUS_LABEL[s.status]} · {s.finding_count} {s.finding_count === 1 ? "find" : "finds"} · {timeAgo(s.last_reported_at)}
                            </span>
                          </button>
                        </li>
                      );
                    })}
              </ul>

              {sites && sites.length > PAGE && (
                <Pagination offset={offset} limit={PAGE} total={sites.length} onChange={(o) => update({ offset: o ? String(o) : "" })} />
              )}
            </section>

            <div className="order-1 lg:order-2">{!loading && <CasePanel site={selected} />}</div>
          </div>
        </>
      )}
    </>
  );
}
