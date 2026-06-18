# Infra-Migration: Render → Hetzner VPS + Coolify — Implementation Plan

> **Für die Umsetzung:** Infrastruktur-Migration mit manuellen Ops-Schritten + wenigen Repo-Änderungen. Schritte mit Checkbox (`- [ ]`). Jeder Schritt markiert, **wer** ihn macht: **[JULIO]** = manuell (Account/Login/Klick), **[CLAUDE]** = Repo-Code/Datei.

**Goal:** Das FastAPI-Backend und den Telegram-Bot von Render (Free, Cold Starts, gedrosselt) auf einen Hetzner-VPS mit Coolify (self-hosted PaaS) umziehen, sodass beide always-on und flüssig laufen.

**Architecture:** Ein Hetzner-VPS (CX22) hostet Coolify. Coolify deployt **ein** GitHub-Repo (`juliokoelle/market-tools`) als Docker-Compose-Stack mit zwei Services aus demselben Image: `backend` (uvicorn, öffentlich über Domain+TLS) und `telegram-bot` (Polling, kein Port, kein öffentlicher Zugang). Frontend bleibt vorerst auf Render/Vercel und zeigt nur per `VITE_API_URL` auf die neue Backend-Domain.

**Tech Stack:** Hetzner Cloud (CX22), Coolify (Docker + Traefik/Caddy für TLS), bestehendes `Dockerfile` (python:3.11-slim, uvicorn), python-telegram-bot (Polling).

## Global Constraints

- Repo: `juliokoelle/market-tools` = `/Users/juliokoelle/projects/automation`, Branch `main`.
- Backend-Entrypoint: `uvicorn scripts.api:app` auf Port `8000` (aus `Dockerfile`).
- Bot-Entrypoint: `python -m scripts.telegram_bot` (Polling, `app.run_polling()`).
- **Render erst abschalten, wenn der neue Stack grün ist** — kein Big-Bang-Cutover.
- Secrets NIE ins Repo committen — nur in der Coolify-UI eintragen.
- Env-Var-Inventar (13), das beide Services brauchen:
  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GITHUB_TOKEN`, `BRAIN_GITHUB_TOKEN`,
  `JULIO_BRAIN_OWNER`, `JULIO_BRAIN_REPO_NAME`, `NEWS_API_KEY`, `TWELVE_DATA_API_KEY`,
  `SUPABASE_URL`, `SUPABASE_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_OWNER_ID`.

---

## Phase 0: Sicherheit & Secrets sammeln (vor allem anderen)

**Warum zuerst:** In `.git/config` steckt ein GitHub-PAT im Klartext (`origin`-URL). Der ist beim Survey in der Konsole gelandet → gilt als kompromittiert.

- [ ] **Step 1 [JULIO]: GitHub-PAT rotieren.** GitHub → Settings → Developer settings → Personal access tokens → den Token `github_pat_11BAK…` **revoken** und neuen erstellen (nur nötige Scopes: `repo`). Neuen Token notieren.
- [ ] **Step 2 [CLAUDE]: Remote-URL säubern.** Token aus der Remote entfernen (`git remote set-url origin https://github.com/juliokoelle/market-tools.git`) und Auth über Credential-Helper/`gh` laufen lassen. (Separater Mini-Task, wenn Julio den neuen Token hat.)
- [ ] **Step 3 [JULIO]: Secrets-Werte bereitlegen.** Aus dem aktuellen Render-Dashboard (Environment-Tab beider Services) die 13 Env-Var-Werte kopieren — am besten in einen temporären, lokalen Notizzettel. Coolify braucht sie in Phase 3.

**Deliverable:** Neuer GitHub-Token, saubere Remote, alle 13 Secret-Werte griffbereit.

---

## Phase 1: Hetzner-VPS provisionieren + Coolify installieren

**Warum CX22:** 2 vCPU / 4 GB RAM / 40 GB SSD, ~€4–5/Monat. Reicht locker für FastAPI + Bot + Coolify selbst. `weasyprint`/`pandas` sind die speicherhungrigsten Teile — 4 GB sind komfortabel. Hochskalieren (CX32 = 8 GB) geht in Hetzner per Klick ohne Neuinstallation.

- [ ] **Step 1 [JULIO]: Hetzner-Cloud-Account + Projekt.** Auf console.hetzner.cloud anmelden, neues Projekt „market-tools" anlegen.
- [ ] **Step 2 [JULIO]: Server erstellen.** Add Server → Location: **Nuremberg/Falkenstein** (DE) → Image: **Ubuntu 24.04** → Type: **CX22** → SSH-Key hinterlegen (eigenen Public Key hochladen; falls keiner: `ssh-keygen -t ed25519` lokal). Server erstellen, **öffentliche IP notieren**.
- [ ] **Step 3 [JULIO]: Per SSH einloggen.** Lokal im Terminal: `ssh root@<VPS-IP>` (Tipp: in dieser Session mit `! ssh root@<IP>` ausführen, dann landet die Ausgabe hier).
- [ ] **Step 4 [JULIO]: Coolify installieren.** Auf dem Server: `curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash`. Dauert ~2–3 Min. Am Ende zeigt es die URL `http://<VPS-IP>:8000`.
- [ ] **Step 5 [JULIO]: Coolify-Admin anlegen.** Im Browser `http://<VPS-IP>:8000` öffnen, ersten Admin-User (E-Mail + Passwort) registrieren.

**Deliverable:** Erreichbare Coolify-Instanz, eingeloggt als Admin.

---

## Phase 2: Repo für Coolify vorbereiten (Two-Service-Compose)

**Warum:** Render lief mit zwei separaten Services. Auf Coolify deployen wir **ein** Repo als Compose-Stack — beide Services teilen sich dasselbe gebaute Image (`build: .`), nur das Start-Kommando unterscheidet sich. So baut Coolify einmal und betreibt Backend + Bot zusammen.

**Files:**
- Create: `docker-compose.coolify.yml`

**Interfaces:**
- Consumes: bestehendes `Dockerfile` (Build-Kontext = Repo-Root), `scripts.api:app`, `scripts/telegram_bot.py`.
- Produces: Compose-Stack mit Services `backend` (Port 8000) und `telegram-bot` (kein Port).

- [ ] **Step 1 [CLAUDE]: Compose-Datei anlegen.**

```yaml
# docker-compose.coolify.yml
# Coolify-Deployment: FastAPI-Backend + Telegram-Bot aus EINEM Image.
# Env-Vars werden in der Coolify-UI gesetzt (NICHT hier committen).
services:
  backend:
    build: .
    command: uvicorn scripts.api:app --host 0.0.0.0 --port 8000
    restart: unless-stopped
    # Coolify mappt die öffentliche Domain auf diesen Port:
    expose:
      - "8000"

  telegram-bot:
    build: .
    command: python -m scripts.telegram_bot
    restart: unless-stopped
    # Kein Port: Polling-Bot, braucht keinen eingehenden Verkehr.
```

- [ ] **Step 2 [CLAUDE]: Committen.**

```bash
git add docker-compose.coolify.yml
git commit -m "infra: add Coolify two-service compose (backend + telegram bot)"
git push
```

Erwartet: Push grün, kein Render-Auto-Deploy-Bruch (Render nutzt `render.yaml`, ignoriert die neue Datei).

**Deliverable:** Compose-Datei auf `main`, bereit für Coolify-Resource.

---

## Phase 3: Backend auf Coolify deployen (Domain + TLS + Secrets)

- [ ] **Step 1 [JULIO]: GitHub mit Coolify verbinden.** Coolify → Sources → GitHub App installieren und Zugriff auf `juliokoelle/market-tools` geben.
- [ ] **Step 2 [JULIO]: Resource anlegen.** Coolify → Projects → „market-tools" → + New Resource → **Docker Compose** → Repo `market-tools`, Branch `main`, Compose-Datei-Pfad: `docker-compose.coolify.yml`.
- [ ] **Step 3 [JULIO]: Env-Vars eintragen.** In der Resource → Environment Variables alle 13 aus dem Global-Constraints-Block einfügen (als „shared", damit beide Services sie sehen).
- [ ] **Step 4 [JULIO]: Domain + TLS.** Service `backend` → Domains → eigene (Sub-)Domain setzen, z. B. `api.<deine-domain>.de`, Port `8000`. Coolify holt automatisch ein Let's-Encrypt-Zertifikat (Traefik). Vorher beim DNS-Provider einen **A-Record** `api → <VPS-IP>` anlegen.
- [ ] **Step 5 [JULIO]: Deploy.** „Deploy" klicken. Logs beobachten bis `Application Exited`-frei und uvicorn auf 8000 läuft.
- [ ] **Step 6 [JULIO/CLAUDE]: Smoke-Test Backend.** `curl -s https://api.<deine-domain>.de/health` (oder ein bekannter Endpoint wie `/market/...`) → erwartet HTTP 200 / valides JSON. (Claude prüft, welcher Health-/Root-Endpoint in `scripts/api.py` existiert, und nennt die exakte URL.)

**Deliverable:** Backend öffentlich erreichbar über HTTPS-Domain, liefert Daten.

---

## Phase 4: Telegram-Bot scharf schalten, Render-Bot abschalten

**Warum getrennt von Backend:** Polling-Bots dürfen nur **einmal** laufen — sonst kollidieren zwei `getUpdates`-Loops. Daher Render-Bot stoppen, bevor/sobald der Coolify-Bot läuft.

- [ ] **Step 1 [JULIO]: Render-Bot stoppen.** Im Render-Dashboard den Bot-Service suspendieren (falls dort als eigener Worker läuft). Falls der Bot bisher gar nicht zuverlässig lief (bekanntes Problem): nur sicherstellen, dass kein zweiter Polling-Prozess aktiv ist.
- [ ] **Step 2 [JULIO]: Coolify-Bot-Logs prüfen.** Service `telegram-bot` → Logs → erwartet `Telegram bot starting — polling.` ohne `Conflict: terminated by other getUpdates`.
- [ ] **Step 3 [JULIO]: Funktionstest.** Im Telegram-Chat eine Nachricht an den Bot senden → erwartet Antwort/Routing wie gewohnt.

**Deliverable:** Genau ein Bot-Prozess (auf Coolify), reagiert im Chat.

---

## Phase 5: Frontend auf neue Backend-Domain umstellen

**Warum:** `frontend/src/services/api.ts:3` nutzt bereits `import.meta.env.VITE_API_URL` und fällt nur auf die alte Render-URL zurück, wenn die Var fehlt. Wir setzen die Var beim Build → kein Code-Umbau nötig.

**Files:**
- Modify: `frontend/.env.production` (oder Build-Env beim Hosting) — `VITE_API_URL`
- Optional Modify: `frontend/src/services/api.ts:6` (Fallback-URL aktualisieren)

- [ ] **Step 1 [CLAUDE]: Build-Env setzen.** `VITE_API_URL=https://api.<deine-domain>.de` als Production-Build-Variable hinterlegen (in `frontend/.env.production` bzw. beim aktuellen Hosting-Anbieter).
- [ ] **Step 2 [CLAUDE]: Fallback aktualisieren (Sicherheitsnetz).** In `frontend/src/services/api.ts:6` die hartkodierte Render-URL durch die neue Backend-Domain ersetzen, damit auch ohne gesetzte Var richtig gezeigt wird.
- [ ] **Step 3 [CLAUDE]: Frontend neu deployen.** `cd frontend && npm run deploy` (baut dist, committet, pusht). Erwartet: Build grün.
- [ ] **Step 4 [JULIO/CLAUDE]: Smoke-Test `/market`.** Frontend öffnen, alle Tabs durchklicken (Dashboard, Hot-Stocks, Portfolio, Watchlist) → Daten kommen von der neuen Domain (Network-Tab prüfen).

**Deliverable:** Frontend zieht Daten vom Hetzner-Backend, alle Tabs grün.

---

## Phase 6: Render abschalten

- [ ] **Step 1 [JULIO]: 24–48 h beobachten.** Backend-/Bot-Logs in Coolify auf Fehler/Memory prüfen. Daten-Frische gegenüber Render-Problemen verifizieren.
- [ ] **Step 2 [JULIO]: Render-Services löschen/suspendieren.** Backend + (falls vorhanden) Bot auf Render entfernen, sobald Hetzner stabil grün ist.
- [ ] **Step 3 [CLAUDE]: Repo aufräumen.** `render.yaml` und `infra/docker-compose.yml` (altes n8n-Konzept) als veraltet markieren oder entfernen, README/ARCHITECTURE auf Coolify aktualisieren.
- [ ] **Step 4 [CLAUDE]: Doku.** Obsidian-Note in `20_Career/HDP/` (oder Markt-Tools-Bereich) mit Ziel · Vorgehen · Annahmen · Lessons · Ergebnis-Links · Status anlegen. Memory `project-infra-migration-render-to-hetzner` auf „umgesetzt" aktualisieren.

**Deliverable:** Render abgeschaltet, Repo + Doku aktuell, Migration abgeschlossen.

---

## Self-Review-Notiz

- Scope = nur Backend + Telegram-Bot (Julios Entscheidung). Vercel-Apps (Cognify, HorseFinder, MyWardrobe, Predict 26) bleiben unberührt — bewusst ausgeklammert.
- Offen/zu verifizieren beim Bauen: exakter Health-Endpoint in `scripts/api.py` (Phase 3 Step 6); ob der Bot auf Render aktuell überhaupt als eigener Service existiert (Phase 4 Step 1); ob das Backend einen persistenten Volume braucht — Annahme **nein**, da Portfolio-Store GitHub-backed ist (kein lokaler State).
