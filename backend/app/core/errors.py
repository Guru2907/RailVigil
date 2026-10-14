"""Errors the application raises on purpose, and that are safe to show to
the client.

`AppError` carries an HTTP status and a message written for the USER
("File is too large (max 500 MB)"). The error handler turns it into a
JSON response as-is. Anything that is NOT an AppError is treated as a bug:
it is logged with its traceback and the client only gets a generic
message (see middleware/error_handler.py).
"""


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationFailed(AppError):
    """The request was well-formed but the content is unusable."""
    status_code = 422


class UnsupportedMedia(AppError):
    status_code = 415


class PayloadTooLarge(AppError):
    status_code = 413
