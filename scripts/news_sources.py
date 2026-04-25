"""
RSS news aggregation with 30-minute caching.

Fetches 8 free RSS feeds and merges with the existing NewsAPI pipeline.
Results cached to data/cache/feeds_YYYY-MM-DD-HHMM.json (rounded to 30-min window).
Individual feed failures are silently skipped — never crashes the pipeline.

Usage:
    from scripts.news_sources import fetch_all_sources
    items = fetch_all_sources(limit_per_source=5)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import feedparser

CACHE_DIR = Path("data/cache")
_CACHE_TTL_MINUTES = 30

RSS_FEEDS = [
    {
        "url": "https://feeds.reuters.com/reuters/worldNews",
        "source": "Reuters",
        "language": "en",
        "region": "global",
    },
    {
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "source": "Reuters Business",
        "language": "en",
        "region": "global",
    },
    {
        "url": "https://www.handelsblatt.com/contentexport/feed/top-themen",
        "source": "Handelsblatt",
        "language": "de",
        "region": "dach",
    },
    {
        "url": "https://www.ft.com/?format=rss",
        "source": "Financial Times",
        "language": "en",
        "region": "global",
    },
    {
        "url": "https://www.theguardian.com/business/rss",
        "source": "The Guardian",
        "language": "en",
        "region": "global",
    },
    {
        "url": "https://sifted.eu/feed",
        "source": "Sifted",
        "language": "en",
        "region": "europe",
    },
    {
        "url": "https://feeds.folha.uol.com.br/mercado/rss091.xml",
        "source": "Folha SP Mercado",
        "language": "pt",
        "region": "brazil",
    },
    {
        "url": "https://finance.yahoo.com/news/rssindex",
        "source": "Yahoo Finance",
        "language": "en",
        "region": "global",
    },
]


@dataclass
class NewsItem:
    source: str
    title: str
    lead: str
    url: str
    published_at: str  # ISO 8601
    language: str
    region: str


def _cache_key() -> str:
    now = datetime.now(timezone.utc)
    minute_block = (now.minute // _CACHE_TTL_MINUTES) * _CACHE_TTL_MINUTES
    return now.strftime("%Y-%m-%d-%H") + f"{minute_block:02d}"


def _cache_path() -> Path:
    return CACHE_DIR / f"feeds_{_cache_key()}.json"


def _load_cache() -> list[NewsItem] | None:
    path = _cache_path()
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return [NewsItem(**item) for item in data]
    return None


def _save_cache(items: list[NewsItem]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path().write_text(
        json.dumps([asdict(i) for i in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fetch_feed(feed_config: dict, limit: int = 5) -> list[NewsItem]:
    """Fetch a single RSS feed. Returns [] on any error — never raises."""
    items = []
    try:
        parsed = feedparser.parse(feed_config["url"])
        for entry in parsed.entries[:limit]:
            title = entry.get("title", "").strip()
            lead = (entry.get("summary") or entry.get("description") or "").strip()
            url = entry.get("link", "")

            published_at = ""
            if getattr(entry, "published_parsed", None):
                try:
                    published_at = datetime(
                        *entry.published_parsed[:6], tzinfo=timezone.utc
                    ).isoformat()
                except (TypeError, ValueError):
                    pass
            elif getattr(entry, "updated_parsed", None):
                try:
                    published_at = datetime(
                        *entry.updated_parsed[:6], tzinfo=timezone.utc
                    ).isoformat()
                except (TypeError, ValueError):
                    pass

            if title:
                items.append(
                    NewsItem(
                        source=feed_config["source"],
                        title=title,
                        lead=lead[:400],
                        url=url,
                        published_at=published_at,
                        language=feed_config["language"],
                        region=feed_config["region"],
                    )
                )
    except Exception as e:
        print(f"[WARN] Feed '{feed_config['source']}' failed: {e}")
    return items


def fetch_all_sources(limit_per_source: int = 5) -> list[NewsItem]:
    """
    Fetch all RSS feeds. Returns cached results if within the last 30 minutes.
    Individual feed failures are silently skipped.
    """
    cached = _load_cache()
    if cached is not None:
        print(f"  [cache] Loaded {len(cached)} RSS items from cache.")
        return cached

    all_items: list[NewsItem] = []
    for feed in RSS_FEEDS:
        try:
            items = fetch_feed(feed, limit=limit_per_source)
        except Exception as e:
            print(f"  [rss] {feed['source']}: skipped ({e})")
            continue
        all_items.extend(items)
        status = f"{len(items)} items" if items else "0 items (failed or empty)"
        print(f"  [rss] {feed['source']}: {status}")

    _save_cache(all_items)
    print(f"  [rss] Total: {len(all_items)} items cached.")
    return all_items


if __name__ == "__main__":
    items = fetch_all_sources()
    print(f"\n{'─'*60}")
    print(f"Total: {len(items)} items from {len({i.source for i in items})} sources\n")
    for item in items[:15]:
        print(f"[{item.region.upper():8}] [{item.source}]")
        print(f"  {item.title[:90]}")
        if item.lead:
            print(f"  {item.lead[:100]}…")
        print()
