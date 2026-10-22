"""
FastAPI entrypoint. Run with (ONE process; see services/job_queue.py):
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core import config
from app.core.logging import configure_logging
from app.db.database import init_db
from app.middleware.cors import add_cors
from app.middleware.error_handler import add_error_handlers
from app.services import image_jobs, job_queue

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Everything that must happen once when the server starts, and once
    when it stops. (Replaces the deprecated @app.on_event handlers.)"""
    configure_logging()
    for d in (config.DATA_DIR, config.OUTPUTS_DIR, config.MODELS_DIR, config.STORAGE_DIR):
        Path(d).mkdir(parents=True, exist_ok=True)
    init_db()  # runs migrations

    # Starting the queues first re-queues anything a previous run left unfinished.
    queue = job_queue.get_queue()          # videos (intrusion)
    queue.start()
    image_queue = image_jobs.get_image_queue()   # photos (encroachment)
    image_queue.start()
    logger.info("RailVigil API ready")
    try:
        yield
    finally:
        # In-flight jobs stop and go back to `queued`.
        image_queue.stop()
        queue.stop()


app = FastAPI(
    title="RailVigil API",
    description=(
        "Railway right-of-way monitoring: potential encroachments (structures, vegetation, "
        "debris, dumped material) in photos, with sites and numbered reports; and intrusion "
        "detection in video (people and vehicles entering configured track zones)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Order matters: errors first (inner), CORS last (outer). See error_handler.py.
add_error_handlers(app)
add_cors(app)

app.include_router(api_router)

# Serves snapshots/annotated videos by direct URL -- used as <img src>
# and fallback <video src> in the frontend.
Path(config.OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/static/outputs", StaticFiles(directory=str(config.OUTPUTS_DIR)), name="outputs")
