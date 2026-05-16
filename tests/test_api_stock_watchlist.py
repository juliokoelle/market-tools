"""Tests for /stock-watchlist CRUD endpoints."""
import json
import pytest
from pathlib import Path


@pytest.fixture
def client(tmp_path, monkeypatch):
    from scripts import api as api_module
    monkeypatch.setattr(api_module, "_STOCK_WATCHLIST_PATH", tmp_path / "sw.json")
    from fastapi.testclient import TestClient
    return TestClient(api_module.app)


def test_get_empty_watchlist(client):
    r = client.get("/stock-watchlist")
    assert r.status_code == 200
    assert r.json() == []


def test_add_stock_entry(client):
    r = client.post("/stock-watchlist", json={"ticker": "asml", "notes": "AI infrastructure"})
    assert r.status_code == 201
    data = r.json()
    assert len(data) == 1
    assert data[0]["ticker"] == "ASML"
    assert data[0]["notes"] == "AI infrastructure"


def test_add_stock_deduplicates(client):
    client.post("/stock-watchlist", json={"ticker": "NVDA", "notes": "first"})
    client.post("/stock-watchlist", json={"ticker": "nvda", "notes": "second"})
    r = client.get("/stock-watchlist")
    assert len(r.json()) == 1
    assert r.json()[0]["notes"] == "first"


def test_add_multiple_stocks(client):
    client.post("/stock-watchlist", json={"ticker": "ASML"})
    client.post("/stock-watchlist", json={"ticker": "NVDA"})
    r = client.get("/stock-watchlist")
    tickers = [e["ticker"] for e in r.json()]
    assert "ASML" in tickers
    assert "NVDA" in tickers


def test_delete_stock(client):
    client.post("/stock-watchlist", json={"ticker": "TSLA"})
    r = client.delete("/stock-watchlist/TSLA")
    assert r.status_code == 200
    assert r.json() == []


def test_delete_stock_case_insensitive(client):
    client.post("/stock-watchlist", json={"ticker": "TSLA"})
    r = client.delete("/stock-watchlist/tsla")
    assert r.json() == []


def test_delete_nonexistent_stock_returns_empty(client):
    r = client.delete("/stock-watchlist/NONEXISTENT")
    assert r.status_code == 200
    assert r.json() == []
