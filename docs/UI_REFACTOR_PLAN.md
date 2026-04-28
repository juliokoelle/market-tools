# UI Refactor Plan — 2026-04-28
Branch: `refactor/ui-overhaul-2026-04`

---

## 1. Current Frontend Structure

**File:** `frontend/index.html` — **2468 lines**, single-file app (HTML + CSS + JS inline)

### Sections (HTML)

| Section | Element ID | Notes |
|---|---|---|
| Sidebar nav | `<aside class="sidebar">` | Fixed left, 240px, collapses on mobile |
| Live ticker banner | `.ticker-banner` | Scrolling price marquee, top of main |
| Dashboard | `#view-dashboard` | Greeting, stat cards (S&P/Gold/EUR-USD), briefing status, market snapshot, portfolio mini |
| Daily Briefing | `#view-briefing` | Generate Premium/Quick buttons, status, cost counter, archive list |
| Portfolio | `#view-portfolio` | Flip cards, portfolio analyzer form |
| Hot Stocks | `#view-hotstocks` | Momentum screener, paginated results |
| Stock Analyzer | `#view-analyzer` | Watchlist grid by category (26 tickers) |
| Ideas Tracker | `#view-ideas` | Coming soon stub |
| Stock Detail Modal | `#stockDetailBackdrop` | Full-screen modal: score arc, chart (Plotly), components, AI summary |
| Portfolio Info Modal | `#modalBackdrop` | Metric explanation modal (Return/Volatility/Diversification) |
| Mobile nav | `.mobile-nav` | Bottom tab bar, shown on mobile only |

---

## 2. CSS Variables (Design System)

All defined in `:root`. Do NOT rename or remove — used throughout.

```css
--bg            #f2f2f7      /* page background */
--surface       #ffffff      /* card background */
--border        #e5e7eb      /* dividers */
--accent        #5856d6      /* primary purple */
--accent-lt     #eef2ff      /* accent tint */
--ink           #1c1c1e      /* primary text */
--muted         #8e8e93      /* secondary text */
--faint         #aeaeb2      /* tertiary / disabled */
--green-dk      #16a34a      /* positive / success */
--red-dk        #dc2626      /* negative / error */
--yellow        #ff9f0a      /* warning / neutral */
--shadow-sm     …            /* subtle card shadow */
--shadow        …            /* elevated card shadow */
--radius        14px         /* card radius */
--radius-sm     9px          /* inner element radius */
--sidebar-w     240px        /* sidebar width */
--topbar-h      44px         /* reserved, not visually used */
--sans          system-ui stack
--serif         Georgia stack (used in briefing body CSS, now dead code)
```

---

## 3. JavaScript Functions — Do Not Break

### Navigation & Init
| Function | What it does |
|---|---|
| `showView(name)` | Switches active view, triggers `loadWatchlist()` on analyzer |
| `initDate()` (IIFE) | Sets greeting + date on dashboard |
| `checkBackendStatus()` | Pings `/`, updates status pill |

### Market Data
| Function | What it does |
|---|---|
| `loadMarketData()` | Fetches prices for stat cards + ticker banner |
| `renderTicker(prices)` | Builds scrolling ticker HTML |
| `renderStatCards(prices)` | S&P / Gold / EUR-USD cards |
| `renderMarketSnapshot(prices)` | Market snapshot widget in dashboard |
| `renderPortfolioMini(prices)` | Portfolio mini-widget in dashboard |
| `fmtPrice(v)` | Price formatter |

### Daily Briefing (control panel only — no content rendered)
| Function | What it does |
|---|---|
| `loadBriefing()` | Checks `/briefing/list` → updates status badge |
| `generateBriefing(provider)` | POSTs to `/briefing/generate`, shows confirmation + cost |
| `loadBriefingArchive()` | Loads archive list (dates + costs + PDF buttons) |
| `loadCostSummary()` | Monthly cost counter |

### Portfolio Analyzer
| Function | What it does |
|---|---|
| `loadPortfolioHoldings()` | Loads saved holdings from backend |
| `savePortfolioHoldings(h)` | Persists holdings |
| `renderPortfolioSection()` | Renders flip cards |
| `renderFlipCards(prices)` | Portfolio flip card grid |
| `addHoldingRow(ticker, inv)` | Adds form row + autocomplete |
| `removeRow(btn)` | Removes holding row |
| `readHoldings()` | Reads form state |
| `analyze()` | POSTs to `/portfolio/analyze` |
| `renderBreakdown(assets)` | Renders asset breakdown table |
| `buildInsight(ret, vol, div)` | Generates text insight |
| `riskProfile(vol)` | Returns risk label |
| `openModal(key)` / `closeModal()` | Info modals for metrics |
| `handleBackdropClick(e)` / `handleEsc(e)` | Modal close handlers |

### Hot Stocks
| Function | What it does |
|---|---|
| `loadHotStocks()` | Fetches momentum screener |
| `hotChangePage(page)` | Pagination |
| `renderHotPage()` | Renders current page of hot stocks |

### Stock Analyzer / Watchlist
| Function | What it does |
|---|---|
| `loadWatchlist(forceRefresh)` | Fetches `/watchlist`, renders grid |
| `renderWatchlist(categories)` | Builds ticker card HTML |
| `scoreColor(s)` / `barColor(s)` | Score → CSS class |
| `openStockDetail(ticker)` | Opens modal, fetches detail + chart (token-guarded) |
| `closeStockDetail()` | Closes + purges Plotly |
| `renderStockDetail(d)` | Fills modal with score/components/metrics |
| `renderPlotlyChart(ohlcv, ticker)` | Renders Plotly OHLC chart |
| `switchChartPeriod(btn, period)` | Reloads chart for new period |
| `loadAiSummary()` | Fetches AI narrative for ticker |
| `analyzeStock()` | Legacy stub |
| `analyzeStockFromCard(ticker)` | Hot stocks → open detail modal |

### Utility
| Function | What it does |
|---|---|
| `mdToHtml(md)` | Markdown → HTML (used only for legacy briefing body CSS, now effectively unused) |
| `showError(msg)` / `clearError()` | Error banner in portfolio view |
| `setStatus(state)` | Updates status pill state |

---

## 4. What Currently Works

- [x] Dashboard: live prices, stat cards, briefing status, market mini, portfolio mini
- [x] Daily Briefing: generate buttons, status + cost display, archive with PDF buttons
- [x] Portfolio: flip cards, analyzer form with autocomplete, risk assessment
- [x] Hot Stocks: momentum screener, pagination
- [x] Stock Analyzer: watchlist grid, detail modal, Plotly chart, AI summary, period switching
- [x] Mobile nav: bottom tab bar
- [x] Backend status pill
- [x] Modal reopen fix (Plotly.purge + token guard — 2026-04-27)

---

## 5. What the Refactor Introduces

> **Fill this section** before starting implementation — specs from user input go here.

- [ ] (Spec TBD)

---

## 6. Test Checklist (pre-merge)

Run through these manually after each refactor step:

**Navigation**
- [ ] All 5 nav items switch views without error
- [ ] Mobile nav matches desktop nav behavior

**Dashboard**
- [ ] Stat cards load (S&P, Gold, EUR-USD)
- [ ] Ticker banner scrolls
- [ ] Briefing status shows correct state

**Daily Briefing**
- [ ] Generate Premium fires POST, shows confirmation + cost
- [ ] Generate Quick fires POST, shows confirmation + cost
- [ ] Archive loads dates + costs + PDF buttons
- [ ] "View PDF" opens new tab

**Stock Analyzer**
- [ ] Watchlist loads all 7 categories
- [ ] Clicking a card opens modal
- [ ] Closing modal and clicking a different card reopens modal (regression from 2026-04-27)
- [ ] Chart loads for default period (3mo)
- [ ] Period buttons switch chart
- [ ] AI Summary generates on click
- [ ] ESC / backdrop click closes modal

**Portfolio**
- [ ] Flip cards render
- [ ] Add/remove holding rows
- [ ] Autocomplete works
- [ ] Analyze sends request, renders metrics
- [ ] Info modals open/close

**Hot Stocks**
- [ ] Load fires, results paginate
- [ ] "Analyze in detail →" opens stock detail modal

---

## 7. Branch Strategy

```
main                          ← production (Render auto-deploys)
refactor/ui-overhaul-2026-04  ← this branch
```

Render will NOT auto-deploy this branch unless configured. Work safely here, merge to `main` when test checklist passes.
