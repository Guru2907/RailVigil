"""Turns errors into JSON responses, without ever leaking internals.

Two kinds of error:
  * AppError         -- raised on purpose with a message meant for the user
                        ("File is too large"). Returned as-is.
  * anything else    -- a bug. The traceback goes to the LOG (tagged with a
                        short request id); the client only gets a generic
                        message plus that id, so a user can quote it and you
                        can find the matching log entry.

IMPORTANT -- registration order in main.py:
    add_error_handlers(app)   # first  -> sits INSIDE the CORS layer
    add_cors(app)             # second -> outermost
Starlette wraps middleware last-added-outermost. If the catch-all were
outside CORS, a 500 response would leave without CORS headers and the
browser would report a confusing "CORS error" instead of the real one.
(The framework's own last-resort 500 handler sits outside every middleware,
which is why we catch in a middleware instead of add_exception_handler.)
"""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import AppError

logger = logging.getLogger(__name__)


async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


def add_error_handlers(app: FastAPI):
    app.add_exception_handler(AppError, app_error_handler)

    @app.middleware("http")
    async def catch_unhandled(request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001 -- this IS the catch-all
            logger.exception("unhandled error [%s] %s %s", request_id, request.method, request.url.path)
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
            )
        response.headers["X-Request-ID"] = request_id
        return response
