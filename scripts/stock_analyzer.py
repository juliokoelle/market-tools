"""
Single-stock analysis: technicals + sentiment.

Public API:
    analyze_stock(ticker) → dict
"""

from __future__ import annotations

import os
import numpy as np
import requests
from dotenv import load_dotenv

from scripts.data_service import get_historical_data

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# ---------------------------------------------------------------------------
# Sentiment keyword sets
# ---------------------------------------------------------------------------

_POSITIVE = {
    "surge", "soar", "gain", "rise", "rally", "profit", "beat", "record",
    "strong", "growth", "bullish", "upgrade", "buy", "outperform", "boom",
    "expand", "breakthrough", "milestone", "revenue", "dividend",
}

_NEGATIVE = {
    "fall", "drop", "plunge", "loss", "miss", "weak", "decline", "bearish",
    "downgrade", "sell", "crash", "lawsuit", "investigation", "fine", "fraud",
    "layoff", "cut", "warning", "risk", "concern", "debt", "default", "recall",
}


def _score_sentiment(headlines: list[str]) -> tuple[str, int, int, str]:
    """Return (label, pos_count, neg_count, confidence)."""
    pos, neg = 0, 0
    for h in headlines:
        words = set(h.lower().split())
        pos += len(words & _POSITIVE)
        neg += len(words & _NEGATIVE)

    total_signals = pos + neg
    if total_signals == 0:
        return "neutral", 0, 0, "low"

    ratio = max(pos, neg) / total_signals
    confidence = "high" if ratio >= 0.7 else "moderate" if ratio >= 0.55 else "low"

    if pos > neg:
        return "positive", pos, neg, confidence
    if neg > pos:
        return "negative", pos, neg, confidence
    return "neutral", pos, neg, "low"


def _fetch_headlines(ticker: str) -> list[str]:
    if not NEWS_API_KEY:
        return []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": f'"{ticker}"', "language": "en", "sortBy": "publishedAt",
                    "pageSize": 20, "apiKey": NEWS_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            return []
        return [a["title"] for a in data.get("articles", []) if a.get("title")]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Derived signal helpers
# ---------------------------------------------------------------------------

def _trend_strength(price: float, ma50: float, ma200: float | None) -> str:
    """
    Classify trend strength based on how far price is from moving averages.
    - strong:   above both MAs and ma50 > ma200 (golden cross territory)
    - moderate: above ma50 but below ma200, or modest deviation
    - weak:     below ma50
    """
    above_50  = price > ma50
    above_200 = ma200 is not None and price > ma200
    ma50_above_200 = ma200 is not None and ma50 > ma200

    if above_50 and above_200 and ma50_above_200:
        return "strong"
    if above_50:
        return "moderate"
    return "weak"


def _risk_level(volatility: float) -> str:
    if volatility < 0.2:
        return "low"
    if volatility < 0.4:
        return "medium"
    return "high"


def _build_summary(
    ticker: str, trend: str, trend_strength: str,
    volatility: float, sentiment: str, return_30d: float | None,
) -> str:
    trend_phrase = {
        ("bullish", "strong"):   "shows a strong upward trend, trading above both its 50-day and 200-day moving averages",
        ("bullish", "moderate"): "shows moderate bullish momentum, trading above its 50-day moving average",
        ("bullish", "weak"):     "has a tentative bullish signal, though momentum remains limited",
        ("bearish", "weak"):     "is trading below its 50-day moving average, indicating near-term weakness",
        ("bearish", "moderate"): "shows moderate bearish pressure across key moving averages",
        ("bearish", "strong"):   "is in a sustained downtrend, trading below both key moving averages",
    }.get((trend, trend_strength), "shows mixed technical signals")

    vol_phrase = (
        "Volatility is elevated, suggesting higher short-term risk."
        if volatility > 0.35 else
        "Volatility is moderate." if volatility > 0.2 else
        "Volatility is low, indicating relatively stable price action."
    )

    sent_phrase = {
        "positive": "Recent news sentiment is positive.",
        "negative": "Recent news coverage is predominantly negative.",
        "neutral":  "News sentiment is neutral.",
    }.get(sentiment, "")

    ret_phrase = ""
    if return_30d is not None:
        if return_30d > 0.05:
            ret_phrase = f"The stock gained {return_30d * 100:.1f}% over the past month."
        elif return_30d < -0.05:
            ret_phrase = f"The stock declined {abs(return_30d) * 100:.1f}% over the past month."

    parts = [f"{ticker} {trend_phrase}.", vol_phrase, sent_phrase]
    if ret_phrase:
        parts.append(ret_phrase)
    return " ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def analyze_stock(ticker: str) -> dict:
    ticker = ticker.upper()

    # Fetch 1y to have enough data for 200d MA
    df = get_historical_data(ticker, period="1y")

    if df is None or df.empty:
        raise ValueError(f"No historical data available for {ticker}.")

    # Flatten MultiIndex columns (yfinance quirk with single ticker)
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"].dropna()
    if len(close) < 50:
        raise ValueError(f"Not enough data to analyze {ticker} (need ≥ 50 trading days).")

    current_price = float(close.iloc[-1])

    # Returns
    def _period_return(n: int) -> float | None:
        if len(close) < n + 1:
            return None
        return round(float(close.iloc[-1] / close.iloc[-n] - 1), 4)

    return_30d = _period_return(22)
    return_90d = _period_return(66)

    # Annualised volatility
    daily_returns = close.pct_change().dropna()
    volatility = round(float(daily_returns.std() * np.sqrt(252)), 4)

    # Moving averages
    ma50  = round(float(close.iloc[-50:].mean()), 2)
    ma200 = round(float(close.iloc[-200:].mean()), 2) if len(close) >= 200 else None

    trend          = "bullish" if current_price > ma50 else "bearish"
    t_strength     = _trend_strength(current_price, ma50, ma200)
    risk           = _risk_level(volatility)

    # Price series for chart (last 6 months ≈ 126 trading days)
    price_series = [
        {"date": str(d.date()), "close": round(float(v), 2)}
        for d, v in close.iloc[-126:].items()
    ]

    # Sentiment
    headlines = _fetch_headlines(ticker)
    sentiment, pos_signals, neg_signals, confidence = _score_sentiment(headlines)

    summary = _build_summary(ticker, trend, t_strength, volatility, sentiment, return_30d)

    return {
        "ticker":               ticker,
        "current_price":        round(current_price, 2),
        "return_30d":           return_30d,
        "return_90d":           return_90d,
        "volatility":           volatility,
        "ma50":                 ma50,
        "ma200":                ma200,
        "trend":                trend,
        "trend_strength":       t_strength,
        "risk_level":           risk,
        "sentiment":            sentiment,
        "sentiment_confidence": confidence,
        "positive_signals":     pos_signals,
        "negative_signals":     neg_signals,
        "headlines_analyzed":   len(headlines),
        "summary":              summary,
        "prices":               price_series,
    }
