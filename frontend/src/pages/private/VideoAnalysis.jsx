import { useEffect, useRef, useState } from "react";
import { uploadVideo, assignVideoZone, getVideo, getAnnotatedVideoUrl, getIncidentSnapshotUrl } from "../../api/videos.js";
import TrainLoader from "../../components/video/TrainLoader.jsx";

const ACCEPTED_EXT = [".mp4", ".avi", ".mov"];

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(sec) {
  if (!Number.isFinite(sec)) return "--:--";
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(Math.floor(sec % 60)).padStart(2, "0");
  return `${m}:${s}`;
}

function fmtTime(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(Math.floor(sec % 60)).padStart(2, "0");
  return `${m}:${s}`;
}

function fmtPct(v) {
  return `${Math.round(v <= 1 ? v * 100 : v)}%`;
}

function sevClass(sev) {
  const s = (sev || "").toUpperCase();
  if (s === "HIGH" || s === "CRITICAL") return "bg-danger/15 text-danger animate-pulse";
  if (s === "MEDIUM" || s === "MED") return "bg-amber-500/15 text-amber-300";
  return "bg-emerald-500/15 text-emerald-300";
}

export default function VideoAnalysis() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [meta, setMeta] = useState(null);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [points, setPoints] = useState([]); // normalized 0..1 relative to the video frame
  const [drawing, setDrawing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [videoId, setVideoId] = useState(null);
  const [job, setJob] = useState(null);
  const [selected, setSelected] = useState(null);
  const inputRef = useRef(null);
  const evidenceRef = useRef(null);

  const zoneReady = !drawing && points.length >= 3;
  const analysisStarted = Boolean(videoId);
  const awaitingZone = job?.status === "awaiting_zone";
  const finished = job?.status === "done" || job?.status === "failed";
  const incidents = [...(job?.incidents ?? [])].sort((a, b) => b.risk_score - a.risk_score);
  const highRisk = incidents.filter((i) => ["HIGH", "CRITICAL"].includes((i.severity || "").toUpperCase())).length;
  const maxRisk = incidents.reduce((m, i) => Math.max(m, i.risk_score), 0);

  // Poll the backend until the video is done or failed
  useEffect(() => {
    if (!videoId || finished) return;
    const timer = setInterval(async () => {
      try {
        setJob(await getVideo(videoId));
      } catch (e) {
        setError(`Lost connection to the server: ${e.message}`);
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [videoId, finished]);

  async function handleAnalyze() {
    setError("");
    setSubmitting(true);
    try {
      const zone = zoneReady
        ? points.map((p) => [Math.round(p.x * meta.width), Math.round(p.y * meta.height)])
        : null;
      const created = await uploadVideo(file, zone);
      setVideoId(created.id);
      setJob(created);
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : e.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAssignZone() {
    if (!videoId || !zoneReady || !meta) return;
    setError("");
    setSubmitting(true);
    try {
      const zone = points.map((p) => [Math.round(p.x * meta.width), Math.round(p.y * meta.height)]);
      const updated = await assignVideoZone(videoId, zone);
      setJob(updated);
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : e.message);
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function handleFile(f) {
    if (!f) return;
    const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPTED_EXT.includes(ext)) {
      setError("Unsupported file. Please upload an MP4, AVI or MOV video.");
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
      setSelected(null);
      setSubmitting(false);
      setFile(null);
      setMeta(null);
      setPreviewFailed(false);
      setError("");
      setPoints([]);
      setDrawing(false);
      if (inputRef.current) inputRef.current.value = "";
    }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files?.[0]);
  }

  function startDrawing() {
    setPoints([]);
    setDrawing(true);
  }

  function addPoint(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    const y = Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height));
    setPoints((p) => [...p, { x, y }]);
  }

  function undoPoint() {
    setPoints((p) => p.slice(0, -1));
  }

  function clearZone() {
    setPoints([]);
    setDrawing(false);
  }

  function finishZone() {
    if (points.length >= 3) setDrawing(false);
  }

  const polyPoints = points.map((p) => `${p.x * 100},${p.y * 100}`).join(" ");

  const rows = file
    ? [
        ["File", file.name],
        ["Size", formatSize(file.size)],
        ["Duration", meta ? formatDuration(meta.duration) : "--:--"],
        ["Resolution", meta ? `${meta.width} × ${meta.height}` : "--"],
        ["Format", file.name.split(".").pop().toUpperCase()],
      ]
    : [];

  return (
    <div>
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="mb-8">
          <div className="text-xs font-mono text-accent mb-2">
            VIDEO ANALYSIS
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">
            Analyze railway footage
          </h1>
          <p className="mt-2 text-white/60 max-w-md">
            Upload a track video, then define the safety zone to start
            detection.
          </p>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.avi,.mov,video/mp4,video/quicktime,video/x-msvideo"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />

        {!file ? (
          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`cursor-pointer rounded-2xl border-2 border-dashed p-16 text-center shadow-none transition-all duration-200 ${
              dragging
                ? "border-accent bg-emerald-500/15 scale-[1.01]"
                : "border-accent/60/60 bg-surface hover:border-accent"
            }`}
          >
            <div className="mx-auto w-14 h-14 rounded-full bg-canvas flex items-center justify-center text-accent">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                className="w-6 h-6"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <path d="M17 8l-5-5-5 5" />
                <path d="M12 3v12" />
              </svg>
            </div>
            <div className="mt-5 text-lg font-semibold text-ink">
              Drag &amp; drop a video here
            </div>
            <p className="mt-1 text-sm text-muted">
              or click to browse · MP4, AVI, MOV
            </p>
          </div>
        ) : (
          <div className="grid lg:grid-cols-5 gap-6">
            {/* Video 60% */}
            <div className="lg:col-span-3 rounded-2xl border border-white/10 bg-black/40 overflow-hidden shadow-2xl">
              <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 text-xs font-mono text-white/50">
                <span>{drawing ? "DRAWING SAFETY ZONE" : "PREVIEW"}</span>
                <span className="truncate max-w-[60%]">{file.name}</span>
              </div>

              {/* Frame matches the video's aspect ratio so zone points map exactly onto the video */}
              <div
                className="relative bg-black"
                style={{
                  aspectRatio: meta
                    ? `${meta.width} / ${meta.height}`
                    : "16 / 9",
                }}
              >
                {previewFailed ? (
                  <div className="absolute inset-0 flex items-center justify-center text-center px-8 text-sm text-white/60">
                    This browser can&apos;t preview{" "}
                    {file.name.split(".").pop().toUpperCase()} files, so the
                    safety zone can&apos;t be drawn here. Convert to MP4 to
                    continue.
                  </div>
                ) : (
                  previewUrl && (
                    <video
                      src={previewUrl}
                      controls={!drawing}
                      className="absolute inset-0 w-full h-full"
                      onLoadedMetadata={(e) =>
                        setMeta({
                          duration: e.currentTarget.duration,
                          width: e.currentTarget.videoWidth,
                          height: e.currentTarget.videoHeight,
                        })
                      }
                      onError={() => setPreviewFailed(true)}
                    />
                  )
                )}

                {/* Zone overlay */}
                {!previewFailed && (
                  <div
                    className={`absolute inset-0 ${drawing ? "cursor-crosshair" : "pointer-events-none"}`}
                    onClick={drawing ? addPoint : undefined}
                  >
                    <svg
                      viewBox="0 0 100 100"
                      preserveAspectRatio="none"
                      className="absolute inset-0 w-full h-full"
                    >
                      {points.length >= 2 &&
                        (zoneReady ? (
                          <polygon
                            points={polyPoints}
                            fill="rgba(225,29,72,0.18)"
                            stroke="#E11D48"
                            strokeWidth="2"
                            strokeDasharray="6 4"
                            vectorEffect="non-scaling-stroke"
                          />
                        ) : (
                          <polyline
                            points={polyPoints}
                            fill="none"
                            stroke="#E11D48"
                            strokeWidth="2"
                            strokeDasharray="6 4"
                            vectorEffect="non-scaling-stroke"
                          />
                        ))}
                    </svg>
                    {points.map((p, i) => (
                      <span
                        key={i}
                        className="absolute w-3 h-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-danger ring-2 ring-white"
                        style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%` }}
                      />
                    ))}
                    {drawing && points.length === 0 && (
                      <div className="absolute inset-x-0 top-4 text-center text-xs font-mono text-white/80">
                        Click on the video to place zone corners
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Details 40% */}
            <div className="lg:col-span-2 rounded-2xl bg-surface text-ink p-6 shadow-none border border-line flex flex-col">
              <div className="flex items-center justify-between mb-5">
                <h3 className="font-semibold">Video details</h3>
                <span className="text-xs font-mono text-emerald-300">
                  UPLOADED
                </span>
              </div>
              <dl className="space-y-3">
                {rows.map(([k, v]) => (
                  <div
                    key={k}
                    className="flex items-center justify-between rounded-2xl bg-surface-2 border border-line px-4 py-3"
                  >
                    <dt className="text-sm text-muted">{k}</dt>
                    <dd className="text-sm font-mono font-medium truncate max-w-[60%]">
                      {v}
                    </dd>
                  </div>
                ))}
              </dl>

              {/* Safety zone */}
              <div className="mt-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">Safety zone</h3>
                  <span
                    className={`text-xs font-mono ${
                      zoneReady
                        ? "text-emerald-300"
                        : drawing
                          ? "text-danger"
                          : "text-muted/80"
                    }`}
                  >
                    {zoneReady ? "READY" : drawing ? "DRAWING" : "NOT SET"} ·{" "}
                    {points.length} pts
                  </span>
                </div>

                {!drawing ? (
                  <button
                    onClick={startDrawing}
                    disabled={previewFailed}
                    className="w-full rounded-full bg-accent text-white font-semibold px-5 py-3 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-40 disabled:hover:scale-100"
                  >
                    {points.length ? "Redraw zone" : "Draw safety zone"}
                  </button>
                ) : (
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      onClick={undoPoint}
                      disabled={!points.length}
                      className="rounded-full border border-line font-medium px-3 py-3 text-sm hover:bg-surface-2 active:scale-[0.98] transition-all duration-200 disabled:opacity-40"
                    >
                      Undo
                    </button>
                    <button
                      onClick={clearZone}
                      className="rounded-full border border-line font-medium px-3 py-3 text-sm hover:bg-surface-2 active:scale-[0.98] transition-all duration-200"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={finishZone}
                      disabled={points.length < 3}
                      className="rounded-full bg-accent text-white font-semibold px-3 py-3 text-sm hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-40 disabled:hover:scale-100"
                    >
                      Finish
                    </button>
                  </div>
                )}

                <p className="mt-3 text-xs text-muted leading-relaxed">
                  {drawing
                    ? "Click each corner of the danger area around the track. You need at least 3 points."
                    : zoneReady
                      ? "Zone saved. Redraw it any time before starting analysis."
                      : "Mark the track corridor RailVigil should watch."}
                </p>

                {points.length > 0 && (
                  <div className="mt-3 rounded-2xl bg-surface-2 border border-line px-4 py-3 text-[11px] font-mono text-muted leading-relaxed max-h-24 overflow-auto">
                    {points.map((p, i) => (
                      <div key={i}>
                        P{i + 1}: {p.x.toFixed(3)}, {p.y.toFixed(3)}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Start analysis + status */}
              <div className="mt-6">
                {!analysisStarted ? (
                  <div className="space-y-2">
                    <button
                      onClick={handleAnalyze}
                      disabled={!meta || submitting}
                      className="w-full rounded-full bg-tactical-dark text-white font-semibold px-5 py-3 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-40 disabled:hover:scale-100"
                    >
                      {submitting
                        ? "Uploading…"
                        : zoneReady
                          ? "Start analysis"
                          : "Upload without zone"}
                    </button>
                    {!zoneReady && (
                      <p className="text-xs text-tactical-dark/50 text-center">
                        You can draw the zone now or after upload.
                      </p>
                    )}
                  </div>
                ) : awaitingZone ? (
                  <button
                    onClick={handleAssignZone}
                    disabled={!zoneReady || !meta || submitting}
                    className="w-full rounded-full bg-accent text-white font-semibold px-5 py-3 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-40 disabled:hover:scale-100"
                  >
                    {submitting ? "Saving zone…" : "Save zone & start analysis"}
                  </button>
                ) : (
                  <div className="rounded-2xl bg-surface-2 border border-line p-4">
                    <div
                      className={`flex items-center mb-3 ${
                        finished ? "justify-between" : "justify-center"
                      }`}
                    >
                      <h3 className="font-semibold text-sm">Analysis status</h3>
                      <span
                        className={`text-xs font-mono ${
                          job?.status === "failed"
                            ? "text-danger"
                            : job?.status === "done"
                              ? "text-emerald-300"
                              : "text-muted animate-[pulse_3s_ease-in-out_infinite]"
                        }`}
                      >
                        {finished ? job.status.toUpperCase() : ""}
                      </span>
                    </div>
                    {!finished && (
                      <div className="mb-4">
                        <TrainLoader />
                      </div>
                    )}
                    <ul className="space-y-2 text-sm font-mono">
                      {[
                        ["queued", "Video uploaded, waiting in queue"],
                        ["processing", "Detecting and tracking"],
                        ["done", "Incidents confirmed"],
                      ].map(([key, label]) => {
                        // Backend lifecycle: queued -> processing -> done | failed
                        const order = {
                          queued: 0,
                          processing: 1,
                          done: 2,
                          failed: 1,
                        };
                        const cur = order[job?.status ?? "queued"];
                        const mine = order[key];
                        const state =
                          mine < cur || job?.status === "done"
                            ? "done"
                            : mine === cur
                              ? "active"
                              : "todo";
                        return (
                          <li key={key} className="flex items-center gap-2">
                            <span
                              className={`w-2.5 h-2.5 rounded-full ${
                                state === "done"
                                  ? "bg-emerald-500"
                                  : state === "active" &&
                                      job?.status === "failed"
                                    ? "bg-danger"
                                    : state === "active"
                                      ? "bg-emerald-400 animate-[pulse_3s_ease-in-out_infinite]"
                                      : "bg-surface-2"
                              }`}
                            />
                            <span
                              className={
                                state === "todo" ? "text-muted/80" : ""
                              }
                            >
                              {label}
                              {/* live percentage while this step is running */}
                              {key === "processing" &&
                                state === "active" &&
                                job?.status === "processing" &&
                                ` ${Math.round(job.progress ?? 0)}%`}
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                    {job?.status === "failed" && (
                      <p className="mt-3 text-xs font-mono text-danger break-words">
                        {(job.error || "Processing failed").split("\n")[0]}
                      </p>
                    )}
                  </div>
                )}
              </div>

              <button
                onClick={handleRemove}
                className="mt-6 rounded-full border border-line text-ink font-medium px-5 py-3 hover:bg-surface-2 active:scale-[0.98] transition-all duration-200"
              >
                Choose a different video
              </button>
            </div>
          </div>
        )}

                {job?.status === "done" && (
          <div className="mt-6 space-y-6">
            {/* Metric cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                ["Confirmed incidents", incidents.length],
                ["High-risk events", highRisk],
                ["Max risk score", Math.round(maxRisk)],
                ["Video duration", meta ? formatDuration(meta.duration) : "--:--"],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl bg-surface text-ink p-6 shadow-none border border-line">
                  <div className="text-3xl font-semibold font-mono">{value}</div>
                  <div className="mt-1 text-sm text-muted">{label}</div>
                </div>
              ))}
            </div>

            {/* 60/40: annotated video + evidence */}
            <div className="grid lg:grid-cols-5 gap-6">
              <div className="lg:col-span-3 rounded-2xl border border-white/10 bg-black/40 overflow-hidden shadow-2xl">
                <div className="px-5 py-3 border-b border-white/10 text-xs font-mono text-white/50">
                  ANNOTATED OUTPUT
                </div>
                <video src={getAnnotatedVideoUrl(videoId)} controls className="w-full bg-black" />
              </div>

              <div
                ref={evidenceRef}
                className="lg:col-span-2 rounded-2xl bg-surface text-ink p-6 shadow-none border border-line scroll-mt-24"
              >
                <h3 className="font-semibold mb-4">Evidence</h3>
                {!selected ? (
                  <p className="text-sm text-muted">
                    Select an incident from the table below to see its snapshot and details.
                  </p>
                ) : (
                  <div>
                    <div className="rounded-2xl overflow-hidden bg-black aspect-video flex items-center justify-center">
                      <img
                        key={selected.id}
                        src={getIncidentSnapshotUrl(selected.id)}
                        alt={`Evidence for track ${selected.track_id}`}
                        className="w-full h-full object-contain"
                        onError={(e) => {
                          e.currentTarget.style.display = "none";
                          e.currentTarget.nextSibling.style.display = "block";
                        }}
                      />
                      <span style={{ display: "none" }} className="text-xs font-mono text-white/60 px-4 text-center">
                        No snapshot available
                      </span>
                    </div>
                    <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                      {[
                        ["Object", `${selected.object_class} #${selected.track_id}`],
                        ["Event", selected.event_type],
                        ["Window", `${fmtTime(selected.start_ts)} – ${fmtTime(selected.end_ts)}`],
                        ["Dwell", `${selected.dwell_time_sec.toFixed(1)}s`],
                        ["Max penetration", fmtPct(selected.max_penetration)],
                        ["Risk score", Math.round(selected.risk_score)],
                      ].map(([k, v]) => (
                        <div key={k} className="rounded-2xl bg-surface-2 border border-line px-3 py-2">
                          <dt className="text-[11px] text-muted">{k}</dt>
                          <dd className="font-mono font-medium truncate">{v}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                )}
              </div>
            </div>

            {/* Incident table */}
            <div className="rounded-2xl bg-surface text-ink p-6 shadow-none border border-line">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Confirmed incidents</h3>
                <span className="text-xs font-mono text-emerald-300">{incidents.length} total · sorted by risk</span>
              </div>
              {incidents.length === 0 ? (
                <p className="text-sm text-muted">
                  No confirmed incidents. Nothing stayed in the safety zone long enough to count.
                </p>
              ) : (
                <div className="max-h-96 overflow-auto rounded-2xl bg-surface-2 border border-line">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-surface-2 text-left text-[11px] font-mono text-muted">
                      <tr>
                        {["TIME", "OBJECT", "TYPE", "DWELL", "PENETRATION", "RISK", "SEVERITY", ""].map((h) => (
                          <th key={h} className="px-4 py-3 font-normal">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="font-mono">
                      {incidents.map((i) => (
                        <tr
                          key={i.id}
                          onClick={() => {
                            setSelected(i);
                            evidenceRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
                          }}
                          className={`cursor-pointer border-t border-line hover:bg-surface-2 transition-all duration-200 ${
                            selected?.id === i.id ? "bg-emerald-500/15" : ""
                          }`}
                        >
                          <td className="px-4 py-3">{fmtTime(i.start_ts)}</td>
                          <td className="px-4 py-3">{i.object_class} #{i.track_id}</td>
                          <td className="px-4 py-3">{i.event_type}</td>
                          <td className="px-4 py-3">{i.dwell_time_sec.toFixed(1)}s</td>
                          <td className="px-4 py-3">{fmtPct(i.max_penetration)}</td>
                          <td className="px-4 py-3">{Math.round(i.risk_score)}</td>
                          <td className="px-4 py-3">
                            <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${sevClass(i.severity)}`}>
                              {(i.severity || "").toUpperCase()}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-emerald-300">View</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-6 rounded-2xl bg-danger/15 text-danger text-sm font-mono px-5 py-3">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}