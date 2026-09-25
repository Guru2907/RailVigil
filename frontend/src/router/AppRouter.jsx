import { Routes, Route } from "react-router-dom";
import LandingPage from "../pages/public/LandingPage.jsx";
import VideoAnalysis from "../pages/private/VideoAnalysis.jsx";

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/upload" element={<VideoAnalysis />} />
    </Routes>
  );
}