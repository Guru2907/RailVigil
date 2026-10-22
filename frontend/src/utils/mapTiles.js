// Map tile layers that work without an API key. (CARTO's basemaps now need a
// key and show "API KEY REQUIRED" tiles otherwise.)

const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services";

export const DARK_BASE = {
  url: `${ESRI}/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`,
  attribution: "Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors",
  maxZoom: 16,
};

export const DARK_LABELS = {
  url: `${ESRI}/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}`,
  attribution: "",
  maxZoom: 16,
};

export const SATELLITE = {
  url: `${ESRI}/World_Imagery/MapServer/tile/{z}/{y}/{x}`,
  attribution: "Tiles &copy; Esri &mdash; Maxar, Earthstar Geographics",
  maxZoom: 19,
};

export const RAILWAYS = {
  url: "https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
  attribution: '&copy; <a href="https://www.openrailwaymap.org/">OpenRailwayMap</a> (CC-BY-SA)',
  subdomains: "abc",
  maxZoom: 19,
};
