import base64
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
