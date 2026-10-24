import axiosClient, { API_BASE_URL } from "./axiosClient.js";

// zonePoints: [[x, y], ...] in video pixel coordinates (optional)
// location: optional { latitude, longitude } of the camera (incidents are mapped there)
export async function uploadVideo(file, zonePoints, cameraLabel, location = {}) {
  const form = new globalThis.FormData();
  form.append("video", file);
  if (zonePoints && zonePoints.length >= 3) {
    form.append("zone_points", JSON.stringify(zonePoints));
  }
  if (cameraLabel) form.append("camera_label", cameraLabel);
  if (location.latitude !== "" && location.latitude != null) form.append("latitude", location.latitude);
  if (location.longitude !== "" && location.longitude != null) form.append("longitude", location.longitude);
  const { data } = await axiosClient.post("/videos", form);
  return data;
}

export async function assignVideoZone(videoId, zonePoints) {
  const { data } = await axiosClient.put(`/videos/${videoId}/zone`, {
    zone_points: zonePoints,
  });
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
