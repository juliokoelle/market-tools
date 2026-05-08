"""Verify that POST /briefing/generate and legacy endpoint return 410 Gone."""
from fastapi.testclient import TestClient


def _client():
    from scripts.api import app
    return TestClient(app)


def test_briefing_generate_returns_410():
    resp = _client().post("/briefing/generate")
    assert resp.status_code == 410
    assert resp.json()["detail"]["error"] == "generation_disabled"


def test_briefing_generate_returns_410_for_openai():
    resp = _client().post("/briefing/generate?provider=openai")
    assert resp.status_code == 410


def test_generate_briefing_legacy_returns_410():
    resp = _client().post("/generate-briefing")
    assert resp.status_code == 410
    assert resp.json()["detail"]["error"] == "generation_disabled"
