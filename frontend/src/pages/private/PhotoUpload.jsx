import { useEffect, useMemo, useState } from "react";
import { fileUrl, getPhoto, uploadPhotos } from "../../api/encroachment.js";
import ZoneCanvas from "../../components/encroachment/ZoneCanvas.jsx";
import FindingList from "../../components/encroachment/FindingList.jsx";
import { formatDateTime } from "../../utils/formatDate.js";

const POLL_MS = 2000;
const BOTTOM_HALF = [
  [0, 0.55],
  [1, 0.55],
  [1, 1],
  [0, 1],
];

function errorText(e) {
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; ");
  return e?.message || "Something went wrong";
}

const LOCATION_TEXT = { exif: "GPS from photo", pin: "Map pin", none: "No location" };

function ResultCard({ photo }) {
  const [view, setView] = useState("annotated");
  const done = photo.status === "done";
  const src = done && view === "annotated" ? photo.annotated_url : photo.original_url;
  return (
    <div className="rounded-2xl bg-surface p-5 text-ink shadow-none">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{photo.original_filename}</h3>
        <span
          className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${
            done ? "bg-emerald-500/15 text-emerald-300" : photo.status === "failed" ? "bg-rose-500/15 text-rose-300" : "animate-pulse bg-amber-500/15 text-amber-300"
          }`}
        >
          {photo.status}
        </span>
        {photo.duplicate && <span className="rounded-full bg-sky-500/15 px-2 py-0.5 text-[11px] text-sky-300">Already uploaded</span>}
        <span className="ml-auto font-mono text-[11px] text-muted">
          {LOCATION_TEXT[photo.location_source]}
          {photo.latitude != null && ` · ${photo.latitude.toFixed(5)}, ${photo.longitude.toFixed(5)}`}
          {photo.captured_at && ` · taken ${formatDateTime(photo.captured_at)}`}
        </span>
      </div>
      {photo.error && <p className="mb-3 text-sm text-rose-300">{photo.error}</p>}
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          {done && (
            <div className="mb-2 inline-flex rounded-full bg-surface-2 p-1 text-xs">
              {["original", "annotated"].map((v) => (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={`rounded-full px-3 py-1 capitalize ${view === v ? "bg-accent text-white" : "text-muted"}`}
                >
                  {v === "original" ? "Before" : "After"}
                </button>
              ))}
            </div>
          )}
          <img src={fileUrl(src)} alt={photo.original_filename} className="w-full rounded-2xl bg-black" />
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">
            Findings {done && `(${photo.findings?.length ?? 0})`}
          </h4>
          {done ? (
            <FindingList findings={photo.findings} />
          ) : (
            <p className="text-sm text-muted">{photo.status === "failed" ? "Analysis failed." : "Analysing…"}</p>
          )}
        </div>
      </div>
    </div>
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

  const preview = useMemo(() => (files[0] ? URL.createObjectURL(files[0]) : null), [files]);
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  // Poll photos that are still being analysed.
  const pending = results.filter((r) => r.status === "queued" || r.status === "processing").map((r) => r.id);
  const pendingKey = pending.join(",");
  useEffect(() => {
    if (!pendingKey) return;
    const t = setInterval(async () => {
      const ids = pendingKey.split(",");
      const fresh = await Promise.all(ids.map((id) => getPhoto(id).catch(() => null)));
      setResults((prev) =>
        prev.map((r) => {
          const f = fresh.find((x) => x && x.id === r.id);
          return f ? { ...f, duplicate: r.duplicate } : r;
        }),
      );
    }, POLL_MS);
    return () => clearInterval(t);
  }, [pendingKey]);

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

  const input = "w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-sm outline-none focus:border-accent";

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Encroachment · Photo analysis</h1>
        <p className="text-sm text-white/60">
          Upload track-side photos, outline the railway land, and RailVigil flags structures, vegetation, debris, dumps
          and vehicles on it.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="rounded-2xl bg-surface p-5 text-ink shadow-none">
          {preview ? (
            <>
              <div className="mb-2 flex items-center justify-between text-sm">
                <span>
                  Click to outline the <b>railway land</b> ({points.length} points)
                  {files.length > 1 && <span className="text-muted"> · same zone used for all {files.length} photos</span>}
                </span>
                <div className="flex gap-2">
                  <button onClick={() => setPoints(BOTTOM_HALF)} className="rounded-full bg-surface-2 px-3 py-1 text-xs hover:bg-line">
                    Lower part
                  </button>
                  <button onClick={() => setPoints(points.slice(0, -1))} className="rounded-full bg-surface-2 px-3 py-1 text-xs hover:bg-line">
                    Undo
                  </button>
                  <button onClick={() => setPoints([])} className="rounded-full bg-surface-2 px-3 py-1 text-xs hover:bg-line">
                    Clear
                  </button>
                </div>
              </div>
              <ZoneCanvas src={preview} points={points} onChange={setPoints} />
            </>
          ) : (
            <label className="flex h-72 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-line text-muted hover:border-accent">
              <span className="text-4xl">📷</span>
              <span className="mt-2 font-medium">Choose photos (JPG, PNG, WebP)</span>
              <span className="text-xs">Up to 20 at once</span>
              <input
                type="file"
                multiple
                accept=".jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={(e) => {
                  setFiles(Array.from(e.target.files || []));
                  setPoints([]);
                }}
              />
            </label>
          )}
        </div>

        <div className="space-y-4 rounded-2xl bg-surface p-5 text-ink shadow-none">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-muted">Photos</div>
            {files.length ? (
              <ul className="mt-1 max-h-32 overflow-auto text-sm">
                {files.map((f) => (
                  <li key={f.name} className="truncate">
                    {f.name}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">None chosen</p>
            )}
            {files.length > 0 && (
              <button
                onClick={() => {
                  setFiles([]);
                  setPoints([]);
                }}
                className="mt-1 text-xs text-accent hover:underline"
              >
                Change photos
              </button>
            )}
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-muted">Location (optional)</div>
            <p className="mb-2 text-[11px] text-muted">Used only when a photo has no GPS of its own.</p>
            <div className="grid grid-cols-2 gap-2">
              <input className={input} placeholder="Latitude" value={lat} onChange={(e) => setLat(e.target.value)} />
              <input className={input} placeholder="Longitude" value={lon} onChange={(e) => setLon(e.target.value)} />
            </div>
          </div>
          <div>
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Label (optional)</div>
            <input className={input} placeholder="e.g. Km 42 near Kalyan" value={label} onChange={(e) => setLabel(e.target.value)} />
          </div>
          {error && <p className="text-sm text-rose-300">{error}</p>}
          <button
            onClick={submit}
            disabled={busy}
            className="w-full rounded-full bg-accent py-3 font-semibold text-white hover:bg-accent-hover disabled:opacity-50"
          >
            {busy ? "Uploading…" : "Analyse photos"}
          </button>
        </div>
      </div>

      {results.map((r) => (
        <ResultCard key={r.id} photo={r} />
      ))}
    </div>
  );
}
