import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getPhoto } from "../../api/encroachment.js";
import PhotoResult from "../../components/encroachment/PhotoResult.jsx";
import { ErrorBanner, PageHeader } from "../../components/ui/index.jsx";
import { formatDateTime } from "../../utils/formatDate.js";

export default function PhotoDetails() {
  const { id } = useParams();
  const [photo, setPhoto] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getPhoto(id)
      .then((p) => !cancelled && setPhoto(p))
      .catch((e) => !cancelled && setError(e.response?.status === 404 ? "Photo not found." : e.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  const crumbs = [["Encroachment"], ["Reports", "/reports"], ["Photo"]];

  return (
    <>
      <PageHeader
        crumbs={crumbs}
        title="Analysed photo"
        description={photo ? `Uploaded ${formatDateTime(photo.created_at)}` : undefined}
      />
      {photo ? (
        <PhotoResult photo={photo} />
      ) : error ? (
        <ErrorBanner>{error}</ErrorBanner>
      ) : (
        <p className="text-sm text-canvas-muted">Loading…</p>
      )}
    </>
  );
}
