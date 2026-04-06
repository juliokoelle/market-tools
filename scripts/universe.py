"""
Stock universe — source of tickers for screening and discovery tools.

Current implementation: curated ~100 large-cap stocks across sectors.

Expansion paths (uncomment when ready):
  - CSV:  load_from_csv("config/universe.csv")
  - API:  load_from_wikipedia_sp500()
"""

# ---------------------------------------------------------------------------
# Curated universe — ~100 large-caps across major sectors
# ---------------------------------------------------------------------------

_UNIVERSE: list[str] = [
    # Technology
    "AAPL", "MSFT", "NVDA", "GOOG", "META", "AVGO", "AMD", "ORCL",
    "CRM", "ADBE", "INTC", "QCOM", "TXN", "IBM", "NOW", "SNOW",
    "PLTR", "MU", "AMAT", "LRCX",

    # Consumer Discretionary
    "AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "BKNG", "LOW",
    "TGT", "ABNB", "EBAY", "GM", "F", "UBER", "LYFT",

    # Communication Services
    "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "SNAP", "PINS",

    # Financials
    "BRK-B", "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP",
    "BLK", "SCHW", "V", "MA", "PYPL", "COF",

    # Healthcare
    "JNJ", "LLY", "UNH", "PFE", "ABBV", "MRK", "TMO", "ABT",
    "DHR", "AMGN", "GILD", "ISRG", "CVS", "HUM",

    # Industrials
    "CAT", "HON", "GE", "BA", "LMT", "RTX", "DE", "UPS",
    "FDX", "CSX", "NSC",

    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "PSX", "MPC",

    # Consumer Staples
    "PG", "KO", "PEP", "COST", "WMT", "PM", "MO", "CL",

    # Materials
    "LIN", "APD", "FCX", "NEM", "DOW",

    # Real Estate
    "AMT", "PLD", "EQIX", "SPG",

    # Utilities
    "NEE", "DUK", "SO", "D",
]


def get_stock_universe() -> list[str]:
    """
    Return the current stock universe as a list of ticker symbols.

    To extend: add tickers to _UNIVERSE above, or replace this function
    body with a CSV/API loader.
    """
    return list(_UNIVERSE)


# ---------------------------------------------------------------------------
# Future loaders (not active)
# ---------------------------------------------------------------------------

def _load_from_csv(path: str) -> list[str]:
    """Load universe from a CSV file with a 'ticker' column."""
    import csv
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [row["ticker"].strip().upper() for row in reader if row.get("ticker")]


def _load_from_wikipedia_sp500() -> list[str]:
    """Scrape the S&P 500 constituent list from Wikipedia."""
    import pandas as pd
    table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
    return table["Symbol"].str.replace(".", "-", regex=False).tolist()
