# Phase 6 — Market-Dashboard (Design)

**Datum:** 2026-06-18
**Route:** `/market` (`frontend/src/pages/Dashboard.tsx`, ersetzt bestehende Basis-Version)
**Branding:** eigene Farben, Light+Dark, EUR + deutsches Format (Entscheidungen A/B aus Redesign-Master-Plan)

## Ziel
Das Market-Dashboard wird zur zentralen Übersicht aller Market-Tabs: ein Hero-Metric-Strip
plus ein 2-Spalten-Grid mit Kurzüberblicken, die in die Detail-Tabs verlinken. Nur **echte**
Daten aus vorhandenen Endpoints — kein Fake-Content.

## Scope (entschieden 2026-06-18)
- **Enthalten:** Hero-Strip, Portfolio-Snapshot, Hot-Stocks-Radar, Watchlist-Movers, Briefing-Preview.
- **Weggelassen:** Next-Best-Actions und Calendar/Tasks — keine echte Datenquelle/Endpoint.
  Spätere Phase, sobald Backing-Daten existieren. (No-Fake-Data-Regel.)
- **Unangetastet:** `Today.tsx` (eigenes Dashboard mit anderem Zweck, Entscheidung C).

## Datenquellen (alle vorhanden)
| Modul | API |
|---|---|
| Portfolio Value + Total P/L | `getPortfolio()` → `analyzePortfolio(holdings)` → `total_value`; P/L = `total_value − Σ investment` |
| Portfolio-Snapshot Top-5 | dieselbe `PortfolioAnalysis.positions` (nach Wert sortiert, Top-5) |
| S&P 500 + VIX | `getMarketPrices('^GSPC,^VIX')` |
| Hot-Stocks-Radar | `getHotStocks()` |
| Watchlist-Movers | `getWatchlist()` |
| Briefing-Preview | `getBriefingPreview()` |

## Aufbau

### 1. Hero-Strip (Plan 6.1)
- Header-Greeting (Tageszeit-abhängig) + Datum + Tape-Status (Markt offen/zu via Markt-Daten-Frische).
- Metric-Strip, 4 Kennzahlen: **Portfolio Value (EUR)** · **Total P/L (EUR + %)** · **S&P 500** · **VIX**.
- P/L farbcodiert (grün/rot) wie bestehende `ChangePill`.

### 2. 2-Spalten-Grid (Plan 6.2) — `grid-main-sidebar`
**Links (Hauptspalte):**
- **Portfolio-Snapshot:** Top-5 Positionen nach Wert (Ticker, Wert EUR, Gewicht %), Link → `/market/portfolio`.
- **Hot-Stocks-Radar:** 3 Mini-Spalten (Top Gainers / Top Losers / Highest Bull), je 3–5 Zeilen aus `getHotStocks()`, Link → `/market/hot-stocks`.

**Rechts (Sidebar):**
- **Briefing-Preview:** bestehende Karte beibehalten.
- **Watchlist-Movers:** größte absolute Tagesbewegungen aus `getWatchlist()`, Top-5, Link → `/market/analyzer`.

## Komponenten-Schnitt
Dashboard.tsx orchestriert; pro Modul eine kleine presentational-Komponente in
`frontend/src/components/market/dashboard/`:
- `HeroStrip.tsx` (Metric-Cards, nimmt fertige Werte als Props)
- `PortfolioSnapshot.tsx`
- `HotStocksRadar.tsx`
- `WatchlistMovers.tsx`
- Briefing-Preview bleibt inline (bereits vorhanden, klein).

Reine Daten-Aufbereitung (P/L-Berechnung, Top-5-Sortierung, Mover-Ranking) als pure Funktionen in
`frontend/src/components/market/dashboard/dashboard-data.ts` + Unit-Tests
(`dashboard-data.test.ts`) — Muster wie `hot-data.ts`/`watchlist-data.ts` aus Phase 4/5.

## Fehlerbehandlung / Degradation
- Jeder Fetch unabhängig (`Promise.allSettled`-Stil, einzelnes `.catch`), wie bestehende Dashboard-Logik.
- Fehlt eine Quelle, zeigt nur deren Karte einen leeren/`—`-Zustand; Rest bleibt nutzbar (graceful degradation, Muster aus Phase 4).
- Loading: Skeleton/`LoadingOverlay` pro Block wie heute.

## Mobile (CLAUDE.md)
- Kein fixes `gridTemplateColumns` auf Parents; `grid-main-sidebar`/`grid-5` Utilities nutzen.
- Überlaufende Tabellen in `.table-scroll`.

## Akzeptanzkriterien
- `/market` zeigt Hero-Strip mit echtem Portfolio-Value + P/L, S&P, VIX.
- Linke Spalte: Top-5-Snapshot + Hot-Stocks-Radar; rechte Spalte: Briefing + Watchlist-Movers.
- Alle Karten verlinken korrekt in die Detail-Tabs.
- `Today.tsx` unverändert.
- `npx vitest run && npx tsc -b` grün; Mobile-Layout ohne Overflow-Bruch.

## Out of scope
- Next-Best-Actions, Calendar/Tasks (spätere Phase).
- Neue Backend-Endpoints.
