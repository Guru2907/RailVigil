import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Check, CircleAlert, ImageOff, Loader2, UploadCloud } from "lucide-react";
import { uploadVideo, assignVideoZone, getVideo, getAnnotatedVideoUrl, getIncidentSnapshotUrl } from "../../api/videos.js";
import { Card, ErrorBanner, KeyValue, PageHeader, SeverityBadge, Table, btn, cellClass, inputClass } from "../../components/ui/index.jsx";
import { eventLabel, fmtPct, fmtTime, shortId } from "../../utils/incidentFormat.js";

const ACCEPTED_EXT = [".mp4", ".avi", ".mov"];
const POLL_MS = 2000;
// Railway land is always the pink wash with a dashed edge, on photos and on video.
const WASH = "rgba(241, 210, 206, 0.45)";
const WASH_EDGE = "#b8321f";

const STEPS = [
  ["queued", "Video uploaded, waiting in the queue"],
  ["processing", "Detecting and tracking"],
  ["done", "Incidents confirmed"],
];
const STEP_ORDER = { queued: 0, processing: 1, done: 2, failed: 1 };

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(sec) {
  return Number.isFinite(sec) ? fmtTime(sec) : "Not known";
}

function errorText(e) {
  const detail = e?.response?.data?.detail;
  return typeof detail === "string" ? detail : e.message;
}

// The uploaded frame with the track zone drawn on it as railway land.
function ZoneFrame({ file, previewUrl, meta, previewFailed, drawing, points, closed, onPoint, onMeta, onFail }) {
  const poly = points.map((p) => `${p.x * 100},${p.y * 100}`).join(" ");
  const Shape = closed ? "polygon" : "polyline";
  const ratio = meta ? meta.width / meta.height : 16 / 9;
  // A tall clip is narrowed so the whole frame stays on screen while the zone is drawn.
  return (
    <div className="bg-ink">
    <div className="relative mx-auto" style={{ aspectRatio: String(ratio), width: `min(100%, calc(70vh * ${ratio}))` }}>
      {previewFailed ? (
        <p className="absolute inset-0 flex items-center justify-center px-8 text-center text-sm text-surface">
          This browser cannot play {file.name.split(".").pop().toUpperCase()} files, so the track zone cannot be drawn here. Convert the video to MP4 to
          continue.
        </p>
      ) : (
        previewUrl && (
          <video
            src={previewUrl}
            controls={!drawing}
            className="absolute inset-0 h-full w-full"
            onLoadedMetadata={(e) => onMeta({ duration: e.currentTarget.duration, width: e.currentTarget.videoWidth, height: e.currentTarget.videoHeight })}
            onError={onFail}
          />
        )
      )}
      {!previewFailed && (
        <div className={`absolute inset-0 ${drawing ? "cursor-crosshair" : "pointer-events-none"}`} onClick={drawing ? onPoint : undefined}>
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full" aria-hidden>
            {points.length >= 2 && (
              <Shape points={poly} fill={closed ? WASH : "none"} stroke={WASH_EDGE} strokeWidth="2" strokeDasharray="6 4" vectorEffect="non-scaling-stroke" />
            )}
          </svg>
          {points.map((p, i) => (
            <span
              key={i}
              className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 border-2 border-surface bg-wash-edge"
              style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%` }}
            />
          ))}
          {drawing && points.length === 0 && (
            <p className="absolute inset-x-0 top-4 text-center text-sm font-semibold text-surface [text-shadow:0_1px_2px_#000]">
              Click on the video to place the corners of the track zone
            </p>
          )}
        </div>
      )}
    </div>
    </div>
  );
}

// Where the job is: three plain steps and, while it runs, a progress line.
function JobStatus({ job }) {
  const failed = job?.status === "failed";
  const done = job?.status === "done";
  const cur = STEP_ORDER[job?.status ?? "queued"];
  const percent = Math.round(job?.progress ?? 0);
  return (
    <div role="status" aria-live="polite">
      <ol className="space-y-2.5 text-sm">
        {STEPS.map(([key, label]) => {
          const mine = STEP_ORDER[key];
          const state = done || mine < cur ? "done" : mine === cur ? (failed ? "failed" : "active") : "todo";
          const Icon = state === "done" ? Check : state === "failed" ? CircleAlert : state === "active" ? Loader2 : null;
          return (
            <li key={key} className={`flex items-center gap-2.5 ${state === "todo" ? "text-muted" : state === "failed" ? "text-sev-critical" : "text-ink"}`}>
              <span className="flex h-5 w-5 shrink-0 items-center justify-center border border-rule bg-paper">
                {Icon && <Icon className={`h-3.5 w-3.5 ${state === "active" ? "animate-spin motion-reduce:animate-none" : ""}`} aria-hidden />}
              </span>
              <span className={state === "active" ? "font-semibold" : ""}>
                {label}
                {key === "processing" && state === "active" && job?.status === "processing" && <span className="tabular"> · {percent}%</span>}
              </span>
            </li>
          );
        })}
      </ol>
      {job?.status === "processing" && (
        <div className="mt-4 h-1.5 bg-canvas-2" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label="Analysis progress">
          <div className="h-full origin-left bg-pop transition-transform duration-500" style={{ transform: `scaleX(${percent / 100})` }} />
        </div>
      )}
      {failed && <p className="mt-3 break-words text-sm text-sev-critical">{(job.error || "Processing failed").split("\n")[0]}</p>}
    </div>
  );
}

function Snapshot({ incident }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div className="flex aspect-video flex-col items-center justify-center gap-2 border border-line bg-paper text-sm text-muted">
        <ImageOff className="h-5 w-5" aria-hidden />
        No frame was saved for this incident.
      </div>
    );
  }
  return (
    <img
      src={getIncidentSnapshotUrl(incident.id)}
      alt={`Saved frame of ${shortId(incident.id)}`}
      className="aspect-video w-full border border-rule bg-ink object-contain"
      onError={() => setFailed(true)}
    />
  );
}

export default function VideoAnalysis() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [meta, setMeta] = useState(null);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [points, setPoints] = useState([]); // 0..1 relative to the video frame
  const [drawing, setDrawing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [videoId, setVideoId] = useState(null);
  const [job, setJob] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const inputRef = useRef(null);

  const zoneReady = !drawing && points.length >= 3;
  const analysisStarted = Boolean(videoId);
  const awaitingZone = job?.status === "awaiting_zone";
  const finished = job?.status === "done" || job?.status === "failed";
  const incidents = [...(job?.incidents ?? [])].sort((a, b) => b.risk_score - a.risk_score);
  const selected = incidents.find((i) => i.id === selectedId) || incidents[0] || null;

  // Poll the backend until the video is done or failed.
  useEffect(() => {
    if (!videoId || finished) return undefined;
    const timer = setInterval(async () => {
      try {
        setJob(await getVideo(videoId));
      } catch (e) {
        setError(`Lost connection to the server: ${e.message}`);
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [videoId, finished]);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const zonePixels = () => points.map((p) => [Math.round(p.x * meta.width), Math.round(p.y * meta.height)]);

  async function handleAnalyze() {
    setError("");
    if ((lat === "") !== (lon === "")) return setError("Give both latitude and longitude, or neither.");
    setSubmitting(true);
    try {
      const created = await uploadVideo(file, zoneReady ? zonePixels() : null, undefined, { latitude: lat, longitude: lon });
      setVideoId(created.id);
      setJob(created);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSubmitting(false);
    }
    return undefined;
  }

  async function handleAssignZone() {
    if (!videoId || !zoneReady || !meta) return;
    setError("");
    setSubmitting(true);
    try {
      setJob(await assignVideoZone(videoId, zonePixels()));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSubmitting(false);
    }
  }

  function handleFile(f) {
    if (!f) return;
    const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPTED_EXT.includes(ext)) {
      setError("This file type is not supported. Choose an MP4, AVI or MOV video.");
      return;
    }
    setError("");
    setMeta(null);
    setPreviewFailed(false);
    setPoints([]);
    setDrawing(false);
    setFile(f);
  }

  function handleRemove() {
    setVideoId(null);
    setJob(null);
    setSelectedId(null);
    setSubmitting(false);
    setFile(null);
    setMeta(null);
    setPreviewFailed(false);
    setError("");
    setPoints([]);
    setDrawing(false);
    if (inputRef.current) inputRef.current.value = "";
  }

  function addPoint(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    const y = Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height));
    setPoints((p) => [...p, { x, y }]);
  }

  const fieldLabel = "mb-1.5 block text-[11px] font-semibold text-muted";
  const zoneState = zoneReady ? "Drawn" : drawing ? "Drawing" : "Not drawn";

  return (
    <>
      <PageHeader
        crumbs={[["Intrusion"], ["Video analysis"]]}
        title="Video analysis"
        description="Upload a CCTV clip and outline the track zone. RailVigil follows each person, vehicle and animal and records the ones that stay inside it."
      />

      {error && <ErrorBanner>{error}</ErrorBanner>}

      <input
        ref={inputRef}
        id="video-file"
        type="file"
        accept=".mp4,.avi,.mov,video/mp4,video/quicktime,video/x-msvideo"
        className="sr-only"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />

      {!file ? (
        <Card title="Upload a video" subtitle="MP4, AVI or MOV">
          <label
            htmlFor="video-file"
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              handleFile(e.dataTransfer.files?.[0]);
            }}
            className={`flex h-80 cursor-pointer flex-col items-center justify-center rounded-sm border-2 border-dashed transition-colors ${
              dragging ? "border-ink bg-surface-2" : "border-line bg-paper hover:border-ink/40"
            }`}
          >
            <UploadCloud className="h-10 w-10 text-muted" aria-hidden />
            <span className="mt-3 font-semibold">Drag a video here or click to browse</span>
            <span className="mt-1 text-sm text-muted">You outline the track zone on the first screen after this</span>
          </label>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          <Card
            className="lg:col-span-3"
            bodyClass="p-0"
            title={drawing ? "Outline the track zone" : "Video"}
            subtitle={
              drawing ? `Click each corner of the area around the track · ${points.length} placed, 3 needed` : file.name
            }
            action={
              !analysisStarted || awaitingZone ? (
                drawing ? (
                  <div className="flex gap-2">
                    <button type="button" onClick={() => setPoints((p) => p.slice(0, -1))} disabled={!points.length} className={`${btn.secondary} ${btn.small}`}>
                      Undo
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setPoints([]);
                        setDrawing(false);
                      }}
                      className={`${btn.secondary} ${btn.small}`}
                    >
                      Cancel
                    </button>
                    <button type="button" onClick={() => setDrawing(false)} disabled={points.length < 3} className={`${btn.primary} ${btn.small}`}>
                      Finish zone
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => {
                      setPoints([]);
                      setDrawing(true);
                    }}
                    disabled={previewFailed}
                    className={`${btn.secondary} ${btn.small}`}
                  >
                    {points.length ? "Redraw the zone" : "Draw the track zone"}
                  </button>
                )
              ) : null
            }
          >
            <ZoneFrame
              file={file}
              previewUrl={previewUrl}
              meta={meta}
              previewFailed={previewFailed}
              drawing={drawing}
              points={points}
              closed={zoneReady}
              onPoint={addPoint}
              onMeta={setMeta}
              onFail={() => setPreviewFailed(true)}
            />
          </Card>

          <Card className="lg:col-span-2" title="Analysis details" bodyClass="space-y-5 p-6">
            <KeyValue
              rows={[
                ["File", file.name],
                ["Size", formatSize(file.size)],
                ["Length", meta ? formatDuration(meta.duration) : "Reading"],
                ["Frame", meta ? `${meta.width} × ${meta.height}` : "Reading"],
                ["Track zone", `${zoneState}${points.length ? ` · ${points.length} corners` : ""}`],
              ]}
            />

            {!analysisStarted ? (
              <>
                <div>
                  <span className={fieldLabel}>Camera location (optional)</span>
                  <div className="grid grid-cols-2 gap-2">
                    <input aria-label="Latitude" className={inputClass} placeholder="Latitude" inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} />
                    <input aria-label="Longitude" className={inputClass} placeholder="Longitude" inputMode="decimal" value={lon} onChange={(e) => setLon(e.target.value)} />
                  </div>
                  <p className="mt-1.5 text-xs text-muted">Confirmed incidents appear on the GIS map at this point.</p>
                </div>
                <div>
                  <button type="button" onClick={handleAnalyze} disabled={!meta || submitting || drawing} className={`${btn.primary} w-full`}>
                    {submitting ? "Uploading" : zoneReady ? "Start the analysis" : "Upload without a zone"}
                  </button>
                  {!zoneReady && <p className="mt-2 text-xs text-muted">Without a zone the video waits; you can draw the zone after the upload.</p>}
                </div>
              </>
            ) : awaitingZone ? (
              <div>
                <button type="button" onClick={handleAssignZone} disabled={!zoneReady || !meta || submitting} className={`${btn.primary} w-full`}>
                  {submitting ? "Saving the zone" : "Save the zone and start the analysis"}
                </button>
                <p className="mt-2 text-xs text-muted">The video is uploaded and waits for its track zone.</p>
              </div>
            ) : (
              <JobStatus job={job} />
            )}

            <button type="button" onClick={handleRemove} className={`${btn.secondary} w-full`}>
              Choose a different video
            </button>
          </Card>
        </div>
      )}

      {job?.status === "done" && (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-5">
          <Card className="lg:col-span-3" bodyClass="p-0" title="Analysed video" subtitle="Track zone and every followed object drawn on the clip">
            <video src={getAnnotatedVideoUrl(videoId)} controls className="block w-full bg-ink" />
          </Card>

          <Card
            className="lg:col-span-2"
            title={selected ? shortId(selected.id) : "Result"}
            subtitle={selected ? eventLabel(selected.event_type) : undefined}
            action={selected && <SeverityBadge value={selected.severity} />}
          >
            {selected ? (
              <>
                <Snapshot key={selected.id} incident={selected} />
                <KeyValue
                  className="mt-3"
                  rows={[
                    ["Risk score", `${Math.round(selected.risk_score)} of 100`],
                    ["Object", `${selected.object_class}, track ${selected.track_id}`],
                    ["In the video at", `${fmtTime(selected.start_ts)} to ${fmtTime(selected.end_ts)}`],
                    ["Time in the zone", `${selected.dwell_time_sec.toFixed(1)} s`],
                    ["Deepest in the zone", fmtPct(selected.max_penetration)],
                  ]}
                />
                <Link to={`/incidents/${selected.id}`} className={`${btn.primary} mt-4 w-full`}>
                  Open incident and clip <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
              </>
            ) : (
              <p className="text-sm text-muted">Nothing stayed inside the track zone long enough to count as an incident.</p>
            )}
          </Card>

          {incidents.length > 0 && (
            <Card
              className="lg:col-span-5"
              bodyClass="p-0"
              title="Incidents in this video"
              subtitle={`${incidents.length} confirmed · highest risk first`}
            >
              <Table head={["Incident", "Event", "At", "In zone for", "Deepest", "Risk", "Severity"]}>
                {incidents.map((i) => {
                  const active = selected?.id === i.id;
                  return (
                    <tr key={i.id} className={active ? "bg-wash" : "hover:bg-canvas-2"}>
                      <td className={cellClass}>
                        <button type="button" onClick={() => setSelectedId(i.id)} aria-pressed={active} className="font-semibold underline-offset-4 hover:underline">
                          {shortId(i.id)}
                        </button>
                      </td>
                      <td className={cellClass}>{eventLabel(i.event_type)}</td>
                      <td className={`${cellClass} tabular`}>{fmtTime(i.start_ts)}</td>
                      <td className={`${cellClass} tabular`}>{i.dwell_time_sec.toFixed(1)} s</td>
                      <td className={`${cellClass} tabular`}>{fmtPct(i.max_penetration)}</td>
                      <td className={`${cellClass} tabular font-semibold`}>{Math.round(i.risk_score)}</td>
                      <td className={cellClass}>
                        <SeverityBadge value={i.severity} />
                      </td>
                    </tr>
                  );
                })}
              </Table>
            </Card>
          )}
        </div>
      )}
    </>
  );
}
