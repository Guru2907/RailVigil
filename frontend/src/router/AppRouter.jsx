import { Routes, Route } from "react-router-dom";
import PublicLayout from "../layouts/PublicLayout.jsx";
import PrivateLayout from "../layouts/PrivateLayout.jsx";
import LandingPage from "../pages/public/LandingPage.jsx";
import Login from "../pages/public/Login.jsx";
import Signup from "../pages/public/Signup.jsx";
import Dashboard from "../pages/private/Dashboard.jsx";
import VideoAnalysis from "../pages/private/VideoAnalysis.jsx";
import Incidents from "../pages/private/Incidents.jsx";
import IncidentDetails from "../pages/private/IncidentDetails.jsx";
import LiveMonitoring from "../pages/private/LiveMonitoring.jsx";
import Analytics from "../pages/private/Analytics.jsx";
import Profile from "../pages/private/Profile.jsx";
import Settings from "../pages/private/Settings.jsx";

export default function AppRouter() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      {/* App: sidebar + topbar */}
      <Route element={<PrivateLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/upload" element={<VideoAnalysis />} />
        <Route path="/incidents" element={<Incidents />} />
        <Route path="/incidents/:id" element={<IncidentDetails />} />
        <Route path="/live" element={<LiveMonitoring />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}