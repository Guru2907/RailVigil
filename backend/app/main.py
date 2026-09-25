"""
FastAPI entrypoint. Run with:
    uvicorn app.main:app --reload --port 8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core import config
from app.db.database import init_db
from app.middleware.cors import add_cors
from app.middleware.error_handler import add_error_handlers
from app.api.router import api_router

app = FastAPI(
    title="RailVigil API",
    description="Automated Railway Track Encroachment Detection -- YOLOv8 + spatiotemporal risk scoring",
    version="0.1.0",
)

add_cors(app)
add_error_handlers(app)


@app.on_event("startup")
def on_startup():
    Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.MODELS_DIR).mkdir(parents=True, exist_ok=True)
    init_db()


app.include_router(api_router)

# Serves snapshots/annotated videos by direct URL -- used as <img src>
# and fallback <video src> in the frontend.
Path(config.OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/static/outputs", StaticFiles(directory=str(config.OUTPUTS_DIR)), name="outputs")