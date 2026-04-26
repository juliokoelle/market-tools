# Status nach Stock Analyzer 2.0 — 2026-04-26

## Was heute gebaut wurde

### 1. Daily-Note Automation
- `scripts/fetch_calendar_today.py` — Apple Calendar via osascript, TCC-kompatibel
- `scripts/create_daily_note.py` — erstellt/appended Daily Notes in `~/projects/julio-brain/10_Daily/` mit Kalender, Briefing-Link, Reflexions-Template
- `scripts/fetch_calendar_google.py` — inaktiver Skeleton für Google Calendar
- `~/.claude/commands/daily-note.md` — globaler Claude-Code-Command `/daily-note`
- `config/models.yaml` — Haiku-Modell-Eintrag hinzugefügt

### 2. Stock Analyzer 2.0

| Datei | Was |
|-------|-----|
| `config/watchlist.yaml` | 7 Kategorien, 26 Ticker (Big Tech, Semis, Energy, Clean Energy, Luxury, ETFs, Crypto) |
| `scripts/scoring.py` | `bull_score()`: Momentum 30% + Sentiment 30% (Haiku) + Valuation 20% + Analyst 20%. Crypto: 50/50 ohne P/E |
| `scripts/api.py` | 4 neue Endpoints, Cache-TTLs, ThreadPoolExecutor für paralleles Fetching |
| `frontend/index.html` | Stock Analyzer Tab komplett neu: Watchlist-Grid + Detail-Modal mit Plotly-Chart |
| `tests/test_scoring.py` | 29 Unit Tests für reine scoring-Funktionen |

---

## Was ist live (nach Render-Redeploy ~5min)

**Backend:** `https://market-tools-backend-my0v.onrender.com`

| Endpoint | Was |
|----------|-----|
| `GET /watchlist` | Alle 26 Ticker mit Bull Score, parallel via ThreadPoolExecutor, 5min Cache |
| `GET /stock/{ticker}/detail` | Bull Score + Firmendaten (longName, sector, market_cap) |
| `GET /stock/{ticker}/chart?period=3mo` | OHLCV-Daten für Plotly, 15min Cache |
| `GET /stock/{ticker}/ai-summary` | Sonnet-Narrativ-Analyse, 6h Cache |
| `GET /debug/env` | API-Keys + GitHub-Config Status |

**Frontend:** `https://market-tools-1.onrender.com`
- Stock Analyzer Tab zeigt jetzt Watchlist-Grid
- Auf Ticker klicken → Detail-Modal mit Plotly-OHLC-Chart

---

## Smoke-Test wenn du zurück bist

```bash
# 1. Backend wach? (kann nach Inaktivität ~30s brauchen)
curl https://market-tools-backend-my0v.onrender.com/

# 2. Watchlist lädt (alle 7 Kategorien)?
curl https://market-tools-backend-my0v.onrender.com/watchlist | python3 -c "
import sys, json
d = json.load(sys.stdin)
for cat in d['categories']:
    t0 = cat['tickers'][0]
    print(cat['name'], '→', t0['ticker'], 'score:', t0['bull_score'])
"

# 3. Europäischer Ticker funktioniert?
curl "https://market-tools-backend-my0v.onrender.com/stock/MC.PA/detail" | python3 -c "
import sys, json; d = json.load(sys.stdin)
print(d.get('ticker'), d.get('bull_score'), d.get('company_name'))
"

# 4. Crypto-Ticker (nur 2 Komponenten)?
curl "https://market-tools-backend-my0v.onrender.com/stock/BTC-USD/detail" | python3 -c "
import sys, json; d = json.load(sys.stdin)
print('is_crypto:', d.get('is_crypto'))
print('components:', list(d.get('components', {}).keys()))
"

# 5. Chart-Daten vorhanden?
curl "https://market-tools-backend-my0v.onrender.com/stock/NVDA/chart?period=3mo" | python3 -c "
import sys, json; d = json.load(sys.stdin)
print('rows:', len(d['ohlcv']), '| first:', d['ohlcv'][0])
"

# 6. AI Summary (kostet ~$0.01)
curl "https://market-tools-backend-my0v.onrender.com/stock/NVDA/ai-summary" | python3 -c "
import sys, json; d = json.load(sys.stdin)
print(d.get('summary', '')[:200])
"

# 7. Frontend: Browser öffnen → Stock Analyzer Tab anklicken
# → Skeleton sichtbar → nach ~15s Ticker-Cards mit Scores geladen
# → Auf AAPL klicken → Detail-Modal mit Plotly-Chart
```

---

## Bekannte Probleme und Einschränkungen

### Europäische Ticker (MC.PA, ASM.AS, BRBY.L, CFR.SW)
**Symptom:** `bull_score` fällt oft auf 50 (neutraler Default).
**Ursache:** yfinance gibt für europäische Ticker häufig HTTP 401 zurück wenn `Ticker.info` aufgerufen wird (yfinance cookie/crumb-Problem). Das betrifft Valuation und Analyst-Komponenten.
**Was passiert:** Beide Komponenten fallen auf Score=50 (neutral), werden aber korrekt ins JSON geschrieben mit `{"error": "..."}` im `details`-Feld.
**Momentum und Sentiment funktionieren** — `yf.download()` ist robuster als `.info`.
**Fix wenn kritisch:** yfinance upgraden oder `Ticker.info` durch direkten API-Call ersetzen.

### VWCE.DE
Nicht im Watchlist-YAML. Falls du willst: `config/watchlist.yaml` → ETFs-Sektion, Eintrag `VWCE.DE` hinzufügen.

### Render Free Tier — Cold Start
Nach >15min Inaktivität braucht der Server ~30s zum Aufwachen. Der `/watchlist`-Request lädt dann alle 26 Ticker parallel (dauert ~10-20s beim ersten Mal wegen Haiku-API-Calls). Beim zweiten Request: 5min-Cache aktiv, Antwort <1s.

### Haiku-Rate-Limit bei parallelem Fetching
Bei 26 gleichzeitigen Haiku-Calls sieht man gelegentlich HTTP 429 vom Anthropic API — Haiku hat automatische Retries (exponential backoff). Das verlangsamt den ersten Watchlist-Load um ~2-5s aber führt nicht zu Fehlern.

### `SHEL` statt `SHELL.AS`
Im Watchlist ist `SHEL` (Shell plc NYSE ADR), nicht die Euronext Amsterdam Notierung. Daten kommen, aber es ist die US ADR, nicht die europäische Aktie.

### AI Summary Cache
6h-Cache bedeutet: der erste Request des Tages kostet ~$0.01 pro Ticker (Sonnet). Danach kostenlos bis Cache abläuft. Nicht automatisch aufgerufen — nur wenn User auf "Generate" klickt.

---

## Was noch offen ist (für nächste Session)

- [ ] Favoriten-System: bestimmte Ticker oben pinnen
- [ ] Watchlist konfigurierbar machen (Ticker hinzufügen/entfernen aus UI)
- [ ] VWCE.DE / weitere europäische ETFs hinzufügen
- [ ] yfinance `.info` Fallback auf alternativen Datenprovider für EU-Ticker
- [ ] Portfolio-Integration: eigene Holdings im Watchlist hervorheben
