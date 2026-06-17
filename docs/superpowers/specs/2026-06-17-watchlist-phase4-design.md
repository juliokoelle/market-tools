# Phase 4 — Watchlist erweitern (reiche Tabellen-Ansicht)

**Status:** Approved (Design), 2026-06-17
**Roadmap:** `docs/superpowers/plans/2026-06-16-market-intelligence-redesign.md` → Phase 4.1
**Vorgänger:** Phase 3 (`2026-06-16-stock-analyzer-phase3-design.md`) — wiederverwendbare Primitives/Score/Format.

## Ziel

Die **persönliche Watchlist** (heute ein spartanischer Tab in `Portfolio.tsx`, gespeist aus `/stock-watchlist`)
zu einer reichen Tabellen-Ansicht auf Lovable-Niveau aufwerten — gespeist aus echten Endpunkten, EUR durchgängig,
fehlende Daten degradieren sauber zu „—" (kein Mock).

## Scope-Entscheidungen (geklärt im Brainstorming)

1. **Welche Watchlist:** Die persönliche `/stock-watchlist` („Meine Picks"), **nicht** die statische
   `config/watchlist.yaml`. Sie bleibt ein **Tab in `Portfolio.tsx`**; der Tab-Inhalt wird in eine eigene
   Komponente `WatchlistPanel` ausgelagert (kein Phase-2-Refactor des restlichen Portfolios).
2. **Datenstrategie:** Alle Spalten bauen, gedrosselte Felder (Rel Vol) zeigen `—`. **Kein Backend-Change** —
   Market Cap kommt zuverlässig aus `fast_info` über den bestehenden `/stock/detail`-Endpunkt.

## Architektur

- **Neu:** `frontend/src/components/market/portfolio/WatchlistPanel.tsx`
  - Kapselt: Add-Ticker-Input (umgezogen aus `Portfolio.tsx`), die reiche Tabelle, das Enrichment-Laden.
  - Props:
    - `tickers: string[]` — Membership (Source of Truth aus `/stock-watchlist`)
    - `portfolioTickers: Set<string>` — für „In Portfolio"-Badge
    - `onAdd: (ticker: string) => void`
    - `onRemove: (ticker: string) => void`
    - `onTransfer: (t: { ticker: string; price: number }) => void`
- **Neu:** `frontend/src/components/market/portfolio/watchlist-data.ts` — reine Helfer (testbar):
  - `buildEnrichmentMap(categories: WatchlistCategory[]): Map<string, EnrichedRow>` — flacht alle Kategorien,
    dedup-robust (ein Pick, der auch in einer statischen Kategorie liegt, wird gefunden).
  - `mergeRow(ticker, enrich?, detail?): WatchRow` — kombiniert schnelle + langsame Quelle, degradiert fehlende
    Felder zu `null` (→ UI rendert „—").
- **Geändert:** `frontend/src/pages/Portfolio.tsx`
  - Der Block `tab === 'watchlist'` (Z. ~713–822) wird durch `<WatchlistPanel … />` ersetzt.
  - Membership-State (`watchlist: string[]`) + `addToWatchlist`/`removeFromWatchlist` bleiben in `Portfolio.tsx`
    (Tab-Badge-Count nutzt `watchlist.length`) und werden als Props gereicht.
  - Entfällt aus `Portfolio.tsx`: `watchPrices`/`watchNames`-Laden via `/market/prices` + `/market/names`
    (durch EUR-Quellen ersetzt) und das alte Tabellen-Markup.

## Datenfluss (additiv, kein Backend-Change)

1. **Membership:** `getStockWatchlist()` (vorhanden) → Tickers. Add/Remove über bestehende POST/DELETE.
2. **Schnelle Anreicherung — 1 Call, serverseitig gecacht, durch Analyzer-Home/Dashboard meist warm:**
   `getWatchlist()` → `buildEnrichmentMap` → pro Ticker: `price` (EUR), `change_pct`, `spark`, `bull_score`,
   `components.momentum`, `name`. Deckt 6 Spalten beim ersten Paint.
3. **Hintergrund pro Ticker — concurrency-limitiert (max 4 parallel), `/stock/detail` 5-min server-cached:**
   `getStockDetail()` → `market_cap` (fast_info, cloud-stabil) + `rel_volume` (meist `null` → „—"). Progressiv
   in die Zeilen gemerged.
4. **„Why moving" — lazy, on-demand:** `getStockAiSummary()` erst bei Klick/Expand der „Why"-Zelle
   (spart LLM-Kosten für ungeöffnete Zeilen). Ergebnis pro Ticker im State gecacht.

## Spalten (11)

| # | Spalte | Quelle | Degradation |
|---|--------|--------|-------------|
| 1 | Star (Toggle) | Membership | — (immer gefüllt = auf Watchlist; Klick entfernt) |
| 2 | Symbol + Name | `getWatchlist` name / Ticker | Name fällt auf Ticker zurück |
| 3 | Trend-Sparkline | `getWatchlist` spark | leer → kein Chart |
| 4 | Price (EUR) | `getWatchlist` price | `···` bis geladen |
| 5 | Day | `getWatchlist` change_pct | `···` bis geladen |
| 6 | Market Cap | `getStockDetail` market_cap (fast_info) | „—" wenn null |
| 7 | Rel Vol | `getStockDetail` rel_volume (.info) | „—" (meist, bis VPS) |
| 8 | Bull | `getWatchlist` bull_score | Default 50 |
| 9 | Momentum | `getWatchlist` components.momentum | Default 50 |
| 10 | Why moving | `getStockAiSummary` (lazy) | Button „Why ↗" bis geklickt |
| 11 | Analyze | Link → `/market/analyzer/:symbol` | immer |

**Erhalten bleiben:** „→ Portfolio"-Transfer-Button + bestehender `TransferModal`, „In Portfolio"-Badge.

## Wiederverwendung

- `Sparkline`, `Delta`, `MiniStat` aus `components/market/primitives.tsx`
- `ScoreBadge` aus `components/market/score.tsx`
- Formatter aus `lib/format.ts` (`fmtCurrency`/`fmtPct`/`fmtCompact`/`fmtMarketCap`) — EUR/de-DE
- Detail-Mapping `getStockDetail` (api.ts) liefert bereits `market_cap`, `rel_volume`, `currency`

## Zustände & Edge-Cases

- **Membership lädt:** Loading-Hinweis (wie heute).
- **Watchlist leer:** bestehende Empty-Message („Your watchlist is empty…").
- **Enrichment pending:** `···`-Platzhalter pro Feld; Tabelle rendert sofort mit Symbol/Name.
- **Gedrosselte Felder:** „—".
- **Market-Cap-Währung:** `getStockDetail` liefert `market_cap` + `currency`. **Verifizieren** ob bereits
  EUR-konvertiert (Phase-3-FX). Falls native → über vorhandenes Detail-`currency`-Feld kennzeichnen oder
  als kompakte native Zahl zeigen; **nicht** falsch als EUR labeln (siehe Memory `yfinance_render_info_throttle`).
- **Mobile:** Tabelle in `.table-scroll`-Wrapper (CLAUDE.md: kein fixes `gridTemplateColumns` auf Parents).

## Tests (vitest)

`frontend/src/components/market/portfolio/watchlist-data.test.ts`:
- `buildEnrichmentMap`: flacht mehrere Kategorien, Ticker in zwei Kategorien → ein Eintrag (dedup).
- `mergeRow`: fehlendes Detail → `market_cap`/`rel_volume` = null; vorhandenes Detail überschreibt korrekt.
- Degrade-/Format-Pfad: null-Werte → erwarteter „—"/`···`-Marker (über kleine Format-Helfer, nicht über DOM).

**Phase-7-Gate:** `npx vitest run && npx tsc -b` grün.

## Out of Scope

- Phase-2-Refactor von `Portfolio.tsx` (Cockpit/Holdings) — nur der Watchlist-Tab wird angefasst.
- Backend-Änderungen (keine).
- Statische `config/watchlist.yaml`-Kategorien.

## Akzeptanz

Watchlist nutzt unverändert das Add/Remove-Schema (`/stock-watchlist`), zeigt aber die reichen Spalten:
Star, Symbol+Name, Sparkline, Price (EUR), Day, Market Cap, Rel Vol, Bull, Momentum, Why moving, Analyze-Link.
Fehlende Werte erscheinen als „—"/`···`, keine gemockten Zahlen. `vitest`+`tsc` grün; Prod-Smoke nach Deploy.
