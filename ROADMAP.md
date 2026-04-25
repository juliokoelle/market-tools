# Roadmap — Personal AI Ecosystem

**Time Budget:** ~20h/Woche (2h/Werktag + 8h Sa + 3-4h So)  
**MVP-Horizont:** 4 Wochen  
**Start:** 2026-04-25

---

## Woche 1 (25.04. — 02.05.) — Stabilisierung

**Ziel:** Was läuft, läuft sauber. Was kaputt ist, ist gefixt. Wir wissen genau, wo wir stehen.

- [ ] **Audit** des automation-Projekts durch Claude Code
  - Output: `PROJECT_STATUS.md`
  - Inventar aller Module, Funktionen, Abhängigkeiten
  - Kennzeichnung: ✅ stabil | ⚠️ teilweise | ❌ kaputt
- [ ] **Daily Briefing umbauen** — von API-basiert auf Claude-Code-Trigger
  - Frontend: Button "Briefing generieren"
  - Backend: schreibt Markdown → Frontend rendert + parallel in julio-brain/10_Daily/
- [ ] **News-Quellen-Liste erstellen** — 3-5 verbindliche Quellen
- [ ] **Codex-Cross-Check** der wichtigsten Briefing-Logik

## Woche 2 (03.05. — 09.05.) — Frontend-Redesign

**Ziel:** Dashboard sieht aus wie ein professionelles Tool.

- [ ] **Frontend-Design Skill** aktivieren für gesamtes UI-Refactoring
- [ ] **Dark Mode** als Standard
- [ ] **Wiederverwendbare Komponenten:** Buttons, Cards, Tab-Navigation
- [ ] **Briefing-Tab** final designen
- [ ] **Portfolio-Tab** Look & Feel überarbeiten

## Woche 3 (10.05. — 16.05.) — Portfolio Deep Dive

**Ziel:** Tracker wird substantiell besser, Julio versteht Unternehmensbewertung tiefer. (Wahrscheinlich längster Sprint, da inhaltliche Lernkurve.)

- [ ] **Bewertungs-Metriken implementieren:** P/E, P/B, EV/EBITDA, FCF-Yield, Dividend-Yield, Debt-to-Equity, ROE, Profit Margin
- [ ] **CSV-Import-Workflow** für Trade-Republic-Exports (offizielle TR-API existiert nicht)
- [ ] **Hottest-Stocks-Algorithmus** klar definieren — welche Metriken, welche Gewichtung?
- [ ] **Begleitende Lernnotizen** in julio-brain/40_Knowledge/Finance/ zu jeder neuen Metrik

## Woche 4 (17.05. — 23.05.) — Brain Layer aktivieren

**Ziel:** Das zweite Gehirn fängt an, Wert zu liefern.

- [ ] **CV** in `julio-brain/20_Career/00_CV.md`
- [ ] **Karriereoptionen-Notizen:** je eine pro Pfad (PE, M&A, IB, VC, Consulting, Startup) mit Pro/Contra
- [ ] **Daily-Note-Routine:** 5-10 Min/Tag in Obsidian
- [ ] **Erste Decision-Frame-Session:** Claude Code mit Vault-Zugriff für eine echte Karrierefrage nutzen
- [ ] **(Optional) Podcast-Pipeline-Test:** 1 Podcast → Transkript → Summary in julio-brain/40_Knowledge/Podcasts/

---

## Nach 4 Wochen — was du hast

- ✅ Funktionierendes Dashboard mit professionellem UI
- ✅ Daily Briefing per Button-Klick
- ✅ Portfolio Tracker mit echten Bewertungs-Metriken
- ✅ Wachsendes zweites Gehirn in Obsidian
- ✅ Vorzeigbares Projekt für Bewerbungsgespräche

---

## Backlog (für später)

- Trade-Republic-Integration (sobald aktiver Trader)
- Vollautomatisches Briefing via Cron + API
- Podcast-Pipeline produktiv
- Mail-Integration (Gmail MCP authentifizieren)
- Calendar-Integration (Google Calendar MCP authentifizieren)
- Mobile/PWA-Version des Dashboards
