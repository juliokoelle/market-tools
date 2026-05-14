import base64
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests as http_client
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

from scripts.data_service import get_multiple_prices, get_hot_stocks, get_historical_data
from scripts.portfolio import analyze_portfolio
from scripts.stock_analyzer import analyze_stock
from scripts.generate_briefing import OUTPUT_LATEST

app = FastAPI()


@app.on_event("startup")
async def _hf_startup():
    threading.Thread(target=_warm_geo_cache_bg, daemon=True).start()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

OUTPUT_LATEST.parent.mkdir(parents=True, exist_ok=True)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# In-memory cache  {key: (monotonic_timestamp, value)}
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, object]] = {}
_TTL_SHORT      = 60.0    # list + rate-limit check
_TTL_LONG       = 300.0   # briefing content
_TTL_BULL_SCORE = 300.0   # watchlist items (5 min)
_TTL_CHART      = 900.0   # OHLC chart data (15 min)
_TTL_AI_SUMMARY = 21600.0 # Sonnet summary (6 h)
_TTL_PORTFOLIO  = 30.0    # portfolio positions (30 s)

_PORTFOLIO_GH_PATH = "20_Career/investments/portfolio-current.json"


def _cache_get(key: str, ttl: float) -> object | None:
    entry = _cache.get(key)
    if entry and time.monotonic() - entry[0] < ttl:
        return entry[1]
    return None


def _cache_set(key: str, value: object) -> None:
    _cache[key] = (time.monotonic(), value)


def _cache_del(key: str) -> None:
    _cache.pop(key, None)


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def _gh_owner() -> str:
    return os.getenv("JULIO_BRAIN_OWNER", "juliokoelle")


def _gh_repo() -> str:
    return os.getenv("JULIO_BRAIN_REPO_NAME", "julio-brain")


def _gh_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    h = {"Accept": "application/vnd.github.v3+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _today_briefing_exists(today_str: str) -> bool:
    """Check GitHub (60 s cache) then fall back to local outputs/."""
    cache_key = f"exists:{today_str}"
    cached = _cache_get(cache_key, _TTL_SHORT)
    if cached is not None:
        return bool(cached)

    try:
        url = (
            f"https://api.github.com/repos/{_gh_owner()}/{_gh_repo()}"
            f"/contents/10_Daily/{today_str}.md"
        )
        resp = http_client.get(url, headers=_gh_headers(), timeout=10)
        exists = resp.status_code == 200
        _cache_set(cache_key, exists)
        return exists
    except Exception as e:
        logging.getLogger("briefing").warning("GitHub exists-check failed: %s", e)

    return Path(f"outputs/{today_str}-briefing.md").exists()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Holding(BaseModel):
    ticker: str
    investment: float


class PortfolioRequest(BaseModel):
    holdings: list[Holding]


class PortfolioHolding(BaseModel):
    ticker: str
    name: str
    shares: float
    investment: float
    purchase_date: str | None = None


class PortfolioHoldingsRequest(BaseModel):
    holdings: list[PortfolioHolding]


class PortfolioPosition(BaseModel):
    ticker: str
    amount_eur: float
    category: str  # "stock" | "etf" | "commodity"
    note: str = ""


class GHPortfolioWrite(BaseModel):
    positions: list[PortfolioPosition]


# ---------------------------------------------------------------------------
# GitHub portfolio helpers
# ---------------------------------------------------------------------------

_log_portfolio = logging.getLogger("portfolio")


def _gh_portfolio_read() -> tuple[dict | None, str | None]:
    """Read portfolio JSON from GitHub. Returns (data, sha) or (None, None)."""
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        return None, None
    url = (
        f"https://api.github.com/repos/{_gh_owner()}/{_gh_repo()}"
        f"/contents/{_PORTFOLIO_GH_PATH}"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        resp = http_client.get(url, headers=headers, timeout=10)
        if resp.status_code == 404:
            return None, None
        if resp.status_code != 200:
            _log_portfolio.warning("GitHub portfolio GET returned %s", resp.status_code)
            return None, None
        body = resp.json()
        sha = body.get("sha")
        raw = base64.b64decode(body["content"]).decode("utf-8")
        return json.loads(raw), sha
    except Exception as e:
        _log_portfolio.warning("GitHub portfolio read failed: %s", e)
        return None, None


def _gh_portfolio_write(data: dict, sha: str | None) -> bool:
    """Write portfolio JSON to GitHub. Returns True on success."""
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        return False
    url = (
        f"https://api.github.com/repos/{_gh_owner()}/{_gh_repo()}"
        f"/contents/{_PORTFOLIO_GH_PATH}"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    content_b64 = base64.b64encode(
        json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    date_str = data.get("last_updated", "")[:10]
    body: dict = {
        "message": f"portfolio: update positions {date_str}",
        "content": content_b64,
        "branch": "main",
    }
    if sha:
        body["sha"] = sha
    try:
        resp = http_client.put(url, headers=headers, json=body, timeout=20)
        if resp.status_code in (200, 201):
            return True
        _log_portfolio.warning(
            "GitHub portfolio PUT returned %s: %s", resp.status_code, resp.text[:200]
        )
        return False
    except Exception as e:
        _log_portfolio.error("GitHub portfolio write failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"message": "Daily Briefing API is running"}


# ---------------------------------------------------------------------------
# Briefing endpoints
# IMPORTANT: specific string paths (/list, /cost-summary) MUST be registered
# before the parameterised path (/{date}) or FastAPI will match them as dates.
# ---------------------------------------------------------------------------

@app.post("/briefing/generate")
def briefing_generate(provider: str = Query("anthropic")):
    raise HTTPException(
        status_code=410,
        detail={
            "error": "generation_disabled",
            "message": "Briefing wird täglich automatisch per E-Mail bezogen.",
        },
    )


@app.get("/briefing/list")
def briefing_list():
    cached = _cache_get("briefing_list", _TTL_SHORT)
    if cached is not None:
        return cached

    # Primary: GitHub directory listing
    try:
        url = (
            f"https://api.github.com/repos/{_gh_owner()}/{_gh_repo()}"
            f"/contents/10_Daily"
        )
        resp = http_client.get(url, headers=_gh_headers(), timeout=10)
        if resp.status_code == 200:
            pdf_dir = Path("outputs/pdf")
            briefings = []
            for f in resp.json():
                name = f.get("name", "")
                if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", name):
                    date_str = name[:-3]
                    has_pdf = (pdf_dir / f"{date_str}-briefing.pdf").exists()
                    briefings.append({"date": date_str, "has_pdf": has_pdf})
            briefings.sort(key=lambda x: x["date"], reverse=True)
            result = briefings[:30]
            _cache_set("briefing_list", result)
            return result
    except Exception as e:
        logging.getLogger("briefing").warning("GitHub list failed: %s", e)

    # Fallback: local outputs/
    outputs_dir = Path("outputs")
    pdf_dir = Path("outputs/pdf")
    briefings = []
    for f in sorted(outputs_dir.glob("????-??-??-briefing.md"), reverse=True):
        date_str = f.stem.replace("-briefing", "")
        has_pdf = (pdf_dir / f"{date_str}-briefing.pdf").exists()
        briefings.append({"date": date_str, "has_pdf": has_pdf})
    return briefings[:30]


@app.get("/briefing/cost-summary")
def briefing_cost_summary():
    log_path = Path("data/cost_log.json")

    if not log_path.exists():
        return {"current_month_cost": 0.0, "current_month_count": 0, "budget_usd": 15.00}

    try:
        entries = json.loads(log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"current_month_cost": 0.0, "current_month_count": 0, "budget_usd": 15.00}

    current_month = datetime.now().strftime("%Y-%m")
    monthly = [e for e in entries if e.get("date", "").startswith(current_month)]

    return {
        "current_month_cost": round(sum(e.get("cost_usd", 0) for e in monthly), 4),
        "current_month_count": len(monthly),
        "budget_usd": 15.00,
    }


def _extract_preview(text: str, max_chars: int = 250) -> str:
    """Strip YAML frontmatter and Markdown headers; truncate at word boundary."""
    s = text.strip()
    if s.startswith("---"):
        end = s.find("---", 3)
        if end != -1:
            s = s[end + 3:].strip()
    s = re.sub(r"^#{1,6}\s+.*$", "", s, flags=re.MULTILINE)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", s)
    s = re.sub(r"\n{2,}", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= max_chars:
        return s
    cut = s[:max_chars]
    last = cut.rfind(" ")
    if last > max_chars // 2:
        cut = cut[:last]
    return cut + "…"


@app.get("/briefing/today/preview")
def briefing_today_preview():
    cache_key = "briefing_today_preview"
    cached = _cache_get(cache_key, _TTL_SHORT)
    if cached is not None:
        return cached

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    markdown_text = _fetch_markdown_for_date(today_str)
    date_used = today_str

    if markdown_text is None:
        try:
            recent_list = briefing_list()
            if recent_list:
                date_used = recent_list[0]["date"]
                markdown_text = _fetch_markdown_for_date(date_used)
        except Exception:
            pass

    if markdown_text is None:
        result = {"date": None, "preview_text": None, "has_briefing": False}
    else:
        result = {
            "date": date_used,
            "preview_text": _extract_preview(markdown_text),
            "has_briefing": True,
        }

    _cache_set(cache_key, result)
    return result


def _fetch_markdown_for_date(date: str) -> str | None:
    """Fetch briefing markdown from GitHub, fall back to local outputs/."""
    try:
        token = os.getenv("GITHUB_TOKEN", "").strip()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        url = (
            f"https://raw.githubusercontent.com/{_gh_owner()}/{_gh_repo()}"
            f"/main/10_Daily/{date}.md"
        )
        resp = http_client.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        logging.getLogger("briefing").warning("GitHub fetch failed for %s: %s", date, e)

    path = Path(f"outputs/{date}-briefing.md")
    if path.exists():
        return path.read_text(encoding="utf-8")

    return None


@app.get("/briefing/{date}")
def briefing_get(date: str):
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    cache_key = f"briefing:{date}"
    cached = _cache_get(cache_key, _TTL_LONG)
    if cached is not None:
        return cached

    markdown_text = _fetch_markdown_for_date(date)
    if markdown_text is None:
        raise HTTPException(status_code=404, detail=f"No briefing for {date}")

    import markdown as md_lib
    result = {
        "date": date,
        "markdown": markdown_text,
        "html_render": md_lib.markdown(markdown_text),
    }
    _cache_set(cache_key, result)
    return result


@app.get("/briefing/{date}/pdf")
def briefing_pdf(date: str):
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    pdf_path = Path(f"outputs/pdf/{date}-briefing.pdf")
    if not pdf_path.exists():
        markdown_text = _fetch_markdown_for_date(date)
        if markdown_text is None:
            raise HTTPException(status_code=404, detail=f"No briefing for {date}")
        from scripts.render_pdf import render_pdf
        render_pdf(markdown_text, date)

    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="briefing-{date}.pdf"'},
    )


# ---------------------------------------------------------------------------
# Legacy briefing endpoints — kept for backwards compatibility
# ---------------------------------------------------------------------------

@app.get("/daily-briefing")
def get_daily_briefing():
    if not OUTPUT_LATEST.exists() or OUTPUT_LATEST.stat().st_size == 0:
        raise HTTPException(status_code=404, detail="No daily briefing available yet")
    content = OUTPUT_LATEST.read_text(encoding="utf-8")
    last_modified = OUTPUT_LATEST.stat().st_mtime
    last_updated = datetime.fromtimestamp(last_modified, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return {"status": "success", "briefing": content, "last_updated": last_updated}


@app.post("/generate-briefing")
def generate_briefing_legacy():
    """Legacy endpoint — disabled, use Gmail pipeline instead."""
    raise HTTPException(
        status_code=410,
        detail={
            "error": "generation_disabled",
            "message": "Briefing wird täglich automatisch per E-Mail bezogen.",
        },
    )


# ---------------------------------------------------------------------------
# Portfolio holdings persistence
# ---------------------------------------------------------------------------

PORTFOLIO_JSON = Path("data/portfolio.json")


@app.get("/portfolio/holdings")
def portfolio_holdings_get():
    if not PORTFOLIO_JSON.exists():
        return {"holdings": []}
    try:
        return {"holdings": json.loads(PORTFOLIO_JSON.read_text(encoding="utf-8"))}
    except (json.JSONDecodeError, OSError):
        return {"holdings": []}


@app.post("/portfolio/holdings")
def portfolio_holdings_save(request: PortfolioHoldingsRequest):
    PORTFOLIO_JSON.parent.mkdir(parents=True, exist_ok=True)
    data = [h.model_dump() for h in request.holdings]
    PORTFOLIO_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"saved": len(data)}


# ---------------------------------------------------------------------------
# Portfolio persistence (GitHub-backed)
# ---------------------------------------------------------------------------

@app.get("/portfolio")
def portfolio_get():
    cached = _cache_get("portfolio", _TTL_PORTFOLIO)
    if cached is not None:
        return cached
    data, _ = _gh_portfolio_read()
    if data is None:
        result = {"positions": [], "last_updated": None, "total_eur": 0}
    else:
        positions = data.get("positions", [])
        result = {
            "positions": positions,
            "last_updated": data.get("last_updated"),
            "total_eur": round(sum(p.get("amount_eur", 0) for p in positions), 2),
        }
    _cache_set("portfolio", result)
    return result


@app.post("/portfolio")
def portfolio_save(request: GHPortfolioWrite):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    positions = [p.model_dump() for p in request.positions]
    data = {
        "positions": positions,
        "last_updated": now,
        "total_eur": round(sum(p.get("amount_eur", 0) for p in positions), 2),
    }
    _, sha = _gh_portfolio_read()
    if not _gh_portfolio_write(data, sha):
        raise HTTPException(
            status_code=503,
            detail="Could not write to GitHub. Check GITHUB_TOKEN or try again shortly.",
        )
    _cache_del("portfolio")
    return {"saved": len(positions), "last_updated": now}


@app.post("/portfolio/position")
def portfolio_position_add(position: PortfolioPosition):
    data, sha = _gh_portfolio_read()
    positions: list[dict] = list(data.get("positions", [])) if data else []
    idx = next((i for i, p in enumerate(positions) if p.get("ticker") == position.ticker), -1)
    pos_dict = position.model_dump()
    if idx >= 0:
        positions[idx] = pos_dict
    else:
        positions.append(pos_dict)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_data = {
        "positions": positions,
        "last_updated": now,
        "total_eur": round(sum(p.get("amount_eur", 0) for p in positions), 2),
    }
    if not _gh_portfolio_write(new_data, sha):
        raise HTTPException(status_code=503, detail="Could not write to GitHub.")
    _cache_del("portfolio")
    return {"saved": True, "positions": len(positions), "last_updated": now}


@app.delete("/portfolio/position/{ticker}")
def portfolio_position_delete(ticker: str):
    data, sha = _gh_portfolio_read()
    if data is None:
        raise HTTPException(status_code=404, detail="Portfolio not found.")
    upper = ticker.upper()
    positions = [p for p in data.get("positions", []) if p.get("ticker") != upper]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_data = {
        "positions": positions,
        "last_updated": now,
        "total_eur": round(sum(p.get("amount_eur", 0) for p in positions), 2),
    }
    if not _gh_portfolio_write(new_data, sha):
        raise HTTPException(status_code=503, detail="Could not write to GitHub.")
    _cache_del("portfolio")
    return {"deleted": upper, "positions": len(positions)}


# ---------------------------------------------------------------------------
# Market endpoints
# ---------------------------------------------------------------------------

@app.get("/market/prices")
def market_prices(
    tickers: str = Query(..., description="Comma-separated list of tickers, e.g. AAPL,MSFT,TSLA")
):
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="No tickers provided.")
    return {"prices": get_multiple_prices(ticker_list)}


@app.get("/market/history")
def market_history(
    ticker: str = Query(..., description="Ticker symbol, e.g. AAPL"),
    period: str = Query("6mo", description="yfinance period: 1mo, 3mo, 6mo, 1y"),
):
    df = get_historical_data(ticker.upper(), period=period)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No historical data for {ticker.upper()}.")
    close = df["Close"].dropna()
    return {
        "ticker": ticker.upper(),
        "period": period,
        "prices": [
            {"date": str(d.date()), "close": round(float(v), 2)} for d, v in close.items()
        ],
    }


_TTL_TICKER_BANNER  = 60.0
_TTL_DASHBOARD      = 120.0
_TTL_HOT_ENRICHED   = 300.0

_BANNER_TICKERS    = ["GC=F", "^GSPC", "^IXIC", "BTC-USD", "VWCE.DE", "AAPL", "NVDA", "MSFT"]
_WATCHLIST_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "JPM"]


def _sparkline(ticker: str, period: str = "5d", interval: str = "1h") -> list:
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=period, interval=interval)
        if hist.empty:
            return []
        return [round(float(v), 2) for v in hist["Close"].dropna().values[-40:]]
    except Exception:
        return []


@app.get("/ticker-banner")
def ticker_banner():
    cached = _cache_get("ticker_banner", _TTL_TICKER_BANNER)
    if cached is not None:
        return cached

    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor

    def _fetch_one(ticker: str) -> dict:
        try:
            fi    = yf.Ticker(ticker).fast_info
            price = fi.get("lastPrice") or fi.get("regularMarketPrice")
            prev  = fi.get("previousClose") or fi.get("regularMarketPreviousClose")
            chg   = (price - prev) / prev * 100 if price and prev and prev != 0 else 0.0
            return {
                "ticker": ticker,
                "price":  round(float(price), 2) if price else None,
                "change_pct": round(float(chg), 2),
            }
        except Exception:
            return {"ticker": ticker, "price": None, "change_pct": 0.0}

    with ThreadPoolExecutor(max_workers=8) as ex:
        result = list(ex.map(_fetch_one, _BANNER_TICKERS))

    _cache_set("ticker_banner", result)
    return result


@app.get("/dashboard-overview")
def dashboard_overview():
    cached = _cache_get("dashboard_overview", _TTL_DASHBOARD)
    if cached is not None:
        return cached

    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor

    def _fetch_watchlist(ticker: str) -> dict:
        try:
            fi    = yf.Ticker(ticker).fast_info
            price = fi.get("lastPrice") or fi.get("regularMarketPrice")
            prev  = fi.get("previousClose") or fi.get("regularMarketPreviousClose")
            chg   = (price - prev) / prev * 100 if price and prev and prev != 0 else 0.0
            return {
                "ticker":     ticker,
                "price":      round(float(price), 2) if price else None,
                "change_pct": round(float(chg), 2),
                "sparkline":  _sparkline(ticker),
            }
        except Exception:
            return {"ticker": ticker, "price": None, "change_pct": 0.0, "sparkline": []}

    with ThreadPoolExecutor(max_workers=8) as ex:
        watchlist = list(ex.map(_fetch_watchlist, _WATCHLIST_TICKERS))

    result = {
        "watchlist": watchlist,
        "sp500_sparkline": _sparkline("^GSPC", period="7d", interval="1d"),
    }
    _cache_set("dashboard_overview", result)
    return result


@app.get("/market/hot-stocks")
def market_hot_stocks():
    cached = _cache_get("hot_stocks_enriched", _TTL_HOT_ENRICHED)
    if cached is not None:
        return cached

    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor

    stocks = get_hot_stocks(top_n=20)
    if not stocks:
        raise HTTPException(status_code=503, detail="Could not fetch market data. Try again shortly.")

    def _enrich(s: dict) -> dict:
        ticker = s["ticker"]
        try:
            info  = yf.Ticker(ticker).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            prev  = info.get("previousClose") or 0
            chg   = (price - prev) / prev * 100 if prev else s.get("return", 0) * 100
            return {
                **s,
                "name":           info.get("shortName") or info.get("longName") or ticker,
                "price":          round(float(price), 2) if price else None,
                "change_pct":     round(float(chg), 2),
                "pe_ratio":       info.get("trailingPE"),
                "week_52_high":   info.get("fiftyTwoWeekHigh"),
                "week_52_low":    info.get("fiftyTwoWeekLow"),
                "analyst_rating": info.get("recommendationKey"),
                "sparkline":      _sparkline(ticker, period="5d", interval="1d"),
            }
        except Exception:
            return {
                **s,
                "name": ticker, "price": None,
                "change_pct": round(s.get("return", 0) * 100, 2),
                "pe_ratio": None, "week_52_high": None,
                "week_52_low": None, "analyst_rating": None, "sparkline": [],
            }

    with ThreadPoolExecutor(max_workers=10) as ex:
        enriched = list(ex.map(_enrich, stocks))

    result = {"stocks": enriched, "total": len(enriched)}
    _cache_set("hot_stocks_enriched", result)
    return result


@app.get("/stock/analyze")
def stock_analyze(ticker: str = Query(..., description="Ticker symbol, e.g. AAPL")):
    try:
        return analyze_stock(ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/portfolio/analyze")
def portfolio_analyze(request: PortfolioRequest):
    return analyze_portfolio(
        [{"ticker": h.ticker, "investment": h.investment} for h in request.holdings]
    )


# ---------------------------------------------------------------------------
# Stock Analyzer 2.0 — Watchlist + scoring endpoints
# ---------------------------------------------------------------------------

def _load_watchlist_categories() -> list[dict]:
    import yaml
    path = Path(__file__).parent.parent / "config" / "watchlist.yaml"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("categories", [])


def _score_one_ticker(ticker: str) -> dict:
    """Bull score with API-level cache (5 min)."""
    cache_key = f"bull:{ticker}"
    cached = _cache_get(cache_key, _TTL_BULL_SCORE)
    if cached is not None:
        return cached
    from scripts.scoring import bull_score
    result = bull_score(ticker)
    _cache_set(cache_key, result)
    return result


@app.get("/watchlist")
def get_watchlist():
    from concurrent.futures import ThreadPoolExecutor

    categories = _load_watchlist_categories()
    if not categories:
        raise HTTPException(status_code=503, detail="Watchlist config not found.")

    all_tickers = [t for cat in categories for t in cat["tickers"]]

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {ticker: executor.submit(_score_one_ticker, ticker) for ticker in all_tickers}
        scores = {ticker: fut.result() for ticker, fut in futures.items()}

    result = []
    for cat in categories:
        items = [scores.get(t, {"ticker": t, "bull_score": 50, "components": {}, "is_crypto": False})
                 for t in cat["tickers"]]
        result.append({"name": cat["name"], "tickers": items})

    return {"categories": result}


@app.get("/stock/{ticker}/detail")
def stock_detail(ticker: str):
    ticker = ticker.upper()
    cache_key = f"detail:{ticker}"
    cached = _cache_get(cache_key, _TTL_BULL_SCORE)
    if cached is not None:
        return cached

    from scripts.scoring import bull_score
    import yfinance as yf

    score_data = bull_score(ticker)

    try:
        info = yf.Ticker(ticker).info
        detail = {
            **score_data,
            "company_name": info.get("longName") or info.get("shortName") or ticker,
            "sector":       info.get("sector"),
            "industry":     info.get("industry"),
            "market_cap":   info.get("marketCap"),
            "currency":     info.get("currency", "USD"),
            "description":  (info.get("longBusinessSummary") or "")[:500],
        }
    except Exception:
        detail = {**score_data, "company_name": ticker}

    _cache_set(cache_key, detail)
    return detail


@app.get("/stock/{ticker}/chart")
def stock_chart(
    ticker: str,
    period: str = Query("3mo", description="1mo, 3mo, 6mo, 1y"),
):
    ticker = ticker.upper()
    if period not in ("1mo", "3mo", "6mo", "1y"):
        period = "3mo"

    cache_key = f"chart:{ticker}:{period}"
    cached = _cache_get(cache_key, _TTL_CHART)
    if cached is not None:
        return cached

    import yfinance as yf
    df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No chart data for {ticker}")

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    rows = []
    for dt, row in df.iterrows():
        try:
            vol = row.get("Volume", 0)
            rows.append({
                "date":   str(dt.date()),
                "open":   round(float(row["Open"]), 2),
                "high":   round(float(row["High"]), 2),
                "low":    round(float(row["Low"]), 2),
                "close":  round(float(row["Close"]), 2),
                "volume": int(vol) if vol == vol else 0,
            })
        except (ValueError, TypeError):
            continue  # skip rows with NaN OHLC values

    result = {"ticker": ticker, "period": period, "ohlcv": rows}
    _cache_set(cache_key, result)
    return result


@app.get("/stock/{ticker}/ai-summary")
def stock_ai_summary(ticker: str):
    ticker = ticker.upper()
    cache_key = f"ai_summary:{ticker}"
    cached = _cache_get(cache_key, _TTL_AI_SUMMARY)
    if cached is not None:
        return cached

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")

    from scripts.scoring import bull_score
    import anthropic
    import yfinance as yf

    score_data = bull_score(ticker)

    try:
        info = yf.Ticker(ticker).info
        company_name = info.get("longName") or info.get("shortName") or ticker
        sector       = info.get("sector", "N/A")
        price        = info.get("currentPrice") or info.get("regularMarketPrice") or "N/A"
    except Exception:
        company_name, sector, price = ticker, "N/A", "N/A"

    comp  = score_data.get("components", {})
    mom   = comp.get("momentum",  {})
    sent  = comp.get("sentiment", {})
    val   = comp.get("valuation")
    anal  = comp.get("analyst")

    val_line  = (f"P/E {val['details'].get('trailing_pe')} / fwd {val['details'].get('forward_pe')} / P/B {val['details'].get('price_to_book')}"
                 if val and val.get("details") else "N/A")
    anal_line = (f"{anal['details'].get('recommendation')} (mean {anal['details'].get('recommendation_mean')}, "
                 f"{anal['details'].get('analyst_count')} analysts)"
                 if anal and anal.get("details") else "N/A")

    prompt = (
        f"Analyze {company_name} ({ticker}):\n"
        f"Price: {price} | Bull Score: {score_data['bull_score']}/100 | Sector: {sector}\n"
        f"Momentum {int(mom.get('weight',0)*100)}%: {mom.get('score',50):.0f}/100 | "
        f"30d {mom.get('details',{}).get('return_30d')}% | 90d {mom.get('details',{}).get('return_90d')}% | "
        f"Above MA50: {mom.get('details',{}).get('above_ma50')} / MA200: {mom.get('details',{}).get('above_ma200')}\n"
        f"Sentiment {int(sent.get('weight',0)*100)}%: {sent.get('score',50):.0f}/100 ({sent.get('details',{}).get('label')})\n"
        f"Valuation 20%: {val.get('score','N/A') if val else 'N/A'}/100 — {val_line}\n"
        f"Analyst 20%: {anal.get('score','N/A') if anal else 'N/A'}/100 — {anal_line}\n\n"
        "Write a 2-3 paragraph investment analysis in the style of a Bloomberg brief. "
        "Be analytical, not promotional. Cover: current outlook, key risks, what to monitor."
    )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    result = {
        "ticker":       ticker,
        "summary":      response.content[0].text.strip(),
        "bull_score":   score_data["bull_score"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache_set(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Ticker profile
# ---------------------------------------------------------------------------

_TTL_TICKER_PROFILE = 86400.0  # 24 h

_TICKER_FALLBACK_DESC: dict[str, str] = {
    "VWCE.DE": (
        "Vanguard FTSE All-World UCITS ETF — tracks ~4,000 large/mid-cap stocks worldwide "
        "across 49 countries. TER 0.19%. Single-instrument exposure to global equities, "
        "market-cap weighted. Domiciled in Ireland, distributing variant available as VWRL."
    ),
    "4GLD.DE": (
        "Xetra-Gold — physically backed gold ETC. Each unit represents 1 gram of gold stored "
        "in Deutsche Börse Commodities' vaults in Frankfurt. Physical delivery possible. "
        "Tax-free after 1-year holding period under German law (§23 EStG). TER ~0.36% p.a."
    ),
}

_log_ticker = logging.getLogger("ticker")


@app.get("/ticker/{ticker}/profile")
def ticker_profile(ticker: str):
    ticker = ticker.upper()
    cache_key = f"profile:{ticker}"
    cached = _cache_get(cache_key, _TTL_TICKER_PROFILE)
    if cached is not None:
        return cached

    import yfinance as yf

    try:
        info = yf.Ticker(ticker).info
        if not info or not (info.get("symbol") or info.get("shortName")):
            raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found.")

        quote_type = info.get("quoteType", "")
        is_etf = (
            quote_type in ("ETF", "MUTUALFUND")
            or bool(info.get("fundFamily"))
            or bool(info.get("categoryName"))
        )

        raw_desc = (
            info.get("longBusinessSummary")
            or info.get("description")
            or _TICKER_FALLBACK_DESC.get(ticker, "")
        )
        description = (raw_desc[:800] if raw_desc else _TICKER_FALLBACK_DESC.get(ticker, ""))

        raw_price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("navPrice")
        )
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        change_pct = None
        if raw_price and prev_close and prev_close != 0:
            change_pct = (raw_price - prev_close) / prev_close * 100

        result = {
            "ticker":         ticker,
            "name":           info.get("longName") or info.get("shortName") or ticker,
            "sector":         "ETF" if is_etf else (info.get("sector") or "—"),
            "industry":       None if is_etf else (info.get("industry") or "—"),
            "description":    description,
            "country":        info.get("country") or "—",
            "exchange":       info.get("exchange") or "—",
            "market_cap":     None if is_etf else info.get("marketCap"),
            "total_assets":   info.get("totalAssets") if is_etf else None,
            "pe_ratio":       None if is_etf else info.get("trailingPE"),
            "forward_pe":     None if is_etf else info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
            "beta":           None if is_etf else info.get("beta"),
            "week52_high":    info.get("fiftyTwoWeekHigh"),
            "week52_low":     info.get("fiftyTwoWeekLow"),
            "website":        info.get("website") or "—",
            "price":          raw_price,
            "change_pct":     change_pct,
            "currency":       info.get("currency", "USD"),
            "is_etf":         is_etf,
        }
        _cache_set(cache_key, result)
        return result

    except HTTPException:
        raise
    except Exception as e:
        _log_ticker.error("yfinance profile failed for %s: %s", ticker, e)
        raise HTTPException(
            status_code=503,
            detail=f"Could not load profile for {ticker}. Yahoo Finance may be temporarily unavailable.",
        )


# ---------------------------------------------------------------------------
# HorseFinder — equestrian tournament finder
# ---------------------------------------------------------------------------

_hf_client = None

# German discipline name → API slug
_DISC_MAP = {
    "Springen":       "show_jumping",
    "Dressur":        "dressage",
    "Vielseitigkeit": "eventing",
    "Fahren":         "driving",
    "Voltigieren":    "vaulting",
    "Breitensport":   "leisure",
}
# Reverse map: API slug → German (for query filtering)
_DISC_MAP_REV = {v: k for k, v in _DISC_MAP.items()}

# In-memory geocoding cache: city → (lat, lng)
_geo_cache: dict[str, tuple[float, float]] = {}
_geo_lock = threading.Lock()
_geo_last_req_time = 0.0


def _get_hf_client():
    global _hf_client
    if _hf_client is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            return None
        from supabase import create_client
        _hf_client = create_client(url, key)
    return _hf_client


def _hf_date_iso(d: str | None) -> str:
    """Convert DD.MM.YYYY → YYYY-MM-DD; pass ISO dates through unchanged."""
    if not d:
        return ""
    if "." in d:
        p = d.split(".")
        if len(p) == 3:
            return f"{p[2]}-{p[1]}-{p[0]}"
    return d


def _geocode_city(city: str) -> tuple[float, float]:
    """Geocode a German city via Nominatim. Rate-limited to 1 req/sec."""
    global _geo_last_req_time
    if city in _geo_cache:
        return _geo_cache[city]
    with _geo_lock:
        if city in _geo_cache:  # double-checked after lock
            return _geo_cache[city]
        elapsed = time.time() - _geo_last_req_time
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)
        try:
            resp = http_client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": city, "country": "Germany", "format": "json", "limit": 1},
                headers={"User-Agent": "horsefinder-app/1.0 (personal project)"},
                timeout=5,
            )
            _geo_last_req_time = time.time()
            data = resp.json()
            if data:
                coords = (float(data[0]["lat"]), float(data[0]["lon"]))
                _geo_cache[city] = coords
                return coords
        except Exception as exc:
            logging.warning("Geocode failed for %r: %s", city, exc)
            _geo_last_req_time = time.time()
        _geo_cache[city] = (0.0, 0.0)
        return (0.0, 0.0)


def _geo_persist(city: str, lat: float, lng: float) -> None:
    """Write geocoded coordinates back to Supabase for all events in this city."""
    sb = _get_hf_client()
    if sb is None or lat == 0.0:
        return
    try:
        sb.from_("events").update({"lat": lat, "lng": lng}).eq("city", city).execute()
    except Exception as exc:
        logging.warning("Geo persist failed for %r: %s", city, exc)


def _warm_geo_cache_bg():
    """Background: geocode cities that have no coordinates in DB, persist results."""
    sb = _get_hf_client()
    if sb is None:
        return
    try:
        # Load already-geocoded coordinates from DB into memory cache first
        resp = sb.from_("events").select("city,lat,lng").execute()
        pre_loaded = 0
        for r in resp.data:
            city = r.get("city", "")
            lat = r.get("lat") or 0.0
            lng = r.get("lng") or 0.0
            if city and lat != 0.0 and city not in _geo_cache:
                _geo_cache[city] = (lat, lng)
                pre_loaded += 1

        # Find cities that still need geocoding
        ungeoced = list({r["city"] for r in resp.data
                         if r.get("city") and (r.get("lat") or 0.0) == 0.0
                         and r["city"] not in _geo_cache})
        logging.info("HorseFinder: %d cities pre-loaded from DB, %d need geocoding", pre_loaded, len(ungeoced))

        for city in ungeoced:
            lat, lng = _geocode_city(city)
            if lat != 0.0:
                _geo_persist(city, lat, lng)

        logging.info("HorseFinder: geo cache ready (%d entries)", len(_geo_cache))
    except Exception as exc:
        logging.warning("Geo warmup failed: %s", exc)


def _hf_map(row: dict, dist_km: float | None = None) -> dict:
    country = row.get("country", "DE")
    if country == "Germany":
        country = "DE"
    start = _hf_date_iso(row.get("start_date", ""))
    end = _hf_date_iso(row.get("end_date") or row.get("start_date", ""))
    city = row.get("city", "")

    # Prefer DB coordinates → memory cache → fallback 0,0
    db_lat = row.get("lat") or 0.0
    db_lng = row.get("lng") or 0.0
    if db_lat != 0.0:
        lat, lng = db_lat, db_lng
    else:
        lat, lng = _geo_cache.get(city, (0.0, 0.0))

    raw_disc = row.get("discipline") or "Unknown"
    discipline = _DISC_MAP.get(raw_disc, "unknown")
    raw_levels = row.get("levels") or []
    levels = [lv for lv in raw_levels if lv and lv != "Unknown"]
    return {
        "id":         row["id"],
        "name":       row.get("title", ""),
        "city":       city,
        "state":      row.get("state", ""),
        "country":    country,
        "date_start": start,
        "date_end":   end,
        "discipline": discipline,
        "levels":     levels,
        "lat":        lat,
        "lng":        lng,
        "source_url": row.get("source_url"),
        "distance":   round(dist_km) if dist_km is not None else None,
    }


@app.get("/horsefinder/events")
def hf_list_events(
    discipline: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    city: str | None = None,
    levels: list[str] | None = Query(default=None),
    lat: float | None = None,
    lng: float | None = None,
    radius_km: int | None = None,
    bounds_n: float | None = None,
    bounds_s: float | None = None,
    bounds_e: float | None = None,
    bounds_w: float | None = None,
):
    sb = _get_hf_client()
    if sb is None:
        raise HTTPException(503, "HorseFinder not configured (SUPABASE_URL/SUPABASE_KEY missing)")

    # Map API slug back to German for DB filter
    db_discipline = _DISC_MAP_REV.get(discipline) if discipline else None

    # Standard table query — date/bounds filtering in Python (DB stores DD.MM.YYYY)
    query = sb.from_("events").select("*")
    if db_discipline:
        query = query.eq("discipline", db_discipline)
    elif discipline == "unknown":
        query = query.eq("discipline", "Unknown")
    if city:
        q = f"%{city}%"
        query = query.ilike("city", q)

    resp = query.execute()
    if resp.data is None:
        raise HTTPException(502, "Supabase query error")

    events = [_hf_map(r) for r in resp.data]

    # Date filtering
    if date_from:
        events = [e for e in events if e["date_start"] >= date_from]
    if date_to:
        events = [e for e in events if e["date_start"] <= date_to]

    # Bounds filtering (uses cached geocoords)
    if all(v is not None for v in (bounds_n, bounds_s, bounds_e, bounds_w)):
        events = [e for e in events
                  if e["lat"] != 0.0 and
                     bounds_s <= e["lat"] <= bounds_n and
                     bounds_w <= e["lng"] <= bounds_e]

    # Geo-radius filtering
    if lat is not None and lng is not None and radius_km:
        from math import radians, cos, sin, asin, sqrt
        def _haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            return 2 * R * asin(sqrt(a))
        filtered = []
        for e in events:
            if e["lat"] == 0.0 and e["lng"] == 0.0:
                continue
            dist = _haversine(lat, lng, e["lat"], e["lng"])
            if dist <= radius_km:
                e["distance"] = round(dist)
                filtered.append(e)
        events = filtered

    events.sort(key=lambda e: e["date_start"])
    return events


@app.get("/horsefinder/events/{event_id}")
def hf_get_event(event_id: str):
    sb = _get_hf_client()
    if sb is None:
        raise HTTPException(503, "HorseFinder not configured")
    resp = sb.from_("events").select("*").eq("id", event_id).maybe_single().execute()
    if not resp.data:
        raise HTTPException(404, "Event not found")
    event = _hf_map(resp.data)
    # Geocode on demand for detail page if not yet cached
    if event["lat"] == 0.0 and event["city"]:
        lat, lng = _geocode_city(event["city"])
        event["lat"], event["lng"] = lat, lng
    return event


# ---------------------------------------------------------------------------
# MyWardrobe — personal clothing catalog
# ---------------------------------------------------------------------------

class _WardrobeBody(BaseModel):
    name: str
    brand: str | None = None
    imageUrl: str | None = None
    imageThumbnailUrl: str | None = None
    categoryGender: str = "Unisex"
    categoryMain: str = "Tops"
    categorySub: str | None = None
    colors: list[str] = []
    size: str = ""
    material: str | None = None
    condition: str | None = None
    season: str | None = None
    tags: list[str] = []
    notes: str | None = None
    aiSuggested: bool = False
    aiConfidence: float | None = None
    sourceUrl: str | None = None


def _wdi_map(row: dict) -> dict:
    return {
        "id":                row["id"],
        "name":              row["name"],
        "brand":             row.get("brand"),
        "imageUrl":          row.get("image_url"),
        "imageThumbnailUrl": row.get("image_thumbnail_url"),
        "categoryGender":    row.get("category_gender", "Unisex"),
        "categoryMain":      row.get("category_main", "Tops"),
        "categorySub":       row.get("category_sub"),
        "colors":            row.get("colors") or [],
        "size":              row.get("size") or "",
        "material":          row.get("material"),
        "condition":         row.get("condition"),
        "season":            row.get("season"),
        "tags":              row.get("tags") or [],
        "notes":             row.get("notes"),
        "aiSuggested":       row.get("ai_suggested", False),
        "aiConfidence":      row.get("ai_confidence"),
        "sourceUrl":         row.get("source_url"),
        "createdAt":         row.get("created_at", ""),
        "updatedAt":         row.get("updated_at", ""),
    }


def _wdi_to_db(body: _WardrobeBody) -> dict:
    return {
        "user_id":              "julio",
        "name":                 body.name,
        "brand":                body.brand,
        "image_url":            body.imageUrl,
        "image_thumbnail_url":  body.imageThumbnailUrl,
        "category_gender":      body.categoryGender,
        "category_main":        body.categoryMain,
        "category_sub":         body.categorySub,
        "colors":               body.colors,
        "size":                 body.size,
        "material":             body.material,
        "condition":            body.condition,
        "season":               body.season,
        "tags":                 body.tags,
        "notes":                body.notes,
        "ai_suggested":         body.aiSuggested,
        "ai_confidence":        body.aiConfidence,
        "source_url":           body.sourceUrl,
    }


@app.get("/wardrobe/items")
def wdi_list(
    category: str | None = None,
    color: str | None = None,
    brand: str | None = None,
    gender: str | None = None,
    season: str | None = None,
):
    sb = _get_hf_client()
    if sb is None:
        raise HTTPException(503, "Wardrobe not configured (SUPABASE_URL/SUPABASE_KEY missing)")
    q = sb.from_("wardrobe_items").select("*").eq("user_id", "julio")
    if category:
        q = q.eq("category_main", category)
    if gender:
        q = q.eq("category_gender", gender)
    if season:
        q = q.eq("season", season)
    if brand:
        q = q.ilike("brand", f"%{brand}%")
    if color:
        q = q.contains("colors", [color])
    resp = q.order("created_at", desc=True).execute()
    if resp.data is None:
        raise HTTPException(502, "Supabase query error")
    return [_wdi_map(r) for r in resp.data]


@app.post("/wardrobe/items", status_code=201)
def wdi_create(body: _WardrobeBody):
    sb = _get_hf_client()
    if sb is None:
        raise HTTPException(503, "Wardrobe not configured")
    resp = sb.from_("wardrobe_items").insert(_wdi_to_db(body)).execute()
    if not resp.data:
        raise HTTPException(502, "Insert failed")
    return _wdi_map(resp.data[0])


@app.put("/wardrobe/items/{item_id}")
def wdi_update(item_id: str, body: _WardrobeBody):
    sb = _get_hf_client()
    if sb is None:
        raise HTTPException(503, "Wardrobe not configured")
    updates = {k: v for k, v in _wdi_to_db(body).items() if k != "user_id"}
    updates["updated_at"] = "now()"
    resp = (
        sb.from_("wardrobe_items")
        .update(updates)
        .eq("id", item_id)
        .eq("user_id", "julio")
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Item not found")
    return _wdi_map(resp.data[0])


@app.delete("/wardrobe/items/{item_id}", status_code=204)
def wdi_delete(item_id: str):
    sb = _get_hf_client()
    if sb is None:
        raise HTTPException(503, "Wardrobe not configured")
    sb.from_("wardrobe_items").delete().eq("id", item_id).eq("user_id", "julio").execute()
    return None


# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------

@app.get("/debug/env")
def debug_env():
    return {
        "TWELVE_DATA_API_KEY": bool(os.getenv("TWELVE_DATA_API_KEY")),
        "NEWS_API_KEY": bool(os.getenv("NEWS_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "GITHUB_TOKEN": bool(os.getenv("GITHUB_TOKEN")),
        "JULIO_BRAIN_OWNER": os.getenv("JULIO_BRAIN_OWNER", ""),
        "JULIO_BRAIN_REPO_NAME": os.getenv("JULIO_BRAIN_REPO_NAME", ""),
    }
