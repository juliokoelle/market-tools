from typing import List, Dict, Tuple
import numpy as np
import pandas as pd

from scripts.data_service import get_close_prices, get_multiple_prices


def resolve_holdings(holdings: List[Dict]) -> Tuple[List[Dict], float]:
    """
    Convert investment amounts into weights using current market prices.

    Each input holding must have: ticker (str), investment (float, USD).

    Returns:
        enriched  — list of dicts with ticker, investment, weight, current_price, shares
        total_value — sum of all investments (USD)

    Tickers whose current price cannot be fetched are kept with price=None
    and will be filtered out in analyze_portfolio after historical data is checked.
    """
    tickers = [h["ticker"].upper() for h in holdings]
    investments = {h["ticker"].upper(): float(h["investment"]) for h in holdings}

    total_value = sum(investments.values())
    if total_value <= 0:
        raise ValueError("Total investment must be greater than 0.")

    current_prices = get_multiple_prices(tickers)

    enriched = []
    for ticker in tickers:
        investment = investments[ticker]
        price = current_prices.get(ticker)
        shares = round(investment / price, 6) if price else None
        enriched.append({
            "ticker":        ticker,
            "investment":    investment,
            "weight":        investment / total_value,
            "current_price": price,
            "shares":        shares,
        })

    return enriched, total_value


def download_prices(tickers: List[str], period: str = "1y") -> pd.DataFrame:
    data = get_close_prices(tickers, period=period)
    if data.empty:
        raise ValueError("No price data could be downloaded.")
    return data


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    returns = prices.pct_change().dropna()
    if returns.empty:
        raise ValueError("Not enough return data available.")
    return returns


def analyze_portfolio(holdings: List[Dict]) -> Dict:
    enriched, total_value = resolve_holdings(holdings)

    tickers      = [h["ticker"]    for h in enriched]
    weights_map  = {h["ticker"]: h["weight"]     for h in enriched}
    invest_map   = {h["ticker"]: h["investment"] for h in enriched}
    price_map    = {h["ticker"]: h["current_price"] for h in enriched}

    prices  = download_prices(tickers)
    returns = compute_returns(prices)

    # Keep only tickers present in historical data; re-normalise weights
    aligned_tickers = [t for t in tickers if t in returns.columns]
    if not aligned_tickers:
        raise ValueError("No valid tickers available after download.")

    weights = np.array([weights_map[t] for t in aligned_tickers])
    weights = weights / weights.sum()   # re-normalise after any dropped tickers

    returns = returns[aligned_tickers]

    n_days     = len(returns)
    cov_matrix = returns.cov()

    # Geometric (compound) annualised return per asset
    # Reflects actual compounded growth; arithmetic mean overstates return when volatility is high.
    cumulative_returns  = (1 + returns).prod()
    geometric_daily     = cumulative_returns ** (1 / n_days) - 1
    annualized_return   = float(np.dot(weights, (1 + geometric_daily) ** 252 - 1))

    portfolio_daily_volatility = float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))))
    annualized_volatility      = portfolio_daily_volatility * np.sqrt(252)

    # Debug
    print(f"[portfolio] period=1y  trading_days={n_days}")
    print(f"[portfolio] cumulative_returns:\n{cumulative_returns.round(4)}")
    print(f"[portfolio] annualized_return={annualized_return:.4f}  annualized_volatility={annualized_volatility:.4f}")

    correlation_matrix    = returns.corr().round(3).to_dict()
    diversification_score = 1 - float(np.sum(weights ** 2))

    largest_weight       = float(weights.max())
    largest_ticker       = aligned_tickers[int(np.argmax(weights))]
    largest_position_usd = round(invest_map[largest_ticker], 2)

    # Per-asset metrics
    asset_annual_returns = (1 + geometric_daily) ** 252 - 1
    asset_volatilities   = returns.std() * np.sqrt(252)

    assets = [
        {
            "ticker":        t,
            "weight":        round(float(w), 4),
            "annual_return": round(float(asset_annual_returns[t]), 4),
            "volatility":    round(float(asset_volatilities[t]), 4),
        }
        for t, w in zip(aligned_tickers, weights)
    ]

    positions = {
        t: {
            "investment":    round(invest_map[t], 2),
            "weight":        round(w, 4),
            "current_price": price_map.get(t),
            "shares":        round(invest_map[t] / price_map[t], 6) if price_map.get(t) else None,
        }
        for t, w in zip(aligned_tickers, weights)
    }

    commentary = build_commentary(
        annualized_return=annualized_return,
        annualized_volatility=annualized_volatility,
        largest_position=largest_weight,
        diversification_score=diversification_score,
    )

    return {
        "tickers":               aligned_tickers,
        "total_value":           round(total_value, 2),
        "positions":             positions,
        "assets":                assets,
        "weights":               {t: round(float(w), 4) for t, w in zip(aligned_tickers, weights)},
        "annualized_return":     round(annualized_return, 4),
        "annualized_volatility": round(annualized_volatility, 4),
        "largest_position":      round(largest_weight, 4),
        "largest_position_usd":  largest_position_usd,
        "number_of_positions":   len(aligned_tickers),
        "diversification_score": round(diversification_score, 4),
        "correlation_matrix":    correlation_matrix,
        "commentary":            commentary,
    }


def build_commentary(
    annualized_return: float,
    annualized_volatility: float,
    largest_position: float,
    diversification_score: float
) -> str:
    parts = []

    if annualized_volatility > 0.35:
        parts.append("The portfolio shows relatively high volatility, suggesting elevated risk.")
    elif annualized_volatility > 0.2:
        parts.append("The portfolio carries moderate risk based on historical volatility.")
    else:
        parts.append("The portfolio appears relatively stable based on historical volatility.")

    if largest_position > 0.4:
        parts.append("Position concentration is high, which increases idiosyncratic risk.")
    elif largest_position > 0.25:
        parts.append("The portfolio has some concentration risk in its largest holding.")
    else:
        parts.append("Position concentration looks reasonably balanced.")

    if diversification_score < 0.5:
        parts.append("Diversification is limited and could be improved across holdings.")
    else:
        parts.append("Diversification is reasonably healthy for the current number of positions.")

    if annualized_return > 0.15:
        parts.append("Historical return momentum has been strong, though this should not be interpreted as a forecast.")
    elif annualized_return < 0:
        parts.append("Historical performance has been negative over the observed period.")
    else:
        parts.append("Historical return performance has been positive but not extreme.")

    return " ".join(parts)