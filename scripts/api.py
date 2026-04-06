from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel

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
    if not OUTPUT_FILE.exists():
        raise HTTPException(status_code=404, detail="Briefing file not found")

    content = OUTPUT_FILE.read_text(encoding="utf-8")
    return {
        "status": "success",
        "briefing": content,
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