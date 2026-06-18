# Personal Intelligence OS — VPS-Migration + Recall-Loop (Design)

**Datum:** 2026-06-19
**Status:** Design genehmigt, Implementierungsplan ausstehend

## Ziel

Das persönliche Ökosystem (Telegram-Bot + Market-Tools-Backend + Daten-Verarbeitung) von „läuft auf dem Mac / Render mit Cold Starts" auf eine **always-on Box (Hetzner VPS + Coolify)** heben — **und** die Intelligenz-Schleife schließen, sodass der Bot aus Julios eigenem Wissen antwortet statt generisch.

Leitprinzip: **höchste Qualität, kein weggeworfener Code.** Der bestehende, getestete Python-Code (`telegram_bot.py`, `classifier.py`, `capture_router.py`, `sync_to_brain.py`) bleibt erhalten; es ändert sich primär *wo* er läuft und *dass Recall dazukommt*.

## Ausgangslage (Ist-Zustand)

- **Telegram-Bot:** Python (`python-telegram-bot`), Polling, läuft als **Mac LaunchAgent** (`com.julio.telegram-bot.plist`, KeepAlive) → tot sobald Mac schläft/aus.
- **Capture-Pipeline (funktioniert, bleibt):** Text/Voice (Whisper)/Photo (GPT-4o Vision) → `classifier.py` (Claude Haiku → 9 Item-Typen) → Inline-Button-Confirmation → `capture_router.py` → Obsidian (GitHub Contents API) + MyWardrobe-API + Market-Tools-Watchlist.
- **Item-Typen:** wishlist, stock_pick, gift_idea, reminder, task, task_done, question, idea, note.
- **Market-Tools:** FastAPI-Backend + React/Vite-Frontend auf **Render** (Cold Starts; yfinance `.info` auf Render-IP gedrosselt).
- **Halbfertiger Altplan:** `infra/MIGRATION.md` + `infra/docker-compose.yml` setzen auf **n8n** (Bot als Visual-Workflow neu bauen) → **verworfen**, weil getesteter Code wegfiele.
- **gbrain** (PGLite-Brain) ist lokal vorhanden, aber **nicht** mit dem Bot verbunden.

### Identifizierte Schwachstellen
1. **Verfügbarkeit:** Mac-Abhängigkeit → Bot unzuverlässig.
2. **Offene Schleife:** Infos fließen rein (Telegram → Obsidian), kommen nie intelligent zurück. Frage-Antworten kommen von nacktem Haiku **ohne Kontext** von Julios Daten → generisch.
3. **Drei getrennte Speicher** (Obsidian, gbrain, Market-Tools) ohne Verbindung.
4. **Render-Cold-Start-Hack** im Router (`stock_pick`: 35s-Timeout, um Render-Spin-up zu überleben).

## Zielarchitektur

**Eine Hetzner-Box mit Coolify hostet das persönliche Ökosystem. Vercel-Apps + Supabase bleiben unangetastet.**

### Auf den VPS (Coolify-Services, Docker)
| Service | Herkunft | Änderung |
|---|---|---|
| `market-tools-backend` (FastAPI) | Render | always-on, kein Cold Start |
| `redis` | neu | Cache vor yfinance |
| `data-refresh` (Cron) | neu | holt Marktdaten periodisch in Redis |
| `telegram-bot` (Python) | Mac LaunchAgent | always-on, Polling unverändert |
| `market-tools-frontend` (statisch) | Render | als **PWA** (Handy-Icon, täglich nutzbar) |

### Bleibt wie es ist
- Vercel-Apps: HorseFinder, Cognify IQ, Predict 26 Elite, MyWardrobe (skalieren elastisch auf Vercel).
- Supabase.
- Daily-Briefing über GitHub Actions (läuft bereits zuverlässig in der Cloud).

### Schlüssel-Entscheidungen (mit Begründung)
1. **Coolify statt n8n.** Bestehender Python-Code wird per Docker deployt, nicht als n8n-Workflow nachgebaut. → null Rework, Tests bleiben gültig.
2. **Polling statt Webhook** für den Bot. Auf always-on VPS sofort schnell genug, kein öffentlicher HTTPS-Endpunkt/SSL für den Bot nötig, **keine** Code-Änderung. (Der n8n-Plan wollte Webhook — unnötige Komplexität.)
3. **Recall-Loop verdrahten (der eigentliche Qualitätssprung):** `question`-Items werden nicht mehr von nacktem Haiku beantwortet, sondern mit **gbrain-Recall** über Julios eigene Daten angereichert (Vault + Captures als Kontext). Der Bot wird vom Ablage- zum Wissens-Assistenten.
4. **Redis-Cache vor yfinance** → Daten echt „live", und die Drosselungs-Workarounds (statische Sektor-Maps, EUR-Mislabeling-Schutz, 35s-Timeout im Router) können entfernt werden.
5. **Mac-LaunchAgents bleiben als Rollback** liegen (nur deaktiviert).

### Datenfluss (Zielzustand)
```
Telegram → Bot (VPS, always-on) → classifier → confirmation → capture_router
                                                                  ├─ Obsidian (GitHub API)
                                                                  ├─ MyWardrobe API
                                                                  └─ Market-Tools (VPS)

Frage (question) → capture_router → gbrain-Recall (Julios Daten) → Antwort + Ablage

Handy-PWA / Browser → Frontend (VPS) → FastAPI (VPS) → Redis-Cache ⇄ Cron-Refresh → yfinance
```

## Migrations-Reihenfolge (high-level, Details im Plan)
1. Hetzner-Server + Coolify aufsetzen (SSL, Subdomain falls vorhanden, sonst Coolify-Auto-Domain).
2. FastAPI-Backend als Coolify-Service deployen; per Env auf VPS-URL umstellen.
3. Redis + Cron-Refresh ergänzen; Cache-Layer vor yfinance; Drosselungs-Workarounds entfernen.
4. Telegram-Bot als Coolify-Service deployen (Env-Vars übernehmen).
5. gbrain-Recall in `capture_router._answer_question` verdrahten.
6. Frontend als PWA bauen + auf VPS deployen.
7. Verifizieren (Bot empfängt, Captures landen, Frage wird aus Brain beantwortet, Marktdaten frisch).
8. Mac-LaunchAgents deaktivieren; Render kündigen.

## Rollback
- Mac-LaunchAgents wieder laden (`launchctl load …`).
- Backend-URL zurück auf Render-Env.
- Telegram bleibt bei Polling (kein Webhook zu deregistrieren).

## Out of Scope (spätere Sub-Projekte)
- Vercel-Apps migrieren (bleiben absichtlich auf Vercel).
- Next-Best-Actions / Calendar-Tasks im Dashboard (kein Datenquelle-Endpunkt).
- Daily-Briefing von GitHub Actions wegziehen.
- Voll-Konsolidierung der drei Speicher in einen (nur Recall-Brücke jetzt, keine Migration).
