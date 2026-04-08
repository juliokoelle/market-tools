import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

from scripts.data_service import get_multiple_prices, get_hot_stocks, get_historical_data
from scripts.portfolio import analyze_portfolio
from scripts.stock_analyzer import analyze_stock

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_FILE = Path("outputs/latest-briefing.md")

# Ensure the outputs directory exists at startup so writes never fail
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Holding(BaseModel):
    ticker: str
    investment: float   # USD amount invested in this position


class PortfolioRequest(BaseModel):
    holdings: list[Holding]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"message": "Daily Briefing API is running"}


@app.get("/daily-briefing")
def get_daily_briefing():
    if not OUTPUT_FILE.exists() or OUTPUT_FILE.stat().st_size == 0:
        raise HTTPException(status_code=404, detail="No daily briefing available yet")

    try:
        content = OUTPUT_FILE.read_text(encoding="utf-8")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Could not read briefing: {e}")

    last_modified = OUTPUT_FILE.stat().st_mtime
    last_updated  = datetime.fromtimestamp(last_modified, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "status": "success",
        "briefing": content,
        "last_updated": last_updated,
    }


@app.post("/generate-briefing")
def generate_briefing():
    """
    Manually trigger a full briefing pipeline run:
      1. Fetch fresh market data
      2. Build prompt from fetched data
      3. Generate briefing via Anthropic API
      4. Overwrite outputs/latest-briefing.md
    """
    log = logging.getLogger("generate-briefing")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not configured on the server.")

    log.info("Starting manual briefing generation")

    from scripts.utils import today, output_path
    from scripts.fetch_data import run as fetch_run
    from scripts.generate_briefing import build_prompt

    run_date = today()

    # ── 1. Fetch data ──────────────────────────────────────────────────────
    log.info("Fetching data…")
    try:
        fetch_run(run_date)
    except Exception as e:
        log.error("Data fetch failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Data fetch failed: {e}")

    # ── 2. Build prompt ────────────────────────────────────────────────────
    try:
        prompt = build_prompt(run_date)
    except Exception as e:
        log.error("Prompt build failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Prompt build failed: {e}")

    # ── 3. Generate via Anthropic ──────────────────────────────────────────
    log.info("Generating briefing…")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=(
                "You are a senior economic journalist producing the Daily Global Economic "
                "Newspaper Briefing. Follow all editorial standards exactly as instructed. "
                "Write in continuous journalistic prose. No bullet lists in the final output."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        briefing_text = message.content[0].text
    except Exception as e:
        log.error("Anthropic API call failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Briefing generation failed: {e}")

    # ── 4. Save ────────────────────────────────────────────────────────────
    log.info("Saving latest briefing…")
    header  = f"# Daily Global Economic Briefing — {run_date}\n\n"
    content = header + briefing_text

    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(content, encoding="utf-8")

        archive = Path(output_path(run_date))
        archive.write_text(content, encoding="utf-8")
    except OSError as e:
        log.error("File write failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Could not save briefing: {e}")

    log.info("Saved latest briefing → %s", OUTPUT_FILE)

    return {
        "status":   "success",
        "message":  "Briefing generated successfully",
        "date":     run_date,
        "words":    len(briefing_text.split()),
    }


@app.get("/market/prices")
def market_prices(tickers: str = Query(..., description="Comma-separated list of tickers, e.g. AAPL,MSFT,TSLA")):
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="No tickers provided.")
    prices = get_multiple_prices(ticker_list)
    return {"prices": prices}


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
        "ticker":  ticker.upper(),
        "period":  period,
        "prices": [{"date": str(d.date()), "close": round(float(v), 2)} for d, v in close.items()],
    }


@app.get("/market/hot-stocks")
def market_hot_stocks():
    stocks = get_hot_stocks(top_n=50)
    if not stocks:
        raise HTTPException(status_code=503, detail="Could not fetch market data. Try again shortly.")
    return {"stocks": stocks, "total": len(stocks)}


@app.get("/stock/analyze")
def stock_analyze(ticker: str = Query(..., description="Ticker symbol, e.g. AAPL")):
    try:
        return analyze_stock(ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/portfolio/analyze")
def portfolio_analyze(request: PortfolioRequest):
    result = analyze_portfolio(
        [{"ticker": h.ticker, "investment": h.investment} for h in request.holdings]
    )
    return result