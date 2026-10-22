from fastapi import APIRouter

from app.api.routes import encroachment, health, incidents, map_features, media, reports, stats, videos

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router)
api_router.include_router(videos.router)
api_router.include_router(incidents.router)
api_router.include_router(media.router)
api_router.include_router(encroachment.router)
api_router.include_router(reports.router)
api_router.include_router(map_features.router)
api_router.include_router(stats.router)
