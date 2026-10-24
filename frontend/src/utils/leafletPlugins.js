// Leaflet with the marker-cluster and heatmap plugins installed.
// ES modules evaluate in import order, so the global `L` exists before the plugins load.
import L from "./leafletGlobal.js";
import "leaflet.markercluster";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.heat";

export default L;
