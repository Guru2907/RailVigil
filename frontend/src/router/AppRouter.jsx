import { Routes, Route } from "react-router-dom";
import PrivateLayout from "../layouts/PrivateLayout.jsx";
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
import NotFound from "../pages/NotFound.jsx";

export default function AppRouter() {
  return (
    <Routes>
      {/* Every page: utility strip, header, menu bar and footer */}
      <Route element={<PrivateLayout />}>
        <Route path="/" element={<LandingPage />} />
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
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}