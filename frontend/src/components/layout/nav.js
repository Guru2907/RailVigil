import { FileText, ImagePlus, LayoutDashboard, Map, MapPinned, Siren, Video } from "lucide-react";

// Main navigation, grouped by module. Encroachment and Intrusion are equal halves.
export const menu = [
  {
    group: null,
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/map", label: "GIS map", icon: Map },
    ],
  },
  {
    group: "Encroachment",
    items: [
      { to: "/encroachment/upload", label: "Photo analysis", icon: ImagePlus },
      { to: "/sites", label: "Sites", icon: MapPinned },
      { to: "/reports", label: "Reports", icon: FileText },
    ],
  },
  {
    group: "Intrusion",
    items: [
      { to: "/upload", label: "Video analysis", icon: Video },
      { to: "/incidents", label: "Incidents", icon: Siren },
    ],
  },
];
