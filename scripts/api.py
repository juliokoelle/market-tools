import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

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

    try:
        result = generate(today(), provider=provider)
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


@app.get("/briefing/{date}")
def briefing_get(date: str):
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    path = Path(f"outputs/{date}-briefing.md")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No briefing for {date}")

    import markdown as md_lib
    markdown_text = path.read_text(encoding="utf-8")
    return {
        "date": date,
        "markdown": markdown_text,
        "html_render": md_lib.markdown(markdown_text),
    }


@app.get("/briefing/{date}/pdf")
def briefing_pdf(date: str):
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    pdf_path = Path(f"outputs/pdf/{date}-briefing.pdf")
    if not pdf_path.exists():
        md_path = Path(f"outputs/{date}-briefing.md")
        if not md_path.exists():
            raise HTTPException(status_code=404, detail=f"No briefing for {date}")
        from scripts.render_pdf import render_pdf
        render_pdf(md_path.read_text(encoding="utf-8"), date)

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
# Market endpoints (unchanged)
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
