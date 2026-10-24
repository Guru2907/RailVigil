import { useEffect, useMemo, useState } from "react";
import { Check, Circle, Loader2, UploadCloud, X } from "lucide-react";
import { fileUrl, getPhoto, uploadPhotos } from "../../api/encroachment.js";
import ZoneCanvas from "../../components/encroachment/ZoneCanvas.jsx";
import FindingList from "../../components/encroachment/FindingList.jsx";
import { Card, ErrorBanner, PageHeader, Segmented, btn, inputClass } from "../../components/ui/index.jsx";
import { formatDateTime } from "../../utils/formatDate.js";

const POLL_MS = 2000;
const LOWER_PART = [
  [0, 0.55],
  [1, 0.55],
  [1, 1],
  [0, 1],
];
const LOCATION_TEXT = { exif: "GPS from photo", pin: "Map pin", none: "No location" };

function errorText(e) {
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; ");
  return e?.message || "Something went wrong";
}

// Pipeline steps derived from the job status the backend reports.
const STEPS = ["Uploaded", "Queued", "YOLO detection", "Zone & severity", "Recorded"];
function stepState(status, i) {
  const reached = { queued: 1, processing: 2, done: 5, failed: 2 }[status] ?? 0;
  if (status === "failed" && i === 2) return "failed";
  if (i < reached || (status === "done" && i <= 4)) return "done";
  if (i === reached) return "active";
  return "todo";
}

function Pipeline({ status }) {
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-2 text-xs">
      {STEPS.map((label, i) => {
        const s = stepState(status, i);
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={`flex items-center gap-1.5 rounded px-2 py-1 font-medium ${
                s === "done"
                  ? "bg-accent text-accent-ink"
                  : s === "active"
                    ? "bg-paper text-ink ring-1 ring-ink/30"
                    : s === "failed"
                      ? "bg-danger/10 text-danger"
                      : "text-muted"
              }`}
            >
              {s === "done" ? (
                <Check className="h-3.5 w-3.5" />
              ) : s === "active" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : s === "failed" ? (
                <X className="h-3.5 w-3.5" />
              ) : (
                <Circle className="h-3 w-3" />
              )}
              {label}
            </span>
            {i < STEPS.length - 1 && <span className="h-px w-3 bg-line" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}

function ResultCard({ photo }) {
  const [view, setView] = useState("after");
  const done = photo.status === "done";
  const src = done && view === "after" ? photo.annotated_url : photo.original_url;
  return (
    <Card
      title={photo.original_filename}
      subtitle={
        <span className="font-mono">
          {LOCATION_TEXT[photo.location_source]}
          {photo.latitude != null && ` · ${photo.latitude.toFixed(5)}, ${photo.longitude.toFixed(5)}`}
          {photo.captured_at && ` · taken ${formatDateTime(photo.captured_at)}`}
          {photo.duplicate && " · already uploaded earlier"}
        </span>
      }
      action={<Pipeline status={photo.status} />}
    >
      {photo.error && <ErrorBanner>{photo.error}</ErrorBanner>}
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <div className="overflow-hidden rounded-md border border-line bg-black">
            <div className="flex items-center justify-between border-b border-white/10 px-3 py-1.5 font-mono text-[10px] tracking-widest text-white/60">
              <span>{done && view === "after" ? "ANALYSED · ZONE + DETECTIONS" : "ORIGINAL"}</span>
              <span>
                {photo.width}×{photo.height}
              </span>
            </div>
            <img src={fileUrl(src)} alt={photo.original_filename} className="block w-full" />
          </div>
          {done && (
            <div className="mt-3">
              <Segmented
                options={[
                  ["before", "Before"],
                  ["after", "After"],
                ]}
                value={view}
                onChange={setView}
                label="Image view"
              />
            </div>
          )}
        </div>
        <div className="lg:col-span-2">
          <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-muted">
            Findings {done && `· ${photo.findings?.length ?? 0}`}
          </h3>
          {done ? (
            <div className="[&_ul]:grid-cols-1">
              <FindingList findings={photo.findings} />
            </div>
          ) : (
            <p className="text-sm text-muted">{photo.status === "failed" ? "Analysis failed." : "Analysing…"}</p>
          )}
        </div>
      </div>
    </Card>
  );
}

export default function PhotoUpload() {
  const [files, setFiles] = useState([]);
  const [points, setPoints] = useState([]);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);
  const [dragging, setDragging] = useState(false);

  const preview = useMemo(() => (files[0] ? URL.createObjectURL(files[0]) : null), [files]);
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  // Poll photos that are still being analysed.
  const pendingKey = results
    .filter((r) => r.status === "queued" || r.status === "processing")
    .map((r) => r.id)
    .join(",");
  useEffect(() => {
    if (!pendingKey) return;
    const t = setInterval(async () => {
      const fresh = await Promise.all(pendingKey.split(",").map((id) => getPhoto(id).catch(() => null)));
      setResults((prev) =>
        prev.map((r) => {
          const f = fresh.find((x) => x && x.id === r.id);
          return f ? { ...f, duplicate: r.duplicate } : r;
        }),
      );
    }, POLL_MS);
    return () => clearInterval(t);
  }, [pendingKey]);

  function choose(list) {
    const imgs = Array.from(list || []).filter((f) => /\.(jpe?g|png|webp)$/i.test(f.name));
    if (!imgs.length) return setError("Choose JPG, PNG or WebP photos.");
    setError("");
    setFiles(imgs);
    setPoints([]);
  }

  async function submit() {
    setError("");
    if (!files.length) return setError("Choose at least one photo.");
    if (points.length < 3) return setError("Mark the railway land with at least 3 points.");
    if ((lat === "") !== (lon === "")) return setError("Give both latitude and longitude, or neither.");
    setBusy(true);
    try {
      const uploaded = await uploadPhotos(files, { zonePoints: points, latitude: lat, longitude: lon, cameraLabel: label });
      // Duplicates are already done: fetch their findings straight away.
      const full = await Promise.all(
        uploaded.map((u) => (u.status === "done" ? getPhoto(u.id).then((d) => ({ ...d, duplicate: u.duplicate })) : u)),
      );
      setResults((prev) => [...full, ...prev]);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  const fieldLabel = "mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-muted";

  return (
    <>
      <PageHeader
        crumbs={[["Encroachment"], ["Photo analysis"]]}
        title="Photo analysis"
        description="Upload track-side photographs, outline the railway land once, and RailVigil flags structures, vegetation, waste, material dumps and vehicles on it."
      />

      <div className="grid gap-6 lg:grid-cols-5">
        {/* 60%: photo and zone */}
        <Card
          className="lg:col-span-3"
          title={preview ? "Mark the railway land" : "Upload photographs"}
          subtitle={
            preview
              ? `Click on the photo to outline the right-of-way · ${points.length} points${files.length > 1 ? ` · applied to all ${files.length} photos` : ""}`
              : "JPG, PNG or WebP · up to 20 photos · 25 MB each"
          }
          action={
            preview && (
              <div className="flex gap-2">
                <button onClick={() => setPoints(LOWER_PART)} className={`${btn.secondary} ${btn.small}`}>
                  Lower part
                </button>
                <button onClick={() => setPoints(points.slice(0, -1))} className={`${btn.secondary} ${btn.small}`} disabled={!points.length}>
                  Undo
                </button>
                <button onClick={() => setPoints([])} className={`${btn.secondary} ${btn.small}`} disabled={!points.length}>
                  Clear
                </button>
              </div>
            )
          }
        >
          {preview ? (
            <ZoneCanvas src={preview} points={points} onChange={setPoints} />
          ) : (
            <label
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                choose(e.dataTransfer.files);
              }}
              className={`flex h-80 cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed transition ${
                dragging ? "border-ink bg-surface-2" : "border-line bg-paper hover:border-ink/40"
              }`}
            >
              <UploadCloud className="h-10 w-10 text-muted" aria-hidden />
              <span className="mt-3 font-semibold">Drag photos here or click to browse</span>
              <span className="mt-1 text-sm text-muted">GPS in the photo is used automatically</span>
              <input type="file" multiple accept=".jpg,.jpeg,.png,.webp" className="sr-only" onChange={(e) => choose(e.target.files)} />
            </label>
          )}
        </Card>

        {/* 40%: details and action */}
        <Card className="lg:col-span-2" title="Analysis details" bodyClass="space-y-5 p-6">
          <div>
            <span className={fieldLabel}>Photographs</span>
            {files.length ? (
              <ul className="max-h-36 divide-y divide-line overflow-auto rounded-md border border-line bg-paper text-sm">
                {files.map((f) => (
                  <li key={f.name} className="flex justify-between gap-3 px-3 py-2">
                    <span className="truncate">{f.name}</span>
                    <span className="shrink-0 font-mono text-xs text-muted">{(f.size / 1e6).toFixed(1)} MB</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">None chosen yet.</p>
            )}
            {files.length > 0 && (
              <button onClick={() => (setFiles([]), setPoints([]))} className="mt-2 text-xs font-medium underline underline-offset-4">
                Change photographs
              </button>
            )}
          </div>
          <div>
            <span className={fieldLabel}>Location (optional)</span>
            <div className="grid grid-cols-2 gap-2">
              <input aria-label="Latitude" className={inputClass} placeholder="Latitude" inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} />
              <input aria-label="Longitude" className={inputClass} placeholder="Longitude" inputMode="decimal" value={lon} onChange={(e) => setLon(e.target.value)} />
            </div>
            <p className="mt-1.5 text-xs text-muted">Used only for photos without GPS. Without a location, findings are recorded but not mapped.</p>
          </div>
          <div>
            <label htmlFor="camera-label" className={fieldLabel}>
              Label (optional)
            </label>
            <input id="camera-label" className={inputClass} placeholder="e.g. Km 42, near Kalyan" value={label} onChange={(e) => setLabel(e.target.value)} />
          </div>
          {error && <ErrorBanner>{error}</ErrorBanner>}
          <button onClick={submit} disabled={busy} className={`${btn.primary} w-full py-3`}>
            {busy ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Uploading…
              </>
            ) : (
              "Analyse photographs"
            )}
          </button>
        </Card>
      </div>

      {results.length > 0 && (
        <section aria-label="Results" className="mt-10 space-y-6">
          <h2 className="border-b border-canvas-line pb-3 font-mono text-[11px] uppercase tracking-[0.2em] text-canvas-muted">
            Results · {results.length} photograph(s)
          </h2>
          {results.map((r) => (
            <ResultCard key={r.id} photo={r} />
          ))}
        </section>
      )}
    </>
  );
}
