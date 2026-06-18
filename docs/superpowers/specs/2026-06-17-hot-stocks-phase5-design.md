# Phase 5 — Hot Stocks aufwerten (Ranking-Listen auf Lovable-Niveau)

**Status:** Approved (Design), 2026-06-17
**Roadmap:** `docs/superpowers/plans/2026-06-16-market-intelligence-redesign.md` → Phase 5.1
**Vorgänger:** Phase 4 (`2026-06-17-watchlist-phase4-design.md`) — wiederverwendbare Primitives/Score/Format
und das `/watchlist`-Datenmuster (`_score_one_ticker` + `_fetch_meta` + `_eur_rate`).

## Ziel

Die `/market/hot-stocks`-Seite von spartanischen Karten zu **Ranking-Listen** aufwerten — gespeist aus echten
Endpunkten, EUR durchgängig, fehlende Daten degradieren sauber zu „—" (kein Mock). Die vier Tabs
(Top Gainers / Top Losers / Highest / Lowest Bull) bleiben erhalten.

## Scope-Entscheidungen (geklärt im Brainstorming)

1. **Bull-Tabs reparieren via Backend.** Heute setzt das Backend **keinen** `bull_score`; der Frontend-Default
   `?? 50` macht alle Bull-Tabs bedeutungslos (alles = 50). Entscheidung: kleiner **additiver Backend-Change** —
   `bull_score` + `components` + `sector` + `market_cap` in die Hot-Stocks-Enrichment aufnehmen, server-gecacht,
   sodass „Highest/Lowest Bull" echt ranken und B/M/V-Badges real sind. (git push → Render autoDeploy; kein
   Dashboard-Eingriff.)
2. **Zeitfenster-Switch vorerst weglassen.** Backend hat keinen `period`-Param; `change_pct` ist Tagesveränderung,
   Sparkline 1M. Phase 5 shippt Ranking-Listen mit Day-Change + 1M-Sparkline (deckt sich mit echten Daten).
   Der 1D/5D/1M/YTD-Switch wird nachgerüstet, sobald das Backend einen `period`-Param hat (eigener Task).

## Kosten-Hinweis (bewusst akzeptiert)

`bull_score(ticker)` ruft für die Sentiment-Komponente **Haiku** auf. Scoring von N Hot-Stocks = N Haiku-Calls
(je 5-Min gecacht via `_TTL_BULL_SCORE`). Deshalb wird das Kandidaten-Set **auf Top 30** begrenzt
(`get_hot_stocks(top_n=30)`) → ≤30 Haiku/5-Min-Fenster, genug Breite für 4×5 Tabs.

## Backend (`scripts/api.py`, additiv)

`market_hot_stocks()` wird vom ad-hoc-`_enrich` auf das bewährte `/watchlist`-Muster umgestellt:

- `get_hot_stocks(top_n=30)` liefert Kandidaten mit `ticker`, `return`, `volume_avg`.
- Pro Ticker parallel (ThreadPool, wie `/watchlist`):
  - `_score_one_ticker(t)` (cached) → `bull_score`, `components{momentum,sentiment,valuation,analyst}`,
    `is_crypto`. Aus `components.momentum.details`: **`price`, `change_pct`, `spark`** (kein separater
    `_sparkline`-Call mehr).
  - `_fetch_meta(t)` (cached) → `name`, `currency`.
  - `_eur_rate(currency)` → **`price` in EUR** (round 2), exakt wie `/watchlist`.
- **Zwei billige, cloud-stabile Zusätze** (`fast_info`, kein `.info`-Throttle):
  - `market_cap` aus `fast_info.market_cap` → EUR via vorhandenem `_eur(...)` (wie `/stock/detail`).
  - `rel_volume` = `fast_info.last_volume / volume_avg` (Nenner aus `get_hot_stocks`); fehlt einer → `None`.
  - `sector` best-effort via `_ticker_sector(t)` (`.info`-throttle → `None` → Frontend „—").
- **Response je Stock:** `ticker, name, sector, price (EUR), change_pct, spark, bull_score, components,
  market_cap (EUR), rel_volume, currency`. Ergebnis server-cached (`_TTL_HOT_ENRICHED`), Sortierung wie
  heute (`change_pct` desc) — die feine Tab-Sortierung passiert im Frontend.
- Robustheit: pro-Ticker `try/except` degradiert zu Teil-Row (Felder `None`), nie 500 wegen Einzel-Ticker.
  Leeres `get_hot_stocks` → bestehender `503`.

**Kein neues Backend-Test-Harness** (Repo hat keins etabliert; Phase 4 ebenso). Validierung: `python -c`-Import/
Syntax-Check + Prod-Smoke nach Deploy.

## Frontend

### `frontend/src/services/api.ts`
- Neue Row-Schnittstelle (rich), z.B. `HotStockRow { ticker, name, sector, price, changePct, spark,
  bull, momentum, sentiment, valuation, marketCap, relVol }`. `StockRow` bleibt für andere Consumer unangetastet.
- `getHotStocks()` fetcht `/market/hot-stocks`, mappt rohe Stocks → `HotStockRow[]` (über `mapHotStock`),
  filtert `price != null`, und liefert die nach Tabs gerankte Struktur (`rankTabs`).

### `frontend/src/components/market/hot-stocks/hot-data.ts` (pure, testbar)
- `mapHotStock(raw): HotStockRow` — null-sichere Feld-Extraktion (`components.momentum.score` etc.),
  fehlende Werte → `null`.
- `rankTabs(rows): Record<Tab, HotStockRow[]>` — `gainers` = Top-5 nach `changePct`, `losers` = Bottom-5
  (reversed), `bull_high` = Top-5 nach `bull`, `bull_low` = Bottom-5 (reversed). Dedup nicht nötig (eine Quelle).

### `frontend/src/components/market/hot-stocks/HotStockList.tsx` (presentational)
Ranking-Liste; pro Zeile:

| Element | Quelle | Degradation |
|---------|--------|-------------|
| Rang `#` | Listenindex | — |
| Initialen-Avatar | aus Ticker (1–2 Zeichen), Tönung deterministisch | kein externer Logo-Dienst |
| Symbol + Sektor | `ticker` / `sector` | Sektor `null` → keine Subzeile |
| Sparkline | `spark` | leer → „—" |
| Preis (EUR) + Day | `price` (`fmtCurrency`) + `changePct` (`Delta`) | `···` bis geladen |
| Market Cap | `marketCap` (`fmtMarketCap(.,'EUR')`) | „—" wenn null |
| Rel Vol | `relVol` (`fmtNumber×`) | „—" wenn null |
| B / M / V Badges | `bull` / `momentum` / `valuation` (`ScoreBadge`, label „B"/„M"/„V") | Default-Anzeige |
| Why moving | `getStockAiSummary` **lazy on click**, im State gecacht | Button „Why ↗" bis geklickt |

- Klick auf Zeile/Symbol → Link `/market/analyzer/:symbol` (intern), nicht mehr Yahoo-extern.
- Lazy-Why-Pattern identisch zu `WatchlistPanel` (`why`/`whyLoading`-State, einmal pro Ticker laden).

### `frontend/src/pages/HotStocks.tsx`
- Behält die 4 Tabs, den 5-Min-Modul-Cache (`_cache`) und den Refresh-Button.
- Rendert `HotStockList` mit den Rows des aktiven Tabs. **Kein Zeitfenster-Switch.**
- Mobile: Liste in `.table-scroll`-Wrapper bzw. flexible Zeilen ohne fixes `gridTemplateColumns` auf Parents
  (CLAUDE.md-Regeln).

## Wiederverwendung
- `Sparkline`, `Delta` aus `components/market/primitives.tsx`
- `ScoreBadge` aus `components/market/score.tsx`
- `fmtCurrency`/`fmtMarketCap`/`fmtCompact`/`fmtNumber` aus `lib/format.ts` (EUR/de-DE)
- `getStockAiSummary` aus `services/api.ts` (lazy Why)
- Backend: `_score_one_ticker`, `_fetch_meta`, `_eur_rate`, `_eur`, `_ticker_sector` (alle vorhanden)

## Zustände & Edge-Cases
- **Laden:** bestehende Skeleton-/„Loading…"-Anzeige bis erster Paint.
- **Keine Daten:** „No data available." (wie heute) bzw. `EmptyState`.
- **Enrichment-Teil-null:** einzelne Felder „—"; Zeile rendert trotzdem mit Symbol/Preis.
- **Rel Vol / Sektor gedrosselt:** „—" (kein Mock).
- **Market-Cap-Währung:** Backend liefert EUR (`_eur`), daher `fmtMarketCap(.,'EUR')` korrekt gelabelt
  (kein EUR-Mislabel, vgl. Memory `yfinance_render_info_throttle`).

## Tests (vitest)
`frontend/src/components/market/hot-stocks/hot-data.test.ts`:
- `mapHotStock`: vollständige Row korrekt gemappt; fehlende `components`/`market_cap`/`rel_volume` → `null`.
- `rankTabs`: gainers/losers nach `changePct` (Top/Bottom-5), bull_high/low nach `bull`; korrekte Reihenfolge
  und Längen bei <5 Rows.

**Phase-7-Gate:** `npx vitest run && npx tsc -b` grün.

## Out of Scope
- Zeitfenster-Switch (1D/5D/1M/YTD) — bis Backend `period`-Param hat.
- Dashboard-Hot-Stocks-Radar (Phase 6).
- Restliches Portfolio/Analyzer.
- Komma-Bug im Portfolio-Editor (separat, nach Phase 5).

## Akzeptanz
Vier Tabs wie heute; Darstellung als Ranking-Listen auf Lovable-Niveau mit echten `/market/hot-stocks`-Daten:
Rang, Initialen-Avatar, Symbol+Sektor, Sparkline, Preis (EUR)+Day, Market Cap, Rel Vol, B/M/V-Badges, lazy „Why".
Bull-Tabs ranken jetzt korrekt (echter `bull_score`). Fehlende Werte „—"/`···`, keine gemockten Zahlen.
`vitest`+`tsc` grün; Prod-Smoke nach Deploy.
