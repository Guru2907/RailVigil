from fastapi import Request
from fastapi.responses import JSONResponse


async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {exc}"},
    )


def add_error_handlers(app):
    app.add_exception_handler(Exception, unhandled_exception_handler)