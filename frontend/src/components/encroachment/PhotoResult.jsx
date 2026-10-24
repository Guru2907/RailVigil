import { useState } from "react";
import { Check, Circle, Loader2, X } from "lucide-react";
import { fileUrl } from "../../api/encroachment.js";
import FindingList from "./FindingList.jsx";
import { Card, ErrorBanner, Segmented } from "../ui/index.jsx";
import { formatDateTime } from "../../utils/formatDate.js";

const LOCATION_TEXT = { exif: "GPS from photo", pin: "Map pin", none: "No location" };

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

// One analysed photo: before/after image, pipeline status and findings.
export default function PhotoResult({ photo }) {
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
