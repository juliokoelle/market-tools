# n8n Migration Guide

Migration von Mac LaunchAgents → n8n auf Hetzner VPS.

---

## Schritt 1 — Hetzner Server erstellen

1. Gehe zu [hetzner.com/cloud](https://hetzner.com/cloud) → neues Projekt
2. Server erstellen:
   - **Typ:** CX11 (1 vCPU, 2 GB RAM) — €3.29/Monat
   - **Image:** Ubuntu 24.04
   - **Location:** Nürnberg oder Helsinki
   - **SSH Key:** deinen public key einfügen
3. Server IP notieren (z.B. `1.2.3.4`)

---

## Schritt 2 — Domain / DNS

Option A (günstig): Subdomain bei deinem bestehenden Registrar  
Option B (kostenlos): Cloudflare kostenlose Zone

DNS A-Record setzen:
```
n8n.juliokoelle.de  →  1.2.3.4   (TTL 300)
```

---

## Schritt 3 — VPS einrichten

```bash
ssh root@1.2.3.4
curl -fsSL https://raw.githubusercontent.com/juliokoelle/market-tools/main/infra/setup.sh | bash
```

Oder manuell:
```bash
scp ~/projects/automation/infra/setup.sh root@1.2.3.4:/root/
ssh root@1.2.3.4 bash /root/setup.sh
```

---

## Schritt 4 — Credentials eintragen

```bash
ssh root@1.2.3.4
nano /opt/n8n/.env
```

Alle Felder aus `.env.example` ausfüllen. Dann SSL:

```bash
certbot --nginx -d n8n.juliokoelle.de
```

---

## Schritt 5 — n8n starten

```bash
ssh root@1.2.3.4
cd /app/automation
docker compose -f infra/docker-compose.yml --env-file /opt/n8n/.env up -d
```

n8n läuft jetzt auf `https://n8n.juliokoelle.de`  
Login: Credentials aus `.env` (`N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD`)

---

## Schritt 6 — Workflows importieren

In n8n UI → **Workflows** → **Import from file** — jeweils:
1. `workflows/gmail-briefing.json`
2. `workflows/telegram-bot.json`
3. `workflows/morning-push.json`
4. `workflows/stock-alerts.json`

**Telegram Credential anlegen:**  
Settings → Credentials → New → Telegram API → Bot Token eintragen. Name: `Telegram Bot`.

---

## Schritt 7 — Telegram Webhook setzen

Telegram muss wissen, dass Nachrichten jetzt zu n8n gehen:

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://n8n.juliokoelle.de/webhook/telegram-bot"
```

Erwartete Antwort: `{"ok":true,"result":true}`

**TELEGRAM_CHAT_ID herausfinden:**  
Eine Nachricht an den Bot schicken → in n8n unter Executions den Trigger anschauen → `message.chat.id` kopieren → in `/opt/n8n/.env` als `TELEGRAM_CHAT_ID` eintragen → n8n neu starten:

```bash
docker compose -f /app/automation/infra/docker-compose.yml --env-file /opt/n8n/.env restart n8n
```

---

## Schritt 8 — Render `/capture` Endpoint testen

```bash
curl -X POST https://market-tools-backend-my0v.onrender.com/capture \
  -H "Content-Type: application/json" \
  -d '{"text": "NVDA auf Watchlist"}'
```

Erwartete Antwort: `{"reply": "📊 *NVDA* ..."}` oder `{"reply": null}`

---

## Schritt 9 — Mac LaunchAgents deaktivieren

Erst wenn alles auf n8n läuft und getestet ist:

```bash
# Telegram Bot deaktivieren
launchctl unload ~/Library/LaunchAgents/com.julio.telegram-bot.plist

# Gmail Briefing deaktivieren
launchctl unload ~/Library/LaunchAgents/com.julio.gmail-briefing.plist
```

Die Plist-Dateien bleiben — so kann man jederzeit zurückrollen:
```bash
launchctl load ~/Library/LaunchAgents/com.julio.telegram-bot.plist
```

---

## Übersicht nach Migration

| Komponente | Vorher (Mac) | Nachher (VPS) |
|---|---|---|
| Gmail Briefing | LaunchAgent 08:15/09/10 | n8n Schedule |
| Telegram Bot | LaunchAgent KeepAlive | n8n Webhook |
| Morning Push | ❌ nicht vorhanden | n8n Schedule 08:30 |
| Stock Alerts | ❌ nicht vorhanden | n8n Schedule 20:00 |
| Market Tools API | Render (unverändert) | Render (unverändert) |

---

## Rollback

Falls etwas schiefläuft:
1. LaunchAgents wieder laden (Schritt 9 rückgängig)
2. Telegram Webhook zurücksetzen auf langen Polling: `deleteWebhook`
```bash
curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```
