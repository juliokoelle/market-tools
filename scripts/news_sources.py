"""
RSS news aggregation with 30-minute caching.

Fetches RSS feeds across global markets, European markets, German sources, and Tech/VC.
Results cached to data/cache/feeds_YYYY-MM-DD-HHMM.json (rounded to 30-min window).
Individual feed failures are silently skipped — never crashes the pipeline.

Feed metadata fields:
  category  — "markets" | "tech" | "vc" | "macro" | "general"
  priority  — 1 (must-include) | 2 (if-relevant) | 3 (optional/fallback)
  language  — "en" | "de" | "pt"
  region    — "global" | "us" | "eu" | "de" | "brazil"

Usage:
    from scripts.news_sources import fetch_all_sources
    items = fetch_all_sources(limit_per_source=5, total_limit=30)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

CACHE_DIR = Path("data/cache")
_CACHE_TTL_MINUTES = 30
_MAX_AGE_HOURS = 24

_SPAM_KEYWORDS = frozenset({
    "sponsored", "advertisement", "promoted", "advertorial",
    "anzeige", "werbung", "partner content", "paid post",
})

RSS_FEEDS = [
    # ── Priority 1 · Global Markets ──────────────────────────────────────
    {
        "url": "https://feeds.reuters.com/reuters/worldNews",
        "source": "Reuters",
        "language": "en",
        "region": "global",
        "category": "general",
        "priority": 1,
    },
    {
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "source": "Reuters Business",
        "language": "en",
        "region": "global",
        "category": "markets",
        "priority": 1,
    },
    {
        "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
        "source": "Reuters Agency",
        "language": "en",
        "region": "global",
        "category": "markets",
        "priority": 1,
    },
    {
        "url": "https://www.ft.com/?format=rss",
        "source": "Financial Times",
        "language": "en",
        "region": "global",
        "category": "markets",
        "priority": 1,
    },
    {
        "url": "https://www.ft.com/markets?format=rss",
        "source": "FT Markets",
        "language": "en",
        "region": "global",
        "category": "markets",
        "priority": 1,
    },
    {
        "url": "https://feeds.bloomberg.com/markets/news.rss",
        "source": "Bloomberg Markets",
        "language": "en",
        "region": "us",
        "category": "markets",
        "priority": 1,
    },
    {
        "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "source": "WSJ Markets",
        "language": "en",
        "region": "us",
        "category": "markets",
        "priority": 1,
    },
    # ── Priority 1 · German Markets ───────────────────────────────────────
    {
        "url": "https://www.handelsblatt.com/contentexport/feed/top-themen",
        "source": "Handelsblatt",
        "language": "de",
        "region": "de",
        "category": "general",
        "priority": 1,
    },
    # ── Priority 2 · Global & EU ──────────────────────────────────────────
    {
        "url": "https://www.theguardian.com/business/rss",
        "source": "The Guardian",
        "language": "en",
        "region": "global",
        "category": "general",
        "priority": 2,
    },
    {
        "url": "https://finance.yahoo.com/news/rssindex",
        "source": "Yahoo Finance",
        "language": "en",
        "region": "global",
        "category": "markets",
        "priority": 2,
    },
    {
        "url": "https://sifted.eu/feed",
        "source": "Sifted",
        "language": "en",
        "region": "eu",
        "category": "tech",
        "priority": 2,
    },
    # ── Priority 2 · Tech & VC ────────────────────────────────────────────
    {
        "url": "https://techcrunch.com/feed/",
        "source": "TechCrunch",
        "language": "en",
        "region": "us",
        "category": "tech",
        "priority": 2,
    },
    {
        "url": "https://www.theinformation.com/feed",
        "source": "The Information",
        "language": "en",
        "region": "us",
        "category": "tech",
        "priority": 2,
    },
    # ── Priority 2 · Brazil ───────────────────────────────────────────────
    {
        "url": "https://feeds.folha.uol.com.br/mercado/rss091.xml",
        "source": "Folha SP Mercado",
        "language": "pt",
        "region": "brazil",
        "category": "macro",
        "priority": 2,
    },
    # ── Priority 3 · Optional / Fallback ─────────────────────────────────
    {
        "url": "https://stratechery.com/feed/",
        "source": "Stratechery",
        "language": "en",
        "region": "us",
        "category": "tech",
        "priority": 3,
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
    category: str = "general"
    priority: int = 2


def _is_spam(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in _SPAM_KEYWORDS)


def _is_too_old(published_at: str) -> bool:
    if not published_at:
        return False
    try:
        pub_dt = datetime.fromisoformat(published_at)
        return (datetime.now(timezone.utc) - pub_dt) > timedelta(hours=_MAX_AGE_HOURS)
    except ValueError:
        return False


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
        for entry in parsed.entries:
            if len(items) >= limit:
                break

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

            if not title or not lead:
                continue
            if _is_spam(title):
                continue
            if _is_too_old(published_at):
                continue

            items.append(
                NewsItem(
                    source=feed_config["source"],
                    title=title,
                    lead=lead[:400],
                    url=url,
                    published_at=published_at,
                    language=feed_config["language"],
                    region=feed_config["region"],
                    category=feed_config.get("category", "general"),
                    priority=feed_config.get("priority", 2),
                )
            )
    except Exception as e:
        print(f"[WARN] Feed '{feed_config['source']}' failed: {e}")
    return items


def fetch_all_sources(limit_per_source: int = 5, total_limit: int = 30) -> list[NewsItem]:
    """
    Fetch all RSS feeds sorted by priority. Returns cached results if within the last 30 minutes.
    Applies total_limit and per-source limit as diversity constraints.
    Individual feed failures are silently skipped.
    """
    cached = _load_cache()
    if cached is not None:
        print(f"  [cache] Loaded {len(cached)} RSS items from cache.")
        return cached

    sorted_feeds = sorted(RSS_FEEDS, key=lambda f: f.get("priority", 2))
    all_items: list[NewsItem] = []

    for feed in sorted_feeds:
        remaining = total_limit - len(all_items)
        if remaining <= 0:
            break
        try:
            items = fetch_feed(feed, limit=min(limit_per_source, remaining))
        except Exception as e:
            print(f"  [rss] {feed['source']}: skipped ({e})")
            continue
        all_items.extend(items)
        status = f"{len(items)} items" if items else "0 items (failed or empty)"
        print(f"  [rss] {feed['source']} (p{feed.get('priority', 2)}): {status}")

    _save_cache(all_items)
    print(f"  [rss] Total: {len(all_items)} items cached.")
    return all_items


if __name__ == "__main__":
    items = fetch_all_sources()
    print(f"\n{'─'*60}")
    print(f"Total: {len(items)} items from {len({i.source for i in items})} sources\n")
    for item in items[:15]:
        print(f"[{item.region.upper():8}] [{item.category:8}] [{item.source}]")
        print(f"  {item.title[:90]}")
        if item.lead:
            print(f"  {item.lead[:100]}…")
        print()
