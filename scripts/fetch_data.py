"""
Phase 2 — Live data fetching.

Fetches from:
  - Twelve Data  (XAU/USD, XAG/USD, EUR/USD)
  - yfinance     (Brent, Natural Gas, Copper — free, no API key)
  - NewsAPI      (filtered global economic headlines)

Saves to data/raw/YYYY-MM-DD/:
  commodities.json
  currencies.json
  news.json

Run:
    python scripts/fetch_data.py [YYYY-MM-DD]

Requires .env with TWELVE_DATA_API_KEY and NEWS_API_KEY.
"""

import json
import os
import sys
from datetime import date, timedelta

import requests
import yfinance as yf
from dotenv import load_dotenv

from scripts.utils import today, data_dir

load_dotenv()

TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# ---------------------------------------------------------------------------
# Commodity sources
# ---------------------------------------------------------------------------

# Twelve Data: precious metals only (XAU/USD, XAG/USD supported on free tier)
TWELVE_DATA_COMMODITIES = {
    "gold_usd_oz":   "XAU/USD",
    "silver_usd_oz": "XAG/USD",
}

# yfinance: energy and industrial commodities via Yahoo Finance futures tickers
YFINANCE_COMMODITIES = {
    "brent_usd_bbl":    "BZ=F",   # Brent Crude futures
    "natgas_usd_mmbtu": "NG=F",   # Natural Gas futures
    "copper_usd_lb":    "HG=F",   # Copper futures (USD/lb)
}

# ---------------------------------------------------------------------------
# NewsAPI — query, source, and content filters
# ---------------------------------------------------------------------------

# Topic-focused query for macroeconomic news
NEWS_QUERY = (
    "inflation OR \"interest rates\" OR \"central bank\" OR "
    "economy OR GDP OR recession OR tariff OR commodities OR "
    "\"Federal Reserve\" OR ECB OR \"trade war\""
)

# Approved high-quality sources (NewsAPI domain identifiers)
APPROVED_SOURCES = {
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "economist.com",
    "nytimes.com",
    "theguardian.com",
    "handelsblatt.com",
    "cnbc.com",
    "bbc.co.uk",
    "apnews.com",
    "businessinsider.com",
    "forbes.com",
    "marketwatch.com",
    "seekingalpha.com",
    "finance.yahoo.com",
    "thehill.com",
    "politico.com",
    "axios.com",
    "foreignpolicy.com",
    "project-syndicate.org",
    "imf.org",
    "worldbank.org",
    "ecb.europa.eu",
    "federalreserve.gov",
}

# Keywords that indicate off-topic articles — reject if found in title
EXCLUDE_KEYWORDS = {
    # Entertainment & celebrity
    "celebrity", "oscar", "grammy", "emmy", "box office", "blockbuster",
    "movie", "film", "album", "concert", "singer", "actor", "actress",
    "reality tv", "fashion week", "red carpet",
    # Sports
    "nfl", "nba", "nhl", "mlb", "fifa", "premier league", "champions league",
    "world cup", "olympics", "super bowl", "tennis", "golf tournament",
    "formula 1", "f1 race",
    # Lifestyle & health (non-economic)
    "diet", "weight loss", "skincare", "horoscope", "zodiac", "recipe",
    "relationship advice", "dating",
    # Crime & local news (non-systemic)
    "murder", "kidnapping", "robbery", "drug bust", "serial killer",
    "missing person", "amber alert",
}

# Keywords that must appear somewhere in the title or description
# to pass as genuinely relevant (at least one must match)
REQUIRED_KEYWORDS = {
    "economy", "economic", "inflation", "gdp", "recession", "growth",
    "central bank", "federal reserve", "ecb", "interest rate", "monetary",
    "fiscal", "budget", "deficit", "debt", "bond", "yield", "treasury",
    "market", "stock", "equity", "commodity", "oil", "gas", "gold", "silver",
    "copper", "trade", "tariff", "sanction", "export", "import", "supply chain",
    "currency", "dollar", "euro", "yen", "yuan", "fx", "exchange rate",
    "bank", "finance", "investment", "capital", "fund", "hedge",
    "unemployment", "labor", "labour", "jobs", "wages", "manufacturing",
    "industrial", "energy", "opec", "imf", "world bank", "g7", "g20",
    "geopolit", "war", "conflict", "sanction", "nato",
    "germany", "german", "bundesbank", "united states", "u.s.", "us economy",
    "brazil", "brasília", "china", "chinese", "russia", "european union",
    "eurozone", "latin america", "emerging market",
    "tech", "semiconductor", "ai ", "artificial intelligence", "startup",
    "venture capital", "ipo", "m&a", "merger", "acquisition",
}


def _title_and_desc(article: dict) -> str:
    """Return lowercased combined title + description for keyword matching."""
    title = (article.get("title") or "").lower()
    desc = (article.get("description") or "").lower()
    return f"{title} {desc}"


def _is_relevant(article: dict) -> bool:
    text = _title_and_desc(article)

    # Drop if any exclusion keyword appears in the title (not description —
    # avoid false positives like "tariff war kills celebrity tax deal")
    title = (article.get("title") or "").lower()
    if any(kw in title for kw in EXCLUDE_KEYWORDS):
        return False

    # Keep only if at least one required keyword appears anywhere
    if not any(kw in text for kw in REQUIRED_KEYWORDS):
        return False

    return True


def _source_domain(article: dict) -> str:
    url = article.get("url") or ""
    # Extract domain from URL cheaply without urllib overhead
    # e.g. "https://www.reuters.com/..." -> "reuters.com"
    try:
        host = url.split("//", 1)[1].split("/", 1)[0]  # strip scheme and path
        host = host.removeprefix("www.")
        return host
    except IndexError:
        return ""


def _is_approved_source(article: dict) -> bool:
    domain = _source_domain(article)
    return any(domain == src or domain.endswith("." + src) for src in APPROVED_SOURCES)


# ---------------------------------------------------------------------------
# Twelve Data — precious metals and FX
# ---------------------------------------------------------------------------

def _twelve_data_price(symbol: str) -> float | None:
    url = "https://api.twelvedata.com/price"
    try:
        resp = requests.get(url, params={"symbol": symbol, "apikey": TWELVE_DATA_KEY}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "price" not in data:
            print(f"  [WARN] Twelve Data — no price for {symbol}: {data.get('message', data)}")
            return None
        return round(float(data["price"]), 4)
    except Exception as e:
        print(f"  [WARN] Twelve Data — {symbol} failed: {e}")
        return None


# ---------------------------------------------------------------------------
# yfinance — energy and industrial commodities
# ---------------------------------------------------------------------------

def _yfinance_price(ticker: str) -> float | None:
    try:
        data = yf.Ticker(ticker).fast_info
        price = data.get("lastPrice") or data.get("regularMarketPrice")
        if price is None:
            print(f"  [WARN] yfinance — no price for {ticker}")
            return None
        return round(float(price), 4)
    except Exception as e:
        print(f"  [WARN] yfinance — {ticker} failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Combined commodity + FX fetchers
# ---------------------------------------------------------------------------

def fetch_commodities() -> dict:
    result = {}

    print("Fetching precious metals from Twelve Data...")
    for key, symbol in TWELVE_DATA_COMMODITIES.items():
        price = _twelve_data_price(symbol)
        result[key] = price
        print(f"  {key}: {price if price is not None else 'MISSING'}")

    print("Fetching energy/industrial commodities from yfinance...")
    for key, ticker in YFINANCE_COMMODITIES.items():
        price = _yfinance_price(ticker)
        result[key] = price
        print(f"  {key}: {price if price is not None else 'MISSING'}")

    return result


def fetch_currencies() -> dict:
    print("Fetching EUR/USD from Twelve Data...")
    price = _twelve_data_price("EUR/USD")
    print(f"  eurusd: {price if price is not None else 'MISSING'}")
    return {"eurusd": price}


# ---------------------------------------------------------------------------
# NewsAPI
# ---------------------------------------------------------------------------

def fetch_news(max_results: int = 15) -> list[dict]:
    """
    Fetch, filter, and return the most recent relevant economic news articles.

    Strategy:
      1. Request articles from the last 24 hours, sorted by publishedAt.
      2. Prefer articles from approved high-quality sources.
      3. Apply keyword inclusion/exclusion filters.
      4. Return up to max_results articles, approved sources first.
    """
    print("Fetching news from NewsAPI...")

    from_date = (date.today() - timedelta(days=1)).isoformat()

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": NEWS_QUERY,
        "language": "en",
        "sortBy": "publishedAt",
        "from": from_date,
        "pageSize": 100,
        "apiKey": NEWS_API_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok":
        print(f"  [WARN] NewsAPI error: {data.get('message', data)}")
        return []

    raw = data.get("articles", [])
    print(f"  {len(raw)} raw articles received (since {from_date}).")

    # Separate into approved-source and other buckets, applying relevance filter to both
    approved, others = [], []
    for a in raw:
        if not _is_relevant(a):
            continue
        if _is_approved_source(a):
            approved.append(a)
        else:
            others.append(a)

    # Fill up to max_results: approved sources first, then others
    # Both lists are already sorted by publishedAt (most recent first) from the API
    selected = (approved + others)[:max_results]
    print(f"  {len(approved)} from approved sources, {len(others)} from others → keeping {len(selected)}.")

    return [
        {
            "title":        a.get("title"),
            "source":       a.get("source", {}).get("name"),
            "domain":       _source_domain(a),
            "published_at": a.get("publishedAt"),
            "url":          a.get("url"),
            "description":  a.get("description"),
        }
        for a in selected
    ]


# ---------------------------------------------------------------------------
# Save helper
# ---------------------------------------------------------------------------

def save(path: str, data: object):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(run_date: str = None):
    if not TWELVE_DATA_KEY:
        raise EnvironmentError("TWELVE_DATA_API_KEY is not set in .env")
    if not NEWS_API_KEY:
        raise EnvironmentError("NEWS_API_KEY is not set in .env")

    d = run_date or today()
    out_dir = data_dir(d)
    os.makedirs(out_dir, exist_ok=True)
    print(f"\nFetching data for: {d}\n")

    commodities = fetch_commodities()
    save(os.path.join(out_dir, "commodities.json"), commodities)

    currencies = fetch_currencies()
    save(os.path.join(out_dir, "currencies.json"), currencies)

    news = fetch_news()
    save(os.path.join(out_dir, "news.json"), news)

    print(f"\nAll data saved to {out_dir}/")


if __name__ == "__main__":
    run_date = sys.argv[1] if len(sys.argv) > 1 else None
    run(run_date)
