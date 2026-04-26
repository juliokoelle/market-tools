import json
import logging
import os
import re
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_LATEST.parent.mkdir(parents=True, exist_ok=True)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# In-memory cache  {key: (monotonic_timestamp, value)}
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, object]] = {}
_TTL_SHORT = 60.0    # list + rate-limit check
_TTL_LONG  = 300.0   # briefing content


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
    if provider not in ("anthropic", "openai"):
        raise HTTPException(status_code=400, detail="provider must be 'anthropic' or 'openai'")

    from scripts.generate_briefing import generate
    from scripts.utils import today

    today_str = today()

    if _today_briefing_exists(today_str):
        tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit",
                "message": "Heutiges Briefing bereits generiert. Nächste Generierung ab Mitternacht (lokale Zeit).",
                "next_available": tomorrow.isoformat(),
            },
        )

    try:
        result = generate(today_str, provider=provider)
        # Mark as exists immediately so any request within the next 60 s gets 429
        _cache_set(f"exists:{today_str}", True)
        _cache_del("briefing_list")
        return {
            "date": result["date"],
            "markdown": result["markdown"],
            "cost_usd": result["cost_usd"],
        }
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logging.getLogger("briefing").error("generate failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")


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
        filename=f"{date}-briefing.pdf",
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
    """Legacy endpoint — delegates to POST /briefing/generate?provider=anthropic."""
    return briefing_generate(provider="anthropic")


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


@app.get("/market/hot-stocks")
def market_hot_stocks():
    stocks = get_hot_stocks(top_n=50)
    if not stocks:
        raise HTTPException(
            status_code=503, detail="Could not fetch market data. Try again shortly."
        )
    return {"stocks": stocks, "total": len(stocks)}


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
