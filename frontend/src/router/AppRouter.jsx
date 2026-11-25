import { Routes, Route } from "react-router-dom";
import AppLayout from "../layouts/AppLayout.jsx";
import PublicLayout from "../layouts/PublicLayout.jsx";
import LandingPage from "../pages/public/LandingPage.jsx";
import VideoAnalysis from "../pages/private/VideoAnalysis.jsx";
import Incidents from "../pages/private/Incidents.jsx";
import IncidentDetails from "../pages/private/IncidentDetails.jsx";
import Dashboard from "../pages/private/Dashboard.jsx";
import MapView from "../pages/private/MapView.jsx";
import PhotoUpload from "../pages/private/PhotoUpload.jsx";
import PhotoDetails from "../pages/private/PhotoDetails.jsx";
import Sites from "../pages/private/Sites.jsx";
import SiteDetails from "../pages/private/SiteDetails.jsx";
import Reports from "../pages/private/Reports.jsx";
import ReportDetails from "../pages/private/ReportDetails.jsx";
import NotFound from "../pages/NotFound.jsx";

export default function AppRouter() {
  return (
    <Routes>
      {/* Landing page: simple top navigation and footer */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
      </Route>

      {/* The working app: sidebar and top bar */}
      <Route element={<AppLayout />}>
        <Route path="/upload" element={<VideoAnalysis />} />
        <Route path="/incidents" element={<Incidents />} />
        <Route path="/incidents/:id" element={<IncidentDetails />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/map" element={<MapView />} />
        <Route path="/encroachment/upload" element={<PhotoUpload />} />
        <Route path="/photos/:id" element={<PhotoDetails />} />
        <Route path="/sites" element={<Sites />} />
        <Route path="/sites/:id" element={<SiteDetails />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/reports/:reportNo" element={<ReportDetails />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}