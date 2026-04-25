# PROJECT_STATUS.md

**Erstellt:** 2026-04-25  
**Basis:** Vollständiger Code-Audit aller Python-Scripts, Frontend, Config und Outputs

---

## Übersicht

`automation/` ist ein persönliches Market-Dashboard mit vier aktiven Modulen: Daily Briefing, Portfolio Tracker, Hottest Stocks und Stock Analyzer. Das Backend läuft als FastAPI-Service, deployed auf Render.com (`https://market-tools.onrender.com`). Das Frontend ist eine Single-Page-App in Vanilla JS/HTML, die alle Daten über REST-API-Calls gegen dieses Backend bezieht. Das System befindet sich in Phase 2 (live data fetching via APIs), aber die Briefing-Generierung per Anthropic-API ist lokal noch nicht funktionsfähig (fehlender API-Key in `.env`).

---

## Module

### Daily Briefing Engine

- **Status:** ⚠️ teilweise
- **Was macht es:** Fetcht täglich Marktdaten (Gold/Silber via Twelve Data, Energie/Industrie-Commodities via yfinance, News via NewsAPI), baut einen strukturierten Prompt mit vorberechneten wirtschaftlichen Interpretationssignalen, und ruft die Anthropic API auf, um das Briefing zu generieren. Output wird in `outputs/latest-briefing.md` und `outputs/YYYY-MM-DD-briefing.md` gespeichert. Das Frontend rendert das Briefing als kolumniertes Zeitungsformat.
- **Dateien:** `scripts/fetch_data.py`, `scripts/generate_briefing.py`, `scripts/run_daily.py`, `scripts/utils.py`, `api.py` (Endpoints: `GET /daily-briefing`, `POST /generate-briefing`)
- **Abhängigkeiten:** Anthropic API (`claude-opus-4-6`), Twelve Data API (XAU/USD, XAG/USD, EUR/USD), NewsAPI (Headlines-Fetching + Filterlogik), yfinance (Brent, NatGas, Copper via Futures-Ticker)
- **Bekannte Probleme:**
  - **KRITISCH:** `ANTHROPIC_API_KEY` fehlt in `.env`. Der Button "↻ Generate New" im Frontend schlägt deshalb lokal immer mit HTTP 500 fehl. Ob der Key auf Render gesetzt ist, konnte nicht verifiziert werden.
  - Die letzte gespeicherte Briefing-Datei (`outputs/latest-briefing.md`) ist inhaltlich leer oder veraltet — das Frontend zeigt nach einem Kaltstart nichts an, bis ein neues Briefing generiert wird.
  - Das Briefing schreibt **nicht** in `~/projects/julio-brain/10_Daily/` — diese Integration ist in `ARCHITECTURE.md` als Ziel beschrieben, aber im Code noch nicht implementiert.
  - `scripts/run_daily.py` ist für einen Render-Cron-Job konzipiert, aber kein solcher Cron ist dokumentiert oder im Backlog als aktiv markiert.
  - `README.md` sagt "Current Phase: 1 — Manual Generation", aber `config/phase.txt` enthält `2`. README ist veraltet.

---

### Portfolio Tracker

- **Status:** ⚠️ teilweise
- **Was macht es:** Nimmt eine Liste von Holdings (Ticker + investierter USD-Betrag) entgegen, berechnet aktuelle Preise via yfinance, lädt 1-Jahr-Historik herunter, berechnet geometrisch annualisierte Renditen, annualisierte Volatilität, Korrelationsmatrix, Diversifikationsscore und einen textuellen Commentary. Das Frontend zeigt Flip-Cards für Positionen und ein vollständiges Analyse-Panel.
- **Dateien:** `scripts/portfolio.py`, `scripts/data_service.py`, `api.py` (Endpoint: `POST /portfolio/analyze`), Frontend-View `#view-portfolio` in `frontend/index.html`
- **Abhängigkeiten:** yfinance (historische Kurse + aktuelle Preise), numpy, pandas
- **Bekannte Probleme:**
  - **Keine Bewertungsmetriken:** P/E, P/B, EV/EBITDA, FCF-Yield, Dividend-Yield, Debt-to-Equity, ROE, Profit Margin sind alle Roadmap-Ziele für Woche 3, aber noch nicht implementiert. Das bestehende Analyse-Panel zeigt ausschließlich quantitative Risikokennzahlen (Return, Volatilität, Diversifikation).
  - **Kein CSV-Import:** Kein Trade-Republic-Export-Workflow vorhanden. Holdings werden manuell per Form-Input eingegeben.
  - Die Flip-Cards im Frontend sind hardcodiert auf eine statische Demo-Portfolio-Liste — sie spiegeln nicht dynamisch die im Analyse-Formular eingetragenen Holdings wider.
  - Debug-Prints in `portfolio.py` (Zeilen 94–96) landen im Render-Log, sollten durch `logging` ersetzt werden.

---

### Hottest Stocks

- **Status:** ✅ stabil
- **Was macht es:** Screent ein kuratiertes Universum von ~100 Large-Cap-Aktien (in `universe.py` gepflegt), berechnet für jede Aktie einen 5-Tage-Momentum-Score (`return * 0.7 + normalized_volume * 0.3`) und gibt die Top-N zurück. Das Frontend zeigt eine paginierte Tabelle mit Links zu Yahoo Finance.
- **Dateien:** `scripts/data_service.py` (`get_hot_stocks()`), `scripts/universe.py`, `api.py` (Endpoint: `GET /market/hot-stocks`), Frontend-View `#view-hotstocks`
- **Abhängigkeiten:** yfinance (Bulk-Download der 5d-Historik)
- **Bekannte Probleme:**
  - Die Scoring-Formel (70% Return, 30% Volume) ist willkürlich und nicht dokumentiert begründet. Die Roadmap fordert eine klare Definition der Gewichtung — das ist noch ausstehend.
  - Das Universum ist auf US Large-Caps fokussiert (S&P-500-nahe Auswahl). Keine europäischen, brasilianischen oder EM-Aktien.
  - Kein Caching: jeder Button-Click triggert einen frischen yfinance-Download für ~100 Tickers, was langsam sein kann.

---

### Stock Analyzer

- **Status:** ⚠️ teilweise
- **Was macht es:** Analysiert eine einzelne Aktie per Ticker: MA50/MA200, Trend-Stärke (Bullish/Bearish + Strong/Moderate/Weak), 30d/90d-Returns, annualisierte Volatilität, Risikostufe, Preis-Zeitreihe für Chart, und ein Keyword-basiertes News-Sentiment über NewsAPI.
- **Dateien:** `scripts/stock_analyzer.py`, `api.py` (Endpoint: `GET /stock/analyze?ticker=XXX`), Frontend-View `#view-analyzer`
- **Abhängigkeiten:** yfinance (1-Jahr-Historik), NewsAPI (Headlines für Sentiment), numpy
- **Bekannte Probleme:**
  - Das Sentiment-System ist rein keyword-basiert (Set-Intersection auf Wortebene) und liefert für viele Aktien `"neutral"` + `"low confidence"`, weil die Headlines einfach keine exakten Keyword-Matches haben. Kein semantisches Verständnis.
  - `NEWS_API_KEY` ist in `.env` gesetzt, aber der Free-Tier von NewsAPI limitiert auf 100 Requests/Tag — bei intensiver Nutzung des Analyzers wird das eng.
  - Der Chart im Frontend ist aktuell nur ein Placeholder (kein Chart-Library eingebunden) — der Code liefert `prices[]`-Array, aber die Visualisierung fehlt noch.
  - Kein Caching: jede Anfrage fetcht erneut 1 Jahr yfinance-Daten.

---

### Dashboard (Startseite)

- **Status:** ✅ stabil
- **Was macht es:** Zeigt Greeting, heutiges Datum, 3 Stat-Cards (S&P 500, Gold, EUR/USD), eine Vorschau des letzten Briefings, und ein Mini-Portfolio-Snapshot. Ticker-Banner scrollt live mit Kursen aus `/market/prices`.
- **Dateien:** Frontend-View `#view-dashboard` in `frontend/index.html`; Backend-Endpoints `GET /`, `GET /market/prices`
- **Abhängigkeiten:** Alle Backend-Endpoints müssen erreichbar sein
- **Bekannte Probleme:**
  - Zeigt "Loading briefing…" wenn kein Briefing vorhanden ist — kein graceful Empty State.
  - Portfolio-Snapshot hardcodiert auf Demo-Daten.

---

### Ideas Tracker

- **Status:** ❌ kaputt / nicht gebaut
- **Was macht es:** Placeholder — nur ein Nav-Item mit "Coming Soon"-Text. Keine Backend-Logik, keine Datenbankstruktur, kein Design.
- **Dateien:** Nur ein Sidebar-Eintrag in `frontend/index.html`
- **Abhängigkeiten:** keine
- **Bekannte Probleme:** Komplett unimplementiert.

---

## Tech-Stack-Übersicht

| Schicht | Technologie |
|---|---|
| Sprache | Python 3.11 (Backend), Vanilla JS / HTML / CSS (Frontend) |
| Backend-Framework | FastAPI + uvicorn |
| Daten-Bibliotheken | pandas, numpy, yfinance |
| HTTP | requests (Python), native fetch (JS) |
| AI-Modell | Anthropic `claude-opus-4-6` |
| Deployment | Render.com (API-Service + Static Site) |
| Paketmanagement | pip + venv |
| Tests | pytest |
| Format | Markdown (Briefing-Output), JSON (Rohdaten), PWA-Manifest |

**Externe APIs:**
- **Anthropic API** — Briefing-Generierung
- **Twelve Data** — XAU/USD, XAG/USD, EUR/USD (Free Tier: 800 API Credits/Tag)
- **NewsAPI** — wirtschaftliche Headlines und Stock-Sentiment (Free Tier: 100 Requests/Tag)
- **Yahoo Finance via yfinance** — alle Aktien-Historik, Futures-Preise, aktuelle Kurse (kein Key nötig, Rate Limits unklar)

---

## Konfiguration & Secrets

Aus `.env.example` und aktuellem `.env`-Stand (keine Werte):

| Variable | Zweck | Status |
|---|---|---|
| `TWELVE_DATA_API_KEY` | Precious metals + FX-Preise | ✅ gesetzt |
| `NEWS_API_KEY` | Headlines-Fetching + Stock-Sentiment | ✅ gesetzt |
| `ANTHROPIC_API_KEY` | Briefing-Generierung via Claude | ❌ **fehlt in .env** |
| `SMTP_HOST` | E-Mail-Delivery (Phase 3) | nicht gesetzt |
| `SMTP_PORT` | E-Mail-Delivery (Phase 3) | nicht gesetzt |
| `SMTP_USER` | E-Mail-Delivery (Phase 3) | nicht gesetzt |
| `SMTP_PASSWORD` | E-Mail-Delivery (Phase 3) | nicht gesetzt |
| `BRIEFING_RECIPIENTS` | E-Mail-Empfänger (Phase 3) | nicht gesetzt |

---

## Empfohlene nächste Schritte

1. **ANTHROPIC_API_KEY in `.env` eintragen** — ohne diesen Key funktioniert der "Generate New"-Button nicht. Dies ist der einzige Blocker für das Kernfeature. Parallel: Key auch auf Render.com als Environment Variable setzen, damit der deployed Service den Briefing-Endpoint nutzen kann.

2. **README.md aktualisieren** — das README beschreibt noch Phase 1 mit manuellem Workflow. Tatsächlich ist das System in Phase 2. Der beschriebene "paste into Claude session"-Workflow entspricht nicht mehr der Realität. README in 10 Minuten anpassen.

3. **julio-brain-Integration implementieren** — das Briefing schreibt aktuell nur in `outputs/`. Die in `ARCHITECTURE.md` beschriebene dritte Output-Route nach `~/projects/julio-brain/10_Daily/YYYY-MM-DD.md` ist nicht implementiert. Ein 5-Zeilen-Ergänzung in `run_daily.py` würde das liefern.

4. **Portfolio: Bewertungsmetriken hinzufügen** — der bestehende Portfolio-Tracker liefert Risikokennzahlen (Return, Volatilität), aber keine Fundamentaldaten. yfinance liefert P/E, Forward P/E, P/B, EV/EBITDA, Dividend Yield, ROE und Profit Margin über `yf.Ticker(ticker).info` — das ist eine Erweiterung, kein Umbau. Priorität für Woche 3.

5. **Frontend-Redesign auf Dark Mode** — das aktuelle UI ist funktional aber optisch light-mode-only. Das ist der Fokus von Woche 2 laut Roadmap. Vor dem Redesign empfiehlt sich eine saubere Komponenten-Inventur: Buttons, Cards und Table sind aktuell inline-styleed und nicht als wiederverwendbare Klassen abstrahiert.
