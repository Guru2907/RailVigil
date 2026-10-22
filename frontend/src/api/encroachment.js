import axiosClient, { API_BASE_URL } from "./axiosClient.js";

// The backend returns file links as "/api/..."; this makes them absolute
// against the API server, so they work with or without the Vite proxy.
const API_ORIGIN = API_BASE_URL.replace(/\/api\/?$/, "");
export function fileUrl(path) {
  if (!path) return null;
  return path.startsWith("http") ? path : `${API_ORIGIN}${path}`;
}

// --- photos (media) ---------------------------------------------------------

// zonePoints: [[x, y], ...] normalized 0-1, so one zone fits photos of any size
export async function uploadPhotos(files, { zonePoints, latitude, longitude, cameraLabel } = {}) {
  const form = new globalThis.FormData();
  files.forEach((f) => form.append("files", f));
  form.append("zone_points", JSON.stringify(zonePoints));
  form.append("zone_format", "normalized");
  if (latitude !== "" && latitude != null) form.append("latitude", latitude);
  if (longitude !== "" && longitude != null) form.append("longitude", longitude);
  if (cameraLabel) form.append("camera_label", cameraLabel);
  const { data } = await axiosClient.post("/media", form);
  return data;
}

export async function getPhoto(mediaId) {
  const { data } = await axiosClient.get(`/media/${mediaId}`);
  return data;
}

export async function listPhotos(params = {}) {
  const { data } = await axiosClient.get("/media", { params });
  return data;
}

// --- findings and sites -----------------------------------------------------

export async function listSites(params = {}) {
  const { data } = await axiosClient.get("/encroachment/sites", { params });
  return data;
}

export async function getSite(siteId) {
  const { data } = await axiosClient.get(`/encroachment/sites/${siteId}`);
  return data;
}

export async function updateSiteStatus(siteId, status, note) {
  const { data } = await axiosClient.patch(`/encroachment/sites/${siteId}`, { status, note: note || null });
  return data;
}

// --- reports, map, stats ----------------------------------------------------

export async function listReports(params = {}) {
  const { data } = await axiosClient.get("/reports", { params });
  return data;
}

export async function getMapFeatures(params = {}) {
  const { data } = await axiosClient.get("/map/features", { params });
  return data;
}

export async function getStatsSummary() {
  const { data } = await axiosClient.get("/stats/summary");
  return data;
}
