from fastapi.middleware.cors import CORSMiddleware

from app.core import config


def add_cors(app, origins: list[str] | None = None):
    """Allow the configured frontend origins (config.CORS_ORIGINS, from the
    CORS_ORIGINS environment variable) to call the API from the browser."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS if origins is None else origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
