"""Unit tests for RSS news aggregation."""
from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest


def test_news_item_is_a_dataclass():
    from scripts.news_sources import NewsItem

    item = NewsItem(
        source="Reuters",
        title="ECB holds rates steady",
        lead="The European Central Bank left rates unchanged.",
        url="https://reuters.com/ecb-rates",
        published_at="2026-04-25T09:00:00+00:00",
        language="en",
        region="global",
    )
    assert item.source == "Reuters"
    assert item.language == "en"
    assert item.region == "global"
    d = asdict(item)
    assert "title" in d


def test_fetch_feed_returns_empty_on_bad_url():
    from scripts.news_sources import fetch_feed

    bad = {
        "url": "https://invalid.example.invalid/feed",
        "source": "Bad",
        "language": "en",
        "region": "global",
    }
    result = fetch_feed(bad, limit=5)
    assert result == []


def test_fetch_feed_parses_mock_feed():
    from scripts.news_sources import NewsItem, fetch_feed

    mock_parsed = MagicMock()
    entry = MagicMock()
    entry.get.side_effect = lambda k, d="": {
        "title": "Gold hits record",
        "summary": "Gold reached $3,400 per ounce.",
        "link": "https://reuters.com/gold",
    }.get(k, d)
    entry.published_parsed = (2026, 4, 25, 9, 0, 0, 5, 115, 0)
    entry.updated_parsed = None
    mock_parsed.entries = [entry]

    with patch("scripts.news_sources.feedparser.parse", return_value=mock_parsed):
        cfg = {
            "url": "https://feeds.reuters.com/reuters/worldNews",
            "source": "Reuters",
            "language": "en",
            "region": "global",
        }
        items = fetch_feed(cfg, limit=5)

    assert len(items) == 1
    assert items[0].title == "Gold hits record"
    assert items[0].source == "Reuters"
    assert items[0].lead == "Gold reached $3,400 per ounce."


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.news_sources.CACHE_DIR", tmp_path)

    from scripts.news_sources import NewsItem, _load_cache, _save_cache

    items = [
        NewsItem(
            "Reuters",
            "Test headline",
            "Lead text",
            "http://x.com",
            "2026-04-25T10:00:00+00:00",
            "en",
            "global",
        )
    ]
    _save_cache(items)

    loaded = _load_cache()
    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0].title == "Test headline"
    assert loaded[0].source == "Reuters"


def test_fetch_all_sources_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.news_sources.CACHE_DIR", tmp_path)

    from scripts.news_sources import NewsItem, _save_cache, fetch_all_sources

    cached_items = [
        NewsItem(
            "Cached",
            "From cache",
            "Lead",
            "http://cached.com",
            "2026-04-25T10:00:00+00:00",
            "en",
            "global",
        )
    ]
    _save_cache(cached_items)

    with patch("scripts.news_sources.fetch_feed") as mock_fetch:
        result = fetch_all_sources(limit_per_source=5)
        mock_fetch.assert_not_called()

    assert result[0].source == "Cached"


def test_fetch_all_sources_tolerates_failed_feeds(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.news_sources.CACHE_DIR", tmp_path)

    from scripts.news_sources import NewsItem, fetch_all_sources

    def side_effect(cfg, limit):
        if cfg["source"] == "Reuters":
            raise RuntimeError("simulated failure")
        return [
            NewsItem(
                cfg["source"],
                "Title",
                "Lead",
                "http://x.com",
                "",
                cfg["language"],
                cfg["region"],
            )
        ]

    with patch("scripts.news_sources.fetch_feed", side_effect=side_effect):
        result = fetch_all_sources(limit_per_source=5)

    sources = {i.source for i in result}
    assert "Reuters" not in sources
    assert len(result) > 0
