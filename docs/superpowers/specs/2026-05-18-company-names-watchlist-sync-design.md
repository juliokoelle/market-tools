# Design: Company Names + Telegram Watchlist Sync

Date: 2026-05-18

## Task 1 — Company Names Everywhere

### Problem
Stock displays show only ticker symbols (AAPL, TSLA). All displays should show "Apple Inc. — AAPL".

### Findings
- `/market/hot-stocks` already enriches with yfinance → has `name` field
- `/watchlist` (Analyzer page) uses `_score_one_ticker()` which only returns scoring data — no name
- Frontend `getWatchlist()` hardcodes `name: t.ticker` instead of using API value
- `/stock/{ticker}/detail` already returns `name`
- Search (`searchTickers`) already returns names

### Design

**Backend (`scripts/api.py`):**
- Add `_fetch_name(ticker: str) -> str` — cached 30 min, uses `yf.Ticker(ticker).info` longName/shortName
- `get_watchlist()` runs a parallel name fetch after scoring, merges `name` into each ticker dict

**Frontend (`frontend/src/services/api.ts`):**
- `getWatchlist()`: `name: t.name ?? t.ticker` (was hardcoded to `t.ticker`)

**Display format:** `{Company Name} — {TICKER}` on one line, name leads

**Locations updated:**
- Analyzer page cards: `{s.name} — {s.ticker}`
- HotStocks table Name column: `{row.name} — {row.ticker}`
- Portfolio watchlist table: show company if stored

---

## Task 2 — Telegram → Watchlist Persistence

### Problem
Stocks added via Telegram disappear from the Market Tools watchlist after each Render deploy.

### Root Cause
`data/stock_watchlist.json` lives on Render's ephemeral filesystem. Free-tier Render wipes it on every deploy.

The POST endpoint itself **works** — confirmed with curl. The routing in capture_router.py is correct. Data loss is the only bug.

Secondary: `StockWatchlistEntry` model missing `company` field → capture_router sends it, Pydantic silently drops it.

### Design

**Backend (`scripts/api.py`):**
- Add `_gh_watchlist_read()` / `_gh_watchlist_write()` mirroring the existing portfolio GitHub persistence pattern, targeting `data/stock_watchlist.json` in the market-tools repo
- Update `_read_stock_watchlist()` to try GitHub first, fall back to local file
- Update `_write_stock_watchlist()` to write to GitHub (with local as fallback)
- Add `company: str = ""` to `StockWatchlistEntry` so the field is accepted and stored

**Scope:** Portfolio → Watchlist tab only. No change to YAML-based Analyzer watchlist.
