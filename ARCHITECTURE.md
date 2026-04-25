# Julio's Personal AI Ecosystem — Architecture

**Owner:** Julio Koelle  
**Last Updated:** 2026-04-25  
**Status:** Phase 2 → Phase 3 Refactor

---

## Vision

Aufbau eines persönlichen KI-Ökosystems, das aus zwei sauber getrennten, aber durch einen gemeinsamen Kontext-Layer verbundenen Systemen besteht:

1. **automation/** — Funktionales Dashboard mit Tools (Briefing, Portfolio, Stocks)
2. **julio-brain/** — Persönliche Wissensdatenbank & Decision-Support-Layer

Beide werden über Claude Code + MCP-Bridge orchestriert. Das System ist ausschließlich für persönlichen Gebrauch konzipiert; eine Erweiterung auf einen kleinen, vertrauten Personenkreis ist langfristig denkbar, aber kein Designziel.

---

## System-Komponenten

### 1. automation/ (Dashboard-System)

**Standort:** `~/projects/automation/`  
**Stack:** Python (Backend), HTML/CSS/JS (Frontend), Markdown (Output-Format)

**Module:**
- **Daily Briefing Engine** — generiert tägliche, personalisierte News-Zusammenfassungen aus kuratierten Quellen. Output: Markdown + HTML-Render. Trigger: Button im Frontend (manuell), via Claude Code.
- **Portfolio Tracker** — Verwaltung & Analyse persönlicher Investments inklusive Bewertungsmetriken (P/E, P/B, EV/EBITDA, FCF-Yield, ROE, Debt-to-Equity, etc.).
- **Hottest Stocks** — algorithmisch generierte Aktien-Empfehlungen basierend auf definierten Marktmetriken. Verlinkung zu Yahoo Finance.
- **Stock Analyzer** — Detail-Analyse einzelner Aktien per Ticker-Eingabe; Bullish/Bearish-Indikator.
- **(Geplant) Podcast Pipeline** — Tagesweise Transkription + Summary von ausgewählten Podcasts.

**Output-Pfade:**
- HTML-UI: `frontend/`
- Generierte Daten: `outputs/`
- Briefings (zusätzlich): `~/projects/julio-brain/10_Daily/`

### 2. julio-brain/ (Knowledge & Memory Layer)

**Standort:** `~/projects/julio-brain/`  
**Stack:** Obsidian Vault (Markdown), Git-versioniert

**Struktur:**
- `00_Inbox/` — schnelle, unsortierte Notizen
- `10_Daily/` — Daily Notes + Daily Briefings (vom automation-System)
- `20_Career/` — TUM-Bewerbung, MBB/IB-Prep, CV, Karriereoptionen
- `30_Projects/` — projektspezifische Notizen (inkl. spiegelnde Notizen zu automation-Modulen)
- `40_Knowledge/` — Frameworks, Konzepte, Lernmaterial, Podcast-Summaries
- `50_People/` — Networking & Kontakte
- `99_Archive/` — abgeschlossene/inaktive Inhalte

### 3. Brain Layer (Orchestrator)

**Tools:**
- **Claude Code** (Opus 4.7) — primäres Modell für Bauen, Refactoring, Architektur, lange Sessions
- **Codex** (GPT-5.5) — Sekundärmodell für Code-Reviews, alternative Lösungsvorschläge, Cross-Checks
- **MCP-Bridge `filesystem-brain`** — gibt Claude Code direkten Lese- und Schreibzugriff auf julio-brain Vault
- **MCP `context7`** — Live-Library-Documentation
- **Obsidian** — Frontend für julio-brain (lesen, schreiben, verlinken)

**Workflow-Regel:**
- Claude Code = Hauptarbeit
- Codex = Second-Opinion nach größeren Features
- Niemals beide gleichzeitig auf derselben Aufgabe

---

## Datenfluss

News-Quellen → Daily Briefing Engine (automation/) → 3 Outputs:
1. outputs/YYYY-MM-DD-briefing.md
2. frontend/ (HTML-Render im Dashboard)
3. julio-brain/10_Daily/YYYY-MM-DD.md (für Memory)

Markt-APIs (Yahoo Finance, etc.) → Portfolio Tracker / Hottest Stocks / Analyzer → frontend/

Julio's Reflexionen, Ideen, Recherche → julio-brain/ (via Obsidian) → Claude Code (via MCP) → Decision Support

---

## Kosten-Modell

**Aktueller Stand:** Daily Briefing nutzt Claude Code (über Pro-Subscription) statt direkter Anthropic-API. Daher: 0€ zusätzliche API-Kosten.

**Mögliche zukünftige Kostenpunkte:**
- Anthropic API (~2-5€/Monat) für vollautomatisierten Cron-Briefing
- Codex-Nutzung läuft über bestehendes ChatGPT-Pro-Abo
- Externe Daten-APIs (Bloomberg, FT) — bei Bedarf gesondert evaluieren

---

## Anti-Goals

Was dieses System explizit NICHT sein soll:
- ❌ Massenmarkt-Produkt oder SaaS
- ❌ Multi-User-Plattform mit Auth-System
- ❌ Mobile App (zumindest nicht in den ersten 3 Monaten)
- ❌ Vollautomatisierter Trading-Bot
- ❌ Generische "AI Assistant"-Lösung — alles muss explizit auf Julio zugeschnitten sein
