import { FileText, ImagePlus, LayoutDashboard, Map, MapPinned, Siren, Video } from "lucide-react";

// Main navigation, grouped by module. Encroachment and Intrusion are equal halves.
export const menu = [
  {
    group: null,
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/map", label: "GIS Map", icon: Map },
    ],
  },
  {
    group: "Encroachment",
    items: [
      { to: "/encroachment/upload", label: "Photo Analysis", icon: ImagePlus },
      { to: "/sites", label: "Sites", icon: MapPinned },
      { to: "/reports", label: "Reports", icon: FileText },
    ],
  },
  {
    group: "Intrusion",
    items: [
      { to: "/upload", label: "Video Analysis", icon: Video },
      { to: "/incidents", label: "Incidents", icon: Siren },
    ],
  },
];
