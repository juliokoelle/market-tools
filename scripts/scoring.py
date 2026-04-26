"""
Bull score algorithm for Stock Analyzer 2.0.

Score: 0–100 composite across four components:
  Price Momentum  30 %  — recent returns + MA position
  Sentiment       30 %  — Haiku LLM classification of news headlines
  Valuation       20 %  — P/E, forward P/E, P/B (omitted for crypto/ETFs)
  Analyst         20 %  — consensus recommendation from yfinance (omitted for crypto/ETFs)

Crypto (tickers ending in -USD) and no-valuation tickers (ETFs, commodities):
  Momentum 50 %, Sentiment 50 %, Valuation and Analyst omitted.

Public API:
    bull_score(ticker) → dict
"""

from __future__ import annotations

import os

import yfinance as yf

_CRYPTO_SUFFIXES = ("-USD",)

# ETFs and commodity trackers: P/E and analyst consensus don't apply.
# Scored like crypto: Momentum 50 % + Sentiment 50 %.
_NO_VALUATION_TICKERS = {"GLD", "SLV", "VWCE.DE"}


def _is_crypto(ticker: str) -> bool:
    return any(ticker.upper().endswith(s) for s in _CRYPTO_SUFFIXES)


def _is_no_valuation(ticker: str) -> bool:
    """True for crypto and ETFs/commodities where P/E and analyst data don't apply."""
    return _is_crypto(ticker) or ticker.upper() in _NO_VALUATION_TICKERS


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# 1. Price Momentum
# ---------------------------------------------------------------------------

def _return_to_score(ret: float | None, scale: float = 0.20) -> float:
    """Map a return to 0–100. scale=0.20 → ±20% spans the full range."""
    if ret is None:
        return 50.0
    return _clamp(50.0 + (ret / scale) * 50.0)


def _momentum_score(ticker: str) -> tuple[float, dict]:
    try:
        df = yf.download(ticker, period="1y", auto_adjust=True, progress=False)
        if df is None or df.empty:
            return 50.0, {"error": "no data"}

        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)

        close = df["Close"].dropna()
        if len(close) < 2:
            return 50.0, {"error": "insufficient data"}

        price = float(close.iloc[-1])

        ret_30d = float(close.iloc[-1] / close.iloc[-22] - 1) if len(close) >= 23 else None
        ret_90d = float(close.iloc[-1] / close.iloc[-66] - 1) if len(close) >= 67 else None

        ma50  = float(close.iloc[-50:].mean())  if len(close) >= 50  else None
        ma200 = float(close.iloc[-200:].mean()) if len(close) >= 200 else None

        above_50  = ma50  is not None and price > ma50
        above_200 = ma200 is not None and price > ma200

        if above_50 and above_200:
            ma_score = 85.0
        elif above_50:
            ma_score = 60.0
        elif ma50 is not None:
            ma_score = 25.0
        else:
            ma_score = 50.0

        s30 = _return_to_score(ret_30d, scale=0.15)
        s90 = _return_to_score(ret_90d, scale=0.25)
        score = s30 * 0.40 + s90 * 0.30 + ma_score * 0.30

        return round(score, 1), {
            "return_30d":  round(ret_30d * 100, 1) if ret_30d is not None else None,
            "return_90d":  round(ret_90d * 100, 1) if ret_90d is not None else None,
            "above_ma50":  above_50,
            "above_ma200": above_200,
            "price":       round(price, 2),
        }
    except Exception as exc:
        return 50.0, {"error": str(exc)}


# ---------------------------------------------------------------------------
# 2. Sentiment — Haiku LLM, keyword fallback
# ---------------------------------------------------------------------------

_POSITIVE_KW = {
    "surge", "soar", "gain", "rise", "rally", "profit", "beat", "record",
    "strong", "growth", "bullish", "upgrade", "buy", "outperform", "boom",
    "expand", "breakthrough", "milestone", "revenue", "dividend", "launch",
}
_NEGATIVE_KW = {
    "fall", "drop", "plunge", "loss", "miss", "weak", "decline", "bearish",
    "downgrade", "sell", "crash", "lawsuit", "investigation", "fine", "fraud",
    "layoff", "cut", "warning", "risk", "concern", "debt", "default", "recall",
}

_SENTIMENT_SCORE_MAP = {"bullish": 80.0, "neutral": 50.0, "bearish": 20.0}


def _fetch_headlines(ticker: str) -> list[str]:
    try:
        news = yf.Ticker(ticker).news or []
        titles = []
        for item in news[:20]:
            if not item:
                continue
            title = (
                item.get("content", {}).get("title")
                or item.get("title")
                or ""
            )
            if title:
                titles.append(title)
        return titles
    except Exception:
        return []


def _keyword_sentiment(headlines: list[str]) -> tuple[str, float]:
    pos, neg = 0, 0
    for h in headlines:
        words = set(h.lower().split())
        pos += len(words & _POSITIVE_KW)
        neg += len(words & _NEGATIVE_KW)
    if pos > neg:
        return "bullish", _SENTIMENT_SCORE_MAP["bullish"]
    if neg > pos:
        return "bearish", _SENTIMENT_SCORE_MAP["bearish"]
    return "neutral", _SENTIMENT_SCORE_MAP["neutral"]


def _haiku_classify(ticker: str, headlines: list[str]) -> str:
    """Call Haiku to classify sentiment. Falls back to keyword on any error."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        label, _ = _keyword_sentiment(headlines)
        return label

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        sample = "\n".join(f"- {h}" for h in headlines[:15] if h)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            system=(
                "You are a financial sentiment classifier. "
                "Respond with exactly one word: bullish, neutral, or bearish."
            ),
            messages=[{
                "role": "user",
                "content": f"Ticker: {ticker}\nHeadlines:\n{sample}",
            }],
        )
        label = resp.content[0].text.strip().lower().split()[0]
        if label not in ("bullish", "neutral", "bearish"):
            label = "neutral"
        return label
    except Exception:
        label, _ = _keyword_sentiment(headlines)
        return label


def _sentiment_score(ticker: str) -> tuple[float, dict]:
    headlines = _fetch_headlines(ticker)
    if not headlines:
        return 50.0, {"label": "neutral", "headlines_count": 0, "source": "no data"}

    label = _haiku_classify(ticker, headlines)
    score = _SENTIMENT_SCORE_MAP[label]
    source = "haiku" if os.getenv("ANTHROPIC_API_KEY") else "keywords"

    return round(score, 1), {
        "label":           label,
        "headlines_count": len(headlines),
        "source":          source,
    }


# ---------------------------------------------------------------------------
# 3. Valuation (stocks only)
# ---------------------------------------------------------------------------

def _pe_to_score(pe: float) -> float:
    if pe < 10:  return 90.0
    if pe < 15:  return 80.0
    if pe < 20:  return 70.0
    if pe < 25:  return 60.0
    if pe < 35:  return 50.0
    if pe < 50:  return 35.0
    return 20.0


def _pb_to_score(pb: float) -> float:
    if pb < 1:  return 85.0
    if pb < 2:  return 70.0
    if pb < 4:  return 55.0
    if pb < 8:  return 35.0
    return 20.0


def _valuation_score(ticker: str) -> tuple[float, dict]:
    try:
        info = yf.Ticker(ticker).info

        def _pos_float(key: str) -> float | None:
            v = info.get(key)
            return float(v) if v is not None and float(v) > 0 else None

        trailing_pe = _pos_float("trailingPE")
        forward_pe  = _pos_float("forwardPE")
        pb          = _pos_float("priceToBook")

        sub_scores:  list[float] = []
        sub_weights: list[float] = []

        if trailing_pe is not None:
            sub_scores.append(_pe_to_score(trailing_pe));  sub_weights.append(0.40)
        if forward_pe is not None:
            sub_scores.append(_pe_to_score(forward_pe));   sub_weights.append(0.40)
        if pb is not None:
            sub_scores.append(_pb_to_score(pb));           sub_weights.append(0.20)

        if not sub_scores:
            score = 50.0
        else:
            total_w = sum(sub_weights)
            score = sum(s * w for s, w in zip(sub_scores, sub_weights)) / total_w

        return round(score, 1), {
            "trailing_pe":   round(trailing_pe, 1) if trailing_pe is not None else None,
            "forward_pe":    round(forward_pe, 1)  if forward_pe  is not None else None,
            "price_to_book": round(pb, 2)          if pb          is not None else None,
        }
    except Exception as exc:
        return 50.0, {"error": str(exc)}


# ---------------------------------------------------------------------------
# 4. Analyst consensus (stocks only)
# ---------------------------------------------------------------------------

def _analyst_score(ticker: str) -> tuple[float, dict]:
    try:
        info = yf.Ticker(ticker).info
        mean  = info.get("recommendationMean")
        key   = (info.get("recommendationKey") or "").lower()
        count = info.get("numberOfAnalystOpinions", 0)

        if mean is not None:
            # 1.0 = Strong Buy → 100, 5.0 = Sell → 0
            score = _clamp((5.0 - float(mean)) / 4.0 * 100.0)
        else:
            score = float({
                "strong_buy": 92, "buy": 75, "hold": 50,
                "underperform": 30, "sell": 12,
            }.get(key, 50))

        return round(score, 1), {
            "recommendation":      key or None,
            "recommendation_mean": round(float(mean), 2) if mean is not None else None,
            "analyst_count":       count,
        }
    except Exception as exc:
        return 50.0, {"error": str(exc)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def bull_score(ticker: str) -> dict:
    """
    Returns:
        {
            "ticker":        str,
            "bull_score":    int (0-100),
            "is_crypto":     bool,
            "no_valuation":  bool,  # True for crypto + ETFs/commodities (GLD, SLV, VWCE.DE…)
            "components": {
                "momentum":  {"score": float, "weight": float, "details": dict},
                "sentiment": {"score": float, "weight": float, "details": dict},
                # valuation + analyst only present when no_valuation=False
                "valuation": {"score": float, "weight": float, "details": dict},
                "analyst":   {"score": float, "weight": float, "details": dict},
            }
        }
    """
    ticker  = ticker.upper()
    crypto  = _is_crypto(ticker)
    no_val  = _is_no_valuation(ticker)

    m_score, m_details = _momentum_score(ticker)
    s_score, s_details = _sentiment_score(ticker)

    if no_val:
        composite = m_score * 0.50 + s_score * 0.50
        components = {
            "momentum":  {"score": m_score, "weight": 0.50, "details": m_details},
            "sentiment": {"score": s_score, "weight": 0.50, "details": s_details},
        }
    else:
        v_score, v_details = _valuation_score(ticker)
        a_score, a_details = _analyst_score(ticker)
        composite = (
            m_score * 0.30
            + s_score * 0.30
            + v_score * 0.20
            + a_score * 0.20
        )
        components = {
            "momentum":  {"score": m_score, "weight": 0.30, "details": m_details},
            "sentiment": {"score": s_score, "weight": 0.30, "details": s_details},
            "valuation": {"score": v_score, "weight": 0.20, "details": v_details},
            "analyst":   {"score": a_score, "weight": 0.20, "details": a_details},
        }

    return {
        "ticker":       ticker,
        "bull_score":   round(composite),
        "is_crypto":    crypto,
        "no_valuation": no_val,
        "components":   components,
    }
