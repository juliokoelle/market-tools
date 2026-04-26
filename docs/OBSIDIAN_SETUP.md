# Obsidian Git Setup Guide

Ziel: Obsidian-Vault (`~/projects/julio-brain`) automatisch mit GitHub synchronisieren.

---

## 1. Plugin installieren

1. Obsidian öffnen → **Settings** → **Community Plugins** → **Browse**
2. Suchen: `Obsidian Git`
3. Installieren + Aktivieren

Das Plugin erkennt das bestehende Git-Repo in `~/projects/julio-brain` automatisch.

---

## 2. Auto-Pull konfigurieren

Settings → Obsidian Git:

| Einstellung | Wert |
|---|---|
| **Pull interval (minutes)** | `5` |
| **Pull on startup** | ✅ an |
| **Merge strategy** | `Merge` (nicht Rebase) |

Der Pull holt täglich neue Briefings, die der Render-Server via GitHub API gepusht hat.

---

## 3. Auto-Commit + Push konfigurieren

| Einstellung | Wert |
|---|---|
| **Auto commit-and-sync interval (minutes)** | `10` |
| **Auto commit-and-sync when app is active** | ✅ an |
| **Commit message** | `vault: auto-sync {{date}}` |
| **Push after commit** | ✅ an |

Damit werden manuelle Notizen, Änderungen und neue Dateien alle 10 Minuten committet und gepusht.

---

## 4. Authentifizierung: Token oder SSH?

### Empfehlung: HTTPS + macOS Keychain (bereits funktionsfähig)

Das Repo nutzt bereits HTTPS (`https://github.com/juliokoelle/julio-brain.git`) und der Push funktioniert lokal über den macOS Keychain. Obsidian Git nutzt denselben git-Credential-Store.

**Kein weiterer Setup nötig** — solange du einmal per `git push` aus dem Terminal authentifiziert bist (bereits erledigt).

### Alternative: SSH

SSH ist langfristig robuster (kein Token-Ablauf), erfordert aber einmaligen Setup:

```bash
# SSH-Key generieren (falls noch keiner vorhanden)
ssh-keygen -t ed25519 -C "juliokoelle@gmail.com"

# Public key in GitHub hinterlegen:
# Settings → SSH and GPG keys → New SSH key
cat ~/.ssh/id_ed25519.pub

# Remote auf SSH umstellen
cd ~/projects/julio-brain
git remote set-url origin git@github.com:juliokoelle/julio-brain.git
```

### Warum KEIN Personal Access Token in Obsidian Git?

Das Plugin speichert Tokens im Vault selbst (`.obsidian/plugins/obsidian-git/data.json`). Das ist nur akzeptabel für ein **privates** Repo ohne sensible Daten. Das julio-brain Repo ist privat — vertretbar, aber HTTPS + Keychain ist sicherer weil der Token nicht im Plugin liegt.

---

## 5. iOS (Mobile)

### Was funktioniert

- **Lesen**: Obsidian Mobile kann das Vault über iCloud oder Working Copy (Git-App) öffnen
- **Obsidian Git Plugin auf iOS**: grundsätzlich unterstützt, aber instabil

### Was nicht funktioniert / eingeschränkt ist

- Auto-Sync im Hintergrund: iOS erlaubt keine Hintergrundprozesse — Sync nur beim aktiven Öffnen der App
- HTTPS-Authentifizierung: erfordert manuellen Token-Eintrag im Plugin (kein Keychain-Zugriff)
- Push/Pull zuverlässig: funktioniert, aber muss manuell getriggert werden (Button in der Statusleiste)

### Empfohlener Mobile-Workflow

1. **Working Copy** (iOS App, ~$20 einmalig) als Git-Client installieren
2. Repo klonen: `https://github.com/juliokoelle/julio-brain.git`
3. Working Copy ↔ Obsidian Mobile via iOS-Dateisystem verbinden
4. Pull in Working Copy vor dem Öffnen in Obsidian
5. Push in Working Copy nach dem Schreiben

Alternativ: nur Lesen auf Mobile (neues Briefing erscheint nach dem nächsten Pull), Schreiben ausschließlich auf dem Mac.

---

## Zusammenfassung

| Aktion | Wo | Frequenz |
|---|---|---|
| Briefings pushen | Render-Server → GitHub API | Bei Generierung |
| Vault pullen | Obsidian (Mac) | Alle 5 Min automatisch |
| Notizen pushen | Obsidian (Mac) | Alle 10 Min automatisch |
| Mobile lesen | Working Copy → Obsidian iOS | Manuell |
