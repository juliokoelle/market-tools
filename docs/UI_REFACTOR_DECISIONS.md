# UI Refactor — Design Decisions
Branch: `refactor/ui-overhaul-2026-04`

---

## D1: Accent Color — Indigo #6366F1

**Chosen:** `#6366F1` (Tailwind Indigo 500)
**Rejected:** Existing `#5856d6` (slightly muddy in dark mode), Trade Republic Mint (too niche)

**Why:** `#6366F1` is slightly lighter and more vibrant than the existing purple. In dark mode against `#0D0D0F` backgrounds it reads as a clear call-to-action without being harsh. Hover state uses `#818CF8` (lighter) in dark mode, `#4F46E5` (darker) in light mode.

---

## D2: Dark Mode Background Scale

**Chosen:**
- `--bg-primary: #0D0D0F` — page background
- `--bg-secondary: #161618` — cards and surfaces
- `--bg-tertiary: #1F1F24` — nested elements (chart bg, input bg)
- `--border: #252530` — subtle dividers

**Why:** Trade Republic uses near-black with slight blue-grey undertone. This palette avoids pure `#000000` (too harsh) and the common "dark grey" (#333) that looks washed out.

---

## D3: CSS Variables — Backward Compatibility Aliases

**Decision:** New semantic variable names (`--bg-primary`, `--text-primary`, etc.) with aliases in both `:root` and `[data-theme="dark"]` that map old names (`--bg`, `--ink`, `--muted`, etc.) to new ones.

**Why:** Avoids mass find-replace across 2400+ lines of HTML. Old variable names in existing HTML/JS continue to work. New components use new names.

---

## D4: Portfolio — LocalStorage Replaces Backend Flip Cards

**Replaced:** `MY_PORTFOLIO` (loaded from `/portfolio/holdings`), flip card grid, `loadPortfolioHoldings()`, `savePortfolioHoldings()`
**With:** `_localPortfolio` (localStorage key `mt_portfolio_v1`), new position cards with P/L

**Why:** Spec explicitly says "Frontend-only. Kein Backend-Speichern heute." The existing backend portfolio is a different feature (server-side holding tracking). New localStorage system has a richer model: `{ ticker, quantity, avg_cost, added_date }` with live P/L calculation.

**Kept:** Portfolio Analyzer (risk/return form → `/portfolio/analyze`) — this is a separate analysis tool, not a holdings tracker.

---

## D5: Hot Stocks — Watchlist-Based Tabs as Primary

**Decision:** New tab-based Hot Stocks sourced from cached `_watchlistData` (from `/watchlist` endpoint).

**Tabs:**
- "Top Gainers" — sort by `return_30d` descending, positive only
- "Top Losers" — sort by `return_30d` ascending, negative only
- "Highest Bull" — sort by `bull_score` descending
- "Lowest Bull" — sort by `bull_score` ascending

**Legacy kept:** "Find Hot Stocks" button that calls `/market/hot-stocks` (backend endpoint). Shown as secondary action if user wants the backend version.

**Why:** Spec says "Backend-Endpoint für Hot Stocks gibt es nicht. Nutze /watchlist." But existing code uses `/market/hot-stocks`. Both are supported — watchlist tabs are the default UI, backend button is available below.

---

## D6: Sparklines — Lazy-Loaded SVG Polylines

**Decision:** SVG `<polyline>` rendered inline. No Plotly, no Chart.js for mini-charts.
**Load strategy:** Render card grid first with placeholder, then fetch chart data in batches of 4 with 100ms delay between batches to avoid overwhelming the backend.
**Data:** `/stock/{ticker}/chart?period=1mo` → last 30 close prices.
**Color:** Green if `close[-1] >= close[0]`, Red otherwise.
**Size:** 80×28px, no axes, no labels.

---

## D7: Plotly Dark Mode

**Decision:** `renderPlotlyChart()` reads current theme from `document.documentElement.dataset.theme` and adjusts `plot_bgcolor`, `paper_bgcolor`, grid colors, and axis text colors.

**Light:** `plot_bgcolor: '#f2f2f7'`, grid: `#e5e7eb`
**Dark:** `plot_bgcolor: '#1F1F24'`, grid: `#252530`

---

## D8: Theme Toggle Position

**Position:** Bottom of sidebar, above status pill.
**Icon:** Sun (light mode active) / Moon (dark mode active) — SVG icons.
**Persistence:** `localStorage.setItem('mt_theme', 'dark' | 'light')`
**Init:** Applied before first paint via `initTheme()` called at top of `<script>` block.

---

## D9: Sidebar Icons — Custom SVG

**Decision:** Replaced emoji/symbol characters with clean 20px SVG icons (stroke-based, 1.5px stroke-width).

Icons used:
- Dashboard: grid-2x2
- Daily Briefing: file-text
- Portfolio: pie-chart
- Hot Stocks: trending-up
- Stock Analyzer: bar-chart-2
- Ideas Tracker: lightbulb
- Theme: sun / moon

---

## D10: Hot Stocks — Watchlist Load Dependency

**Issue:** Hot Stocks tabs need `_watchlistData` which is loaded when visiting Stock Analyzer. If user visits Hot Stocks before Analyzer, data may be empty.

**Fix:** `loadHotTabData()` triggers `loadWatchlist()` if `_watchlistData` is empty. Hot Stocks shows "Loading watchlist data…" state while waiting.
