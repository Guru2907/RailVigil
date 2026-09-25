import axiosClient, { API_BASE_URL } from "./axiosClient.js";

// zonePoints: [[x, y], ...] in video pixel coordinates
export async function uploadVideo(file, zonePoints, cameraLabel) {
  const form = new FormData();
  form.append("video", file);
  form.append("zone_points", JSON.stringify(zonePoints));
  if (cameraLabel) form.append("camera_label", cameraLabel);
  const { data } = await axiosClient.post("/videos", form);
  return data;
}

export async function getVideo(videoId) {
  const { data } = await axiosClient.get(`/videos/${videoId}`);
  return data;
}

export function getAnnotatedVideoUrl(videoId) {
  return `${API_BASE_URL}/videos/${videoId}/file`;
}

export function getIncidentSnapshotUrl(incidentId) {
  return `${API_BASE_URL}/incidents/${incidentId}/snapshot`;
}

export async function listVideos() {
  const { data } = await axiosClient.get("/videos");
  return data;
}