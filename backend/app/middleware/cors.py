from fastapi.middleware.cors import CORSMiddleware

# Vite's default dev port. Permissive on purpose for the demo stage --
# tighten this before any real deployment.
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def add_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )