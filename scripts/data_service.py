"""
Centralized data layer for all market data access.

All tools (Portfolio Analyzer, Hot Stocks Watcher, Chart + Sentiment)
import from here. No tool should call yfinance directly.

Public API:
    get_stock_price(ticker)          → single price dict
    get_multiple_prices(tickers)     → {ticker: price, ...}
    get_historical_data(ticker)      → OHLC DataFrame (single ticker)
    get_close_prices(tickers)        → Close DataFrame (multi-ticker, for portfolio math)
    get_hot_stocks()                 → ranked list of trending stocks
"""

from __future__ import annotations

import yfinance as yf
import pandas as pd


def get_stock_price(ticker: str) -> dict | None:
    """
    Return the latest available price for a single ticker.

    Returns:
        {"ticker": "AAPL", "price": 180.2, "currency": "USD"}
        or None if the ticker cannot be resolved.
    """
    try:
        info = yf.Ticker(ticker).fast_info
        price = info.get("lastPrice") or info.get("regularMarketPrice")
        if price is None:
            return None
        return {
            "ticker":   ticker.upper(),
            "price":    round(float(price), 4),
            "currency": info.get("currency", "USD"),
        }
    except Exception:
        return None


def get_multiple_prices(tickers: list[str]) -> dict[str, float | None]:
    """
    Return latest prices for a list of tickers.

    Returns:
        {"AAPL": 180.2, "MSFT": 410.5, "INVALID": None}
    """
    result = {}
    for ticker in tickers:
        data = get_stock_price(ticker)
        result[ticker.upper()] = data["price"] if data else None
    return result


def get_historical_data(ticker: str, period: str = "6mo") -> pd.DataFrame | None:
    """
    Return full OHLCV DataFrame for a single ticker.

    Args:
        ticker: e.g. "AAPL"
        period: yfinance period string — "1mo", "3mo", "6mo", "1y", "2y", "5y"

    Returns:
        DataFrame with columns [Open, High, Low, Close, Volume]
        or None if download fails.
    """
    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def get_hot_stocks(universe: list[str] | None = None, top_n: int = 5) -> list[dict]:
    """
    Rank stocks by short-term momentum and return the top N.

    Scoring (5-day window):
        score = return * 0.7 + volume_score * 0.3

    volume_score is the min-max normalised average daily volume across
    the universe, so all inputs to the score are on a comparable scale.

    Returns a list of dicts sorted by score descending, e.g.:
        [{"ticker": "NVDA", "return": 0.08, "volume_avg": 45_000_000, "score": 0.91}, ...]
    """
    from scripts.universe import get_stock_universe
    if universe is None:
        universe = get_stock_universe()

    try:
        raw = yf.download(universe, period="5d", auto_adjust=True, progress=False)
    except Exception:
        return []

    # Extract Close and Volume; handle single-ticker flat vs multi-ticker MultiIndex
    if isinstance(raw.columns, pd.MultiIndex):
        close  = raw["Close"]
        volume = raw["Volume"]
    else:
        close  = raw[["Close"]].rename(columns={"Close": universe[0]})
        volume = raw[["Volume"]].rename(columns={"Volume": universe[0]})

    records = []
    for ticker in universe:
        if ticker not in close.columns:
            continue
        prices = close[ticker].dropna()
        vols   = volume[ticker].dropna()
        if len(prices) < 2:
            continue

        period_return = float((prices.iloc[-1] / prices.iloc[0]) - 1)
        avg_volume    = float(vols.mean())
        records.append({"ticker": ticker, "return": period_return, "volume_avg": avg_volume})

    if not records:
        return []

    # Min-max normalise volume across the universe so it contributes fairly to score
    volumes   = [r["volume_avg"] for r in records]
    vol_min, vol_max = min(volumes), max(volumes)
    vol_range = vol_max - vol_min or 1  # guard against all-equal volumes

    for r in records:
        volume_score = (r["volume_avg"] - vol_min) / vol_range
        r["score"]   = round(r["return"] * 0.7 + volume_score * 0.3, 4)
        r["return"]  = round(r["return"], 4)
        r["volume_avg"] = int(r["volume_avg"])

    records.sort(key=lambda r: r["score"], reverse=True)
    return records[:top_n]


def get_close_prices(tickers: list[str], period: str = "6mo") -> pd.DataFrame:
    """
    Return a Close-price DataFrame for multiple tickers — used by portfolio math.

    Drops tickers with no data but does not raise. Callers should check
    which columns are present before proceeding.

    Returns:
        DataFrame indexed by date, one column per valid ticker.
    """
    try:
        data = yf.download(tickers, period=period, auto_adjust=True, progress=False)

        # yfinance returns a MultiIndex when multiple tickers are requested
        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"]
        else:
            # Single ticker returned as flat columns
            close = data[["Close"]].rename(columns={"Close": tickers[0].upper()})

        close = close.dropna(how="all")
        return close
    except Exception:
        return pd.DataFrame()
