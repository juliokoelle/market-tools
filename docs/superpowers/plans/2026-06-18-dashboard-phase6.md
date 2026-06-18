# Phase 6 — Market-Dashboard (Implementierungs-Plan / Handoff)

**Spec:** `docs/superpowers/specs/2026-06-18-dashboard-phase6-design.md`
**Ziel-Datei:** `frontend/src/pages/Dashboard.tsx` (Route `/market`, ersetzt Basis-Version)
**Repo:** `/Users/juliokoelle/projects/automation`, Branch `main`
**Status:** Spec + Plan committet. **Implementierung in frischer Session bauen** (dieser
Kontext wurde zu teuer). GateGuard ist via `ECC_GATEGUARD=off` in `~/.claude/settings.json`
deaktiviert (greift ggf. erst nach Session-Neustart — passt für frische Session).

## Scope (entschieden 2026-06-18)
- **Bauen:** Hero-Strip · Portfolio-Snapshot Top-5 · Hot-Stocks-Radar · Watchlist-Movers · Briefing-Preview (vorhanden).
- **Weglassen:** Next-Best-Actions, Calendar/Tasks (keine Datenquelle, spätere Phase).
- **Nicht anfassen:** `Today.tsx`.

## Fertige Bausteine (alles vorhanden — NICHT neu erfinden)

### Portfolio Value + Total P/L + Top-5
- `getPortfolio()` (`services/api.ts:54`) → `{ positions: Position[], total_value, last_updated }`.
  `Position = { ticker, investment(EUR), shares?, avg_buy? }`.
- `getMarketPrices(tickers)` (`api.ts:25`) → `Record<ticker,{price,change,change_pct}>`.
- **`computePnl(positions, prices)`** (`components/market/portfolio-panels.tsx:46`) →
  `PnlStats { items[], totalCost, totalValue, totalPnl, totalPnlPct, dayPnl, dayPnlPct, anyPnl }`.
  Jedes `item` hat `value` (→ nach `value` desc sortieren, `slice(0,5)` für Snapshot).
  ⚠️ FX-Hinweis im Code: EUR-P&L für US-Titel noch Näherung — so übernehmen, nicht „fixen".
- **Flow:** `getPortfolio()` → tickers extrahieren → `getMarketPrices(tickers.join(','))` →
  `computePnl(positions, prices)`. Hero: `totalValue`, `totalPnl`/`totalPnlPct`.

### Hot-Stocks-Radar
- `getHotStocks()` (`api.ts:28`) → `Record<Tab,{...}>` mit `Tab = 'gainers'|'losers'|'bull_high'|'bull_low'`,
  je bis 5 `HotStockRow` (`hot-stocks/hot-data.ts`: `ticker,name,sector,price,changePct,spark,bull,momentum,valuation,marketCap,relVol`).
- Radar zeigt 3 Mini-Spalten: `gainers`, `losers`, `bull_high` (je 3–5 Zeilen). Link → `/market/hot-stocks`.

### Watchlist-Movers
- `getWatchlist()` (`api.ts:101`) → `WatchlistCategory[]` (`{category, stocks: StockDetail[]}`).
  `StockDetail` hat `ticker,name,price,change_pct,bull_score,...`.
- Alle `stocks` flatten → nach `Math.abs(change_pct)` desc → Top-5. Link → `/market/analyzer`.

### Markt + Briefing
- `getMarketPrices('^GSPC,^VIX')` für Hero. Briefing-Preview-Karte aus aktueller `Dashboard.tsx`
  (Z. 99–119) unverändert übernehmen.

### Format + Primitives (wiederverwenden, EUR/de)
- `fmtCurrency`, `MetricCard`, `MiniStat`, `Panel`, `SectionHeader` aus `portfolio-panels.tsx`
  (bzw. dortige Imports). Bestehende CSS-Utilities: `grid-5`, `grid-main-sidebar`, `card`,
  `card-sm`, `badge`/`badge-teal`, `stat-label`, `LoadingOverlay`. `ChangePill`-Muster aus aktueller Dashboard.tsx.

## Tasks
1. **`components/market/dashboard/dashboard-data.ts`** + `dashboard-data.test.ts` — pure Funktionen:
   - `topPositions(stats: PnlStats, n=5)` → nach `value` desc.
   - `topMovers(cats: WatchlistCategory[], n=5)` → flatten + `abs(change_pct)` desc.
   - (P/L kommt aus `computePnl` — nicht duplizieren.) Tests wie `hot-data.test.ts`/`watchlist-data.test.ts`.
2. **`HeroStrip.tsx`** — Greeting (Tageszeit) + Datum + Tape-Status; 4 Metric-Cards: Depotwert, Gesamt-G/V (farbcodiert), S&P 500, VIX. Nimmt fertige Werte als Props.
3. **`PortfolioSnapshot.tsx`** — Top-5 (Ticker, Wert EUR, Gewicht %), Link → Portfolio.
4. **`HotStocksRadar.tsx`** — 3 Mini-Spalten (gainers/losers/bull_high), Link → Hot-Stocks.
5. **`WatchlistMovers.tsx`** — Top-5 Mover, Link → Analyzer.
6. **`Dashboard.tsx` neu** — orchestriert: paralleles Laden (`Promise.allSettled`-Stil, je `.catch`),
   `grid-main-sidebar`-Layout (links Snapshot+Radar, rechts Briefing+Movers), graceful degradation
   pro Karte. Mobile: kein fixes `gridTemplateColumns` auf Parents; `.table-scroll` bei Overflow.

## Verifikation + Deploy
- `cd frontend && npx vitest run && npx tsc -b` grün.
- `npm run deploy` (staged jetzt Source+dist zusammen — siehe geänderten Deploy-Script).
- Prod-Smoke: `/market` zeigt echten Depotwert + G/V, Radar + Movers laden, Mobile ok, `Today` unverändert.

## Abschluss
- Obsidian-Doku: `julio-brain/30_Projects/market-tools/2026-06-18-dashboard-phase6.md`
  (Ziel · Vorgehen · Annahmen · Lessons · Ergebnisse+Links · offene Punkte · Status).
- Master-Plan `2026-06-16-market-intelligence-redesign.md`: Phase 6 abhaken.

## Offene Punkte / Annahmen
- Tape-Status simpel aus Markt-Daten-Frische ableiten (kein Börsen-Kalender-Endpoint).
- US-EUR-P&L bleibt Näherung (bestehendes Verhalten).
