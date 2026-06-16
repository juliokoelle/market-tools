# Market Intelligence Redesign — Lovable-Niveau auf echten Daten

> **For agentic workers:** Phasen-Plan (Roadmap-Altitude). Jede Phase wird vor Start in einen Task-by-Task-Plan (TDD, `superpowers:executing-plans`) heruntergebrochen. Checkboxen tracken Phasen-Fortschritt.

**Goal:** Das Market-Intelligence-Frontend auf das visuelle und inhaltliche Niveau des Lovable-Prototyps (`juliokoelle/market-intelligence-os`) heben — aber gespeist aus unserem echten FastAPI/yfinance-Backend statt Mock-Daten. Akute Bugs zuerst beheben (Daten laden nicht, P&L fehlt, Allocation = „Unknown").

**Leitprinzip:** Lovable = Design-Vorlage (reiches UI, Mock-Daten). Unser Repo = echte Datenpipeline (dünnes UI). Wir portieren Lovables Design-System + Layouts und verdrahten sie mit unseren Endpunkten. Fehlende Datenpunkte (Performance-Zeitreihe, Rel-Volume, Peers) ergänzen wir im Backend.

---

## Quellen-Mapping (Lovable → unser Stack)

| Lovable | Pfad (in `/tmp/mi-os`) | Unser Gegenstück |
|---------|------------------------|------------------|
| Design-Tokens (oklch, dark-first) | `src/styles.css` | `frontend/src/index.css` |
| Primitives (Panel, Delta, Sparkline, SectionHeader) | `src/components/market/primitives.tsx` | neu: `frontend/src/components/market/` |
| Score (ScoreBadge, ScoreGauge) | `src/components/market/score.tsx` | ersetzt `DonutSvg.tsx` |
| Dashboard | `routes/market.index.tsx` | `pages/Dashboard.tsx` + `Today.tsx` |
| Portfolio-Cockpit | `routes/market.portfolio.index.tsx` | `pages/Portfolio.tsx` (Monolith, 989 Z.) |
| Watchlist | `routes/market.portfolio.watchlist.tsx` | Watchlist-Teil in `Portfolio.tsx` |
| Stock Analyzer (Home + Detail) | `routes/market.analyzer*.tsx` | `pages/Analyzer.tsx` |
| Hot Stocks | `routes/market.hot-stocks.tsx` | `pages/HotStocks.tsx` |
| Format-Helfer | `src/lib/market/format.ts` | neu: `frontend/src/lib/format.ts` |

**Tech-Lücke:** Lovable nutzt `recharts` (echte Charts), `lucide-react` (Icons), shadcn/ui, Tailwind v4. Unser Frontend hat nur eine SVG-Donut-Komponente. → Phase 1 zieht `recharts` + `lucide-react` ein.

---

## Daten-Inventar: haben wir / müssen wir bauen

**Backend liefert bereits** (`scripts/api.py`):
- `/stock/{ticker}/detail` → name, price, change_pct, **bull_score + components{momentum, sentiment, valuation, analyst}**, sector, market_cap, pe_ratio, 52W-high/low
- `/stock/{ticker}/chart` → Kurshistorie (für Sparklines + Price-Chart)
- `/stock/{ticker}/ai-summary` → „why moving" / Analyst-Text
- `/market/hot-stocks`, `/market/prices`, `/market/names`, `/market/search-ticker`, `/market/history`
- `/watchlist`, `/stock-watchlist` (GET/POST/DELETE)
- `/portfolio/analyze` → annual_return, volatility, diversification_score, largest_position, per-asset weight/return/vol
- `/portfolio/allocation` → byHolding/bySector/byContinent/byMarket/byCountry
- `/portfolio` (GitHub-backed GET/POST) → Persistenz

**Müssen wir bauen / ergänzen:**
- **`shares` + `avg_buy` Persistenz** (Backend-Model + api.ts) → Voraussetzung für echte P&L. *(Phase 0)*
- **`/portfolio/performance`** → Portfolio-Wert-Zeitreihe + S&P-500-Benchmark (aus Holdings × Kurshistorie). *(Phase 2)*
- **`rel_volume`** in `/stock/{ticker}/detail` (yfinance: volume / avg_volume). *(Phase 3)*
- **Peers** (gleicher Sektor aus Watchlist-Universum) — clientseitig ableitbar. *(Phase 3)*
- **Financials** (Revenue/EBITDA) — yfinance `income_stmt`, optional; sonst ausblenden statt mocken. *(Phase 3)*

---

## Phasen-Übersicht

| Phase | Inhalt | Lovable nötig? | Behebt |
|-------|--------|----------------|--------|
| 0 | Datenfundament + P&L | nein | „Daten nicht aktualisiert", fehlende P&L, Allocation=Unknown |
| 1 | Design-System portieren | ja (Tokens/Primitives) | dünne Visuals |
| 2 | Portfolio-Cockpit | ja | Allocation/Performance/Risk-Visuals |
| 3 | Stock Analyzer (am meisten übernehmen) | ja | flache Analyzer-Ansicht |
| 4 | Watchlist erweitern | ja | fehlende Spalten |
| 5 | Hot Stocks aufwerten | ja | spartanische Karten |
| 6 | Dashboard (Overview aller Tabs) | ja | kein echtes Dashboard |
| 7 | Deploy + Verifikation | nein | — |

---

## Phase 0 — Datenfundament & P&L *(kein Lovable nötig, sofort lieferbar)*

**Behebt direkt deine Hauptbeschwerden.**

- [ ] **0.1 Lade-Bug:** In `Portfolio.tsx:442-457` gewinnt `localStorage` immer über den Server → Cross-Device-Updates kommen nie an. Fix: **Server-Daten gewinnen**, wenn `last_updated` neuer ist als der lokale Stand (Timestamp-Merge), sonst localStorage nur als Offline-Cache. Mindestlösung: bei vorhandenen Server-Positions diese laden und localStorage überschreiben.
- [ ] **0.2 `shares`/`avg_buy` durchverdrahten:**
  - `frontend/src/services/api.ts`: `savePortfolio` sendet `shares` + `avg_buy` mit; `getPortfolio` mappt sie zurück.
  - `scripts/api.py`: `PortfolioPosition` / `GHPortfolioWrite` um `shares: float | None`, `avg_buy: float | None` erweitern; GitHub-JSON-Schema mitziehen (`portfolio-current.json`).
- [ ] **0.3 P&L berechnen + anzeigen:** Marktwert = `shares × aktueller Kurs` (aus `/market/prices`), Einstand = `shares × avg_buy`, P&L = Marktwert − Einstand (€ + %). Pro Position **und** Gesamt. In bestehende Analysis-Sektion einsetzen (vollständiges Redesign folgt Phase 2).
- [ ] **0.4 Allocation live verifizieren:** Prüfen, warum Prod noch „Unknown/Other" zeigt (Throttle-Fix ist deployed). Vermutlich stale Frontend-State; nach 0.1 erneut testen. Ticker-Normalisierung (GOOG vs GOOGL, DTE.DE) gegenprüfen.

**Akzeptanz:** Nach Reload zeigt das Portfolio die gestern gespeicherten Werte (Total ~2.348 €), Stück/Ø-Kauf bleiben nach Save erhalten, P&L erscheint pro Position + gesamt, Allocation zeigt echte Sektoren/Kontinente.

---

## Phase 1 — Design-System portieren

**Entschieden (A):** Wir behalten **unser** Branding (eigene Farben, Light **und** Dark Mode, unsere interaktiven Systeme). Von Lovable übernehmen wir nur **Struktur + Features + Chart-/Primitive-Bauweise**, gestylt mit **unseren** CSS-Variablen. Lovables oklch-Dark-Theme wird NICHT 1:1 übernommen.

- [ ] **1.1 Dependencies:** `recharts`, `lucide-react` (ggf. `framer-motion`) in `frontend/package.json`.
- [ ] **1.2 Semantische Tokens (light+dark):** Falls noch nicht vorhanden, in `index.css` semantische Variablen ergänzen, die **unsere** bestehenden Farben mappen: `--gain`/`--loss`/`--warn`, `--brand` (= unser Rot), `--surface-1..3`, `--chart-1..5`, mono-Font mit tabular-nums. Beide Modi (hell/dunkel) müssen sauber aussehen.
- [ ] **1.3 Primitives** nach `frontend/src/components/market/` — Lovable-Bauweise, unsere Tokens: `Panel`, `SectionHeader`, `Delta`, `Sparkline`, `EmptyState`, `MetricCard`, `MiniStat`, `RiskBar`.
- [ ] **1.4 Score:** `ScoreBadge` + `ScoreGauge` (ersetzt/ergänzt `DonutSvg`).
- [ ] **1.5 Format:** `frontend/src/lib/format.ts` — `fmtCurrency`/`fmtPct`/`fmtPrice`/`fmtCompact`/`fmtMarketCap`/`scoreTone`. **EUR + deutsches Format** durchgängig.

**Akzeptanz:** Primitives gerendert in einer Test-Page, tsc grün, Theme konsistent.

---

## Phase 2 — Portfolio-Cockpit *(du magst den Aufbau — Cockpit-Erstansicht + Performance vs. S&P + Risk)*

Vorlage: `market.portfolio.index.tsx`.

- [ ] **2.1 Backend `/portfolio/performance`:** Portfolio-Wert-Zeitreihe (Holdings × historische Kurse) + S&P-500-Benchmark, Zeitfenster 1M/3M/6M/1Y/All.
- [ ] **2.2 Metric-Strip:** Total Value (groß, Akzent-Glow), Total P/L (€+%), Day P/L, Holdings/Sektoren, Diversification, Sharpe/Volatilität (aus `/portfolio/analyze`).
- [ ] **2.3 Performance-Chart:** Recharts `AreaChart`, Portfolio (brand) vs Benchmark (gestrichelt), Zeitfenster-Switch.
- [ ] **2.4 Allocation:** Recharts Donut (by sector/continent/market umschaltbar) + Legende mit % + Risk-Badges (Tech-Anteil, US-Anteil, FX-Risiko).
- [ ] **2.5 Risk-Card:** Concentration, Volatilität (60d), Beta vs SPX, Drawdown — als Balken (aus `/portfolio/analyze` + Ableitungen).
- [ ] **2.6 Holdings-Tabelle:** Symbol+Sektor, Trend-Sparkline, Stück, Ø-Kauf, Kurs, Marktwert, Day-Delta, Total-P/L (€+%), Gewicht-Bar. **Inline-Editor + TR-CSV-Import behalten.**
- [ ] **2.7 Refactor:** `Portfolio.tsx` (989 Z.) in Komponenten zerlegen (`PortfolioCockpit`, `HoldingsTable`, `AllocationPanel`, `PerformancePanel`, `RiskPanel`, `HoldingsEditor`).

**Akzeptanz:** Cockpit-Erstansicht mit echter P&L, Performance-Kurve vs S&P, Recharts-Allocation, Risk-Balken; Editieren/Import funktioniert weiter.

---

## Phase 3 — Stock Analyzer *(am meisten von Lovable übernehmen)*

Vorlage: `market.analyzer.tsx` + `market.analyzer.$symbol.tsx`.

- [ ] **3.1 Analyzer-Home:** Hero-Such-Panel (Glow, ⌘K-Optik) + „Trending"-Chips + Themen-/Sektor-Rails (unsere Watchlist-Kategorien) mit Sparkline + Preis + Bull-Score-Badge.
- [ ] **3.2 Analyzer-Detail (`/analyzer/:symbol`):**
  - Company-Header: Logo-Initialen, Preis groß, Day-Delta, Market Cap, Rel-Vol, 52W-Range, Beta; Action-Buttons (Watchlist/Add to Portfolio/Export).
  - Bull-Score-`ScoreGauge` + Decomposition-Tiles (unsere Komponenten momentum/sentiment/valuation/analyst → auf 4 Tiles mappen).
  - Price-Chart (`/stock/{ticker}/chart`), Zeitfenster-Switch.
  - Financials-Bars (yfinance `income_stmt`; falls leer: Panel ausblenden, **nicht mocken**).
  - Peer-Tabelle (gleicher Sektor aus Universum) mit Bull-Badges.
  - AI-Summary (`/stock/{ticker}/ai-summary`), Thesis/Risks/Catalysts.
- [ ] **3.3 Backend:** `rel_volume` zu `/stock/{ticker}/detail`; optional Financials-Endpoint.

**Akzeptanz:** Suche + Detail-Workspace im Lovable-Layout, alle Zahlen aus echten Endpunkten, keine gemockten Werte sichtbar (fehlende Daten → ausgeblendet/„n/a").

---

## Phase 4 — Watchlist erweitern *(unser Schema behalten + Lovable-Spalten)*

Vorlage: `market.portfolio.watchlist.tsx`.

- [ ] **4.1** Tabellen-Ansicht: Star, Symbol+Name, Trend-Sparkline, Price, Day, **Market Cap, Rel Vol, Bull, Momentum, Why moving**, „Analyze"-Link. Add/Remove über bestehende `/stock-watchlist`-Endpunkte.

**Akzeptanz:** Watchlist nutzt unser Add/Remove-Schema, zeigt aber die reichen Lovable-Spalten.

---

## Phase 5 — Hot Stocks aufwerten *(unsere Tabs behalten + Lovable-Darstellung)*

Vorlage: `market.hot-stocks.tsx`.

- [ ] **5.1** 4 Tabs behalten (Top Gainers / Top Losers / Highest / Lowest Bull). Karten → **Ranking-Listen** mit Rang, Logo, Symbol+Sektor, Why-Moving, Sparkline, Preis+Day, Market Cap + Rel-Vol, B/M/V-Score-Badges. Zeitfenster-Switch (1D/5D/1M/YTD).

**Akzeptanz:** Tab-Logik wie heute, Darstellung auf Lovable-Niveau mit echten `/market/hot-stocks`-Daten.

---

## Phase 6 — Dashboard *(Lovable-Dashboard als Overview aller Tabs)*

Vorlage: `market.index.tsx`. Du findest Lovables Dashboard „sehr gut" → 1:1 als zentrale Übersicht.

- [ ] **6.1** Header-Greeting + Tape-Status. Hero-Metric-Strip: Portfolio Value, Total P/L, S&P 500, VIX.
- [ ] **6.2** 2-Spalten-Grid: **links** Portfolio-Snapshot-Tabelle (Top-5) + Hot-Stocks-Radar (3 Spalten) + Next-Best-Actions; **rechts** Briefing-Preview (aus `/briefing`) + Watchlist-Movers + Calendar/Tasks (aus Personal-OS/Today-Daten).
- [ ] **6.3** `Today.tsx` bleibt **getrennt** (wird später eigenes Dashboard mit anderem Zweck/Hintergrund). Phase 6 baut nur das **Market-Dashboard** (`Dashboard.tsx`).

**Akzeptanz:** Market-Dashboard mit Kurzüberblick aller Market-Tabs, Links springen in die Detail-Tabs. Today unangetastet.

---

## Phase 7 — Deploy & Verifikation

- [ ] **7.1** `npx vitest run && npx tsc -b` grün.
- [ ] **7.2** `npm run deploy` (baut dist) + `git push` (Backend `scripts/api.py`). Render autoDeploy.
- [ ] **7.3** Prod-Smoke: Portfolio zeigt echte Werte + P&L; Analyzer/Watchlist/HotStocks/Dashboard laden; Mobile-Layout (CLAUDE.md-Regeln: kein fixes `gridTemplateColumns` auf Parents, `.table-scroll` für überlaufende Tabellen).

---

## Entscheidungen (getroffen 2026-06-16)

- **A — Theme:** ✅ Unser Branding bleibt (eigene Farben, Light **und** Dark Mode, unsere interaktiven Systeme). Von Lovable nur Struktur/Features/Chart-Bauweise, in unserem Look. Kein Dark-Navy/Blau.
- **B — Währung/Locale:** ✅ Durchgängig **EUR + deutsches Format**.
- **C — Today vs Dashboard:** ✅ **Getrennt lassen.** Today wird später ein eigenes Dashboard. Phase 6 = nur Market-Dashboard.
- **D — Reihenfolge:** ✅ Phase 0 zuerst, dann **1 → 2 → 3 → 4 → 5 → 6**.

## Verweise
- Lovable-Repo: `juliokoelle/market-intelligence-os` (lokal geklont: `/tmp/mi-os`), Lovable-Projekt `5fe9908b-41de-4432-8d2d-e3d76379ae96`
- Vorgänger-Plan: `docs/superpowers/plans/2026-06-16-portfolio-data-integrity.md`
- Deploy: `npm run deploy` baut nur dist; Backend braucht `git push` (Render autoDeploy on main)
- Stop-Conditions (CLAUDE.md): kein force-push, keine Render-Dashboard-Änderungen autonom, `VITE_API_URL` ist build-time.
