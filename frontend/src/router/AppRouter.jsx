import { Routes, Route } from "react-router-dom";
import PrivateLayout from "../layouts/PrivateLayout.jsx";
import LandingPage from "../pages/public/LandingPage.jsx";
import VideoAnalysis from "../pages/private/VideoAnalysis.jsx";

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />

      {/* App pages: sidebar + top bar */}
      <Route element={<PrivateLayout />}>
        <Route path="/upload" element={<VideoAnalysis />} />
      </Route>
    </Routes>
  );
}