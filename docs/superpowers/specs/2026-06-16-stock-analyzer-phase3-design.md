# Stock Analyzer (Phase 3) — Design

> Sub-Projekt von `docs/superpowers/plans/2026-06-16-market-intelligence-redesign.md` (Phase 3). Liefert den Lovable-Niveau Stock-Analyzer auf echten FastAPI/yfinance-Daten, **EUR durchgängig**.

**Goal:** Den flachen Analyzer (Suche + Watchlist-Karten + Detail-**Modal**) zu einem Lovable-Niveau-Workspace heben: Sektor-Rails auf der Home-Ansicht und eine eigene **Detail-Route** (`/market/analyzer/:symbol`) mit ScoreGauge, Decomposition, Price-Chart, Financials, Peers und AI-Summary — alle Zahlen aus echten Endpunkten, in EUR.

**Leitprinzip:** FX-Umrechnung wird **zentral im Backend** erledigt (Ansatz A), damit Portfolio, Analyzer, HotStocks und Watchlist konsistent dieselben EUR-Werte zeigen. Frontend bleibt dünn und konsumiert fertige EUR-Zahlen.

---

## Entscheidungen (getroffen 2026-06-16)

- **Währung:** ✅ **EUR durchgängig**, auch für globale Einzelaktien. Backend rechnet native Kurse serverseitig in EUR um.
- **FX-Ort:** ✅ **Ansatz A — Backend rechnet um, dünnes Frontend.** (Nicht B/Frontend, nicht C/Modal behalten.)
- **Detail-Umfang v1:** ✅ **Voll inkl. Financials.** Header + ScoreGauge + Decomposition + Price-Chart + AI-Summary (Freitext, wie heute) + Peers **+ Financials-Bars**. Strukturierte Thesis/Risks/Catalysts (JSON-AI-Endpoint) sind **nicht** in v1 (YAGNI; AI-Summary bleibt Freitext).
- **Detail = Route, nicht Modal:** ✅ `/market/analyzer/:symbol` als Workspace; `StockModal` wird entfernt.

---

## Ist-Stand (vor Phase 3)

**`frontend/src/pages/Analyzer.tsx` (340 Z.):**
- Home: `SearchBar` (lokaler Prefix-Match + remote `searchTickers`) + Watchlist-Kategorien als Karten-Grid (`BullRing` SVG + `$`-Preis + Change).
- Detail: `StockModal` (Overlay) mit Metrik-Grid, eigener `CandlestickChart`-SVG, `/ai-summary`-Text.
- Probleme: Inline-Styles, **`$`/USD** statt EUR, harte Hex-Farben statt Tokens, kein recharts, Detail nur als Modal.

**Backend `/stock/{ticker}/detail`** liefert heute: `bull_score` + `components{momentum,sentiment,valuation,analyst}`, `name`, `company_name`, `price`, `change_pct`, `pe_ratio`, `week_52_high`, `week_52_low`, `sector`, `market_cap` — alles in **nativer Währung**.
**Fehlt für Phase 3:** `native_currency`, `beta`, `rel_volume`, EUR-Umrechnung, Financials, Peers.

**Vorhandene Bausteine (aus Phase 1/2, wiederverwenden):**
- `components/market/score.tsx`: `ScoreBadge`, `ScoreGauge`
- `components/market/primitives.tsx`: `Panel`, `SectionHeader`, `Delta`, `Sparkline`, `MetricCard`, `MiniStat`, `RiskBar`, `EmptyState`
- `lib/format.ts`: `fmtCurrency`, `fmtCurrencyExact`, `fmtPrice`, `fmtNumber`, `fmtCompact`, `fmtMarketCap('USD'|'EUR')`, `fmtPct`, `scoreTone`, `relativeTime`
- Deps: `recharts ^3.8.1`, `lucide-react` vorhanden.
- Routing: `react-router-dom` `Routes/Route` in `App.tsx`; Analyzer unter `/market/analyzer`.

---

## Architektur

### 1. Routing & Seitenstruktur
- Neue Route `/market/analyzer/:symbol` → neue Seite `pages/AnalyzerDetail.tsx`.
- `Analyzer.tsx` (Home): Suche + Sektor-Rails; Karten **navigieren** via `useNavigate` zur Detail-Route (kein Modal mehr). `SearchBar.onSearch` springt direkt nach `/market/analyzer/<ticker>`.
- `StockModal` + lokaler `CandlestickChart` werden **entfernt** (Chart kommt als recharts-Panel in den Workspace).

### 2. Backend (`scripts/api.py`) — FX zentral

**FX-Helfer**
```
_eur_rate(currency: str) -> float   # Multiplikator native -> EUR
```
- `currency == "EUR"` → `1.0`.
- Sonst via yfinance-FX-Paar (z.B. `EUR{CUR}=X`) → Kehrwert als native→EUR-Faktor.
- Gecacht (`fx:{CUR}`, TTL ~1h) analog bestehender `_cache_get/_cache_set`.
- Fallback bei Fehler: `1.0` **und** ein Flag/Log, damit nicht stillschweigend falsch gerechnet wird (`fx_ok: false`).

**`/stock/{ticker}/detail`** — erweitern:
- Neu: `native_currency` (yfinance `fast_info.currency`/`info['currency']`), `beta` (`info['beta']`), `rel_volume` (`volume / averageVolume`, z.B. `info['averageDailyVolume10Day']`; `None` wenn nicht ableitbar).
- EUR-Umrechnung von `price`, `week_52_high`, `week_52_low`, `market_cap` über `_eur_rate(native_currency)`.
- `currency: "EUR"` ergänzen. `change_pct` bleibt unverändert (relativ).

**`/stock/{ticker}/chart`** — OHLC × `_eur_rate` (Volume unverändert), `currency:"EUR"`.
*Annahme v1: aktueller Spot-Kurs über die gesamte Serie. Per-Datum-FX (historische `EUR{CUR}=X`-Serie) ist ein dokumentiertes Follow-up; FX-Drift über 3–6 Monate ist gering.*

**Neu `/stock/{ticker}/financials`** — `income_stmt` (yfinance) → `{"currency":"EUR","rows":[{year,revenue,ebitda,net_income}]}`, Werte EUR-umgerechnet. **Leere `rows` wenn nicht verfügbar** (Frontend blendet Panel aus, mockt nicht).

**Neu `/stock/{ticker}/peers`** — Sektor-Kollegen aus dem Analyzer-Universum (Sektor des Tickers ermitteln, gleiche-Sektor-Ticker filtern), Batch-Scoring nutzen → `[{ticker,name,bull_score,price(EUR),change_pct}]`, max ~6, ohne den Ticker selbst.

### 3. Detail-Workspace `pages/AnalyzerDetail.tsx` (Panels)
Komponiert aus bestehenden Primitives + recharts; Geld immer EUR via `format.ts`.
- **CompanyHeader**: Initialen-Logo, großer EUR-Preis, `Delta` (Day), Market-Cap, Rel-Vol, 52W-Range-Bar (`RiskBar`/eigene Bar), Beta; Action-Buttons: Watchlist (best. `/stock-watchlist`), Add to Portfolio, Yahoo↗.
- **Score-Panel**: `ScoreGauge` + 4 Decomposition-Tiles (momentum/sentiment/valuation/analyst als `MetricCard`).
- **PriceChart**: recharts `AreaChart` aus `/chart`, Zeitfenster-Switch (1M/3M/6M/1Y), Brand-Farbe.
- **FinancialsBars**: recharts `BarChart` (Revenue/EBITDA/Net Income je Jahr); **Panel nur rendern wenn `rows.length > 0`**.
- **PeerTable**: `/peers` → Tabelle mit `ScoreBadge`, Preis (EUR), Delta; Zeilen verlinken zur jeweiligen Detail-Route.
- **AiSummaryPanel**: Freitext aus `/stock/{ticker}/ai-summary` (unverändert).
- Lade-/Fehlerzustände: `EmptyState` / Skeleton; einzelne Panels scheitern unabhängig (ein toter Endpoint kippt nicht die ganze Seite).

### 4. Home-Rails (`Analyzer.tsx`)
- Watchlist-Kategorien als Rails; Karten: `Sparkline` + `ScoreBadge` + EUR-Preis + `Delta`. Klick → `navigate('/market/analyzer/' + ticker)`.
- Mobile: kein fixes `gridTemplateColumns` auf Parents; überlaufende Tabellen via `.table-scroll` (CLAUDE.md-Regeln).

### 5. Frontend-Service (`services/api.ts`)
- `StockDetail`-Typ um `native_currency`, `currency`, `beta`, `rel_volume` erweitern.
- Neu: `getStockFinancials(ticker)`, `getStockPeers(ticker)` + Typen.
- `ChartPoint` unverändert (Werte jetzt EUR).

---

## Komponenten-Grenzen (Isolation)

| Unit | Zweck | Abhängigkeiten |
|------|-------|----------------|
| `_eur_rate` (BE) | native→EUR-Faktor, gecacht | yfinance FX-Paar, Cache |
| `/financials`, `/peers` (BE) | neue Datenpunkte | yfinance, Batch-Scoring |
| `AnalyzerDetail` (FE) | Workspace-Komposition + Routing/Loading | Panels, api.ts |
| `CompanyHeader`/`PriceChart`/`FinancialsBars`/`PeerTable`/`ScorePanel`/`AiSummaryPanel` | je 1 Aufgabe, eigene Props | primitives, score, format, recharts |
| `Analyzer` (Home) | Suche + Rails + Navigation | api.ts, primitives |

Jedes Panel ist isoliert testbar/verständlich; ein fehlender Endpoint blendet nur sein Panel aus.

---

## Tests & Verifikation

- **TDD (vitest)** für neue **reine** Funktionen: rel-volume-Label/Formatter, financials→Bar-Datenmapping, 52W-Range-Position, Peer-Sortierung. (Tests zuerst, dann Implementierung.)
- **Komponenten:** `npx tsc -b` grün + Render-Smoke (kein Crash, Panels mounten).
- **Backend:** Live-Smoke per `curl` gegen lokalen uvicorn + Prod: `/detail` (EUR + `beta`/`rel_volume`/`native_currency`), `/chart` (EUR), `/financials` (rows oder leer), `/peers` (Sektor-Liste). Kein vitest fürs Python-Backend.
- **Prod-Smoke (Phase-7-Regeln):** Analyzer-Home lädt Rails; Detail-Route zeigt EUR-Zahlen, Chart, Score, Peers; Financials-Panel nur bei Daten; Mobile-Layout ok.

## Slicing (für writing-plans)
1. **Backend:** FX-Helfer + `/detail`-Felder + `/chart`-EUR + `/financials` + `/peers` → push (Render autoDeploy) + Smoke.
2. **Detail-Route-Workspace:** `AnalyzerDetail.tsx` + Panels + api.ts + App.tsx-Route.
3. **Home-Rails + Modal-Entfernung** + Navigation.
4. **Deploy + Prod-Verifikation** (`npm run deploy`, tsc/vitest grün, Smoke).

## Nicht in Scope (YAGNI / Follow-up)
- Strukturierte Thesis/Risks/Catalysts (JSON-AI-Endpoint).
- Per-Datum-historische FX im Chart (v1 nutzt Spot).
- Optionaler eigenständiger Financials-Tab über v1 hinaus.

## Verweise
- Roadmap: `docs/superpowers/plans/2026-06-16-market-intelligence-redesign.md` (Phase 3)
- Deploy: `npm run deploy` baut nur `dist`; Backend braucht `git push` (Render autoDeploy on `main`)
- Stop-Conditions (CLAUDE.md): kein force-push, keine Render-Dashboard-Änderungen autonom, `VITE_API_URL` ist build-time.
