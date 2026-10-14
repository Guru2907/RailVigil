"""The error layer: users see clear messages, never internals, and the
browser can always read the response (CORS headers present even on a 500)."""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import PayloadTooLarge, ValidationFailed
from app.middleware.cors import add_cors
from app.middleware.error_handler import add_error_handlers

ORIGIN = "http://localhost:5173"


@pytest.fixture
def client():
    """A tiny app wired up exactly like main.py (errors first, CORS last)."""
    app = FastAPI()
    add_error_handlers(app)
    add_cors(app)

    @app.get("/boom")
    def boom():
        raise RuntimeError(r"secret internals: C:\Users\someone\.env password=hunter2")

    @app.get("/user-error")
    def user_error():
        raise ValidationFailed("zone is bad")

    @app.get("/too-big")
    def too_big():
        raise PayloadTooLarge("File is too large (maximum 500 MB).")

    @app.get("/ok")
    def ok():
        return {"ok": True}

    return TestClient(app)


def test_unexpected_error_returns_generic_message_without_internals(client):
    r = client.get("/boom", headers={"Origin": ORIGIN})
    assert r.status_code == 500
    body = r.json()
    assert body["detail"] == "Internal server error"
    assert "secret" not in r.text and "hunter2" not in r.text and "Users" not in r.text
    assert len(body["request_id"]) == 8
    assert r.headers["x-request-id"] == body["request_id"]


def test_unexpected_error_still_has_cors_headers(client):
    """Without this the browser reports a misleading 'CORS error' instead
    of the real 500."""
    r = client.get("/boom", headers={"Origin": ORIGIN})
    assert r.headers["access-control-allow-origin"] == ORIGIN


def test_unexpected_error_is_logged_with_traceback_and_request_id(client, caplog):
    with caplog.at_level(logging.ERROR, logger="app.middleware.error_handler"):
        r = client.get("/boom")
    record = next(rec for rec in caplog.records if "unhandled error" in rec.getMessage())
    assert r.json()["request_id"] in record.getMessage()
    assert record.exc_info is not None                    # the traceback is in the log


def test_app_errors_pass_their_message_and_status_through(client):
    r = client.get("/user-error", headers={"Origin": ORIGIN})
    assert (r.status_code, r.json()) == (422, {"detail": "zone is bad"})
    assert r.headers["access-control-allow-origin"] == ORIGIN

    r = client.get("/too-big")
    assert r.status_code == 413


def test_every_response_carries_a_request_id(client):
    assert client.get("/ok").headers["x-request-id"]
