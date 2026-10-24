// Leaflet plugins (marker clustering, heatmap) attach themselves to a global `L`.
// This module runs first because leafletPlugins.js imports it first.
import L from "leaflet";

globalThis.L = L;

export default L;
