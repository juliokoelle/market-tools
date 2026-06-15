# Portfolio Daten-Integrität (Fundament) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Korrupte Portfolio-Zahlen beheben (Smart-Dezimal-Parser), manuelle Stück/Ø-Kauf-Eingabe ermöglichen und den Allocation-Endpoint gegen Yahoo-Throttling absichern.

**Architecture:** Der Zahlen-Parser wird aus `Portfolio.tsx` in ein eigenes, unit-getestetes Modul `frontend/src/lib/parseNum.ts` extrahiert und format-erkennend neu geschrieben. Eine kleine Ticker-Alias-Map (`TELEKOM → DTE.DE`) lebt in `frontend/src/lib/ticker.ts`. Der Editor bekommt zwei zusätzliche Spalten (Stück, Ø-Kaufpreis), die über den Smart-Parser laufen und `investment` automatisch ableiten. Backend: `_alloc_meta` bekommt Retry+Backoff und cached nur erfolgreiche Fetches; `portfolio_allocation` senkt `max_workers` 8→3.

**Tech Stack:** React 19 + TypeScript + Vite (Frontend), Vitest (neu, für Parser-Unit-Tests), FastAPI + yfinance (Backend).

---

## File Structure

- **Create** `frontend/src/lib/parseNum.ts` — Smart-Dezimal-Parser (eine Funktion, eine Verantwortung).
- **Create** `frontend/src/lib/parseNum.test.ts` — Vitest-Unit-Tests deutsch + dezimal-Punkt.
- **Create** `frontend/src/lib/ticker.ts` — `TICKER_ALIASES` + `normalizeTicker`.
- **Create** `frontend/src/lib/ticker.test.ts` — Vitest-Test für Alias.
- **Modify** `frontend/package.json` — `vitest` devDep + `test`-Script.
- **Modify** `frontend/src/pages/Portfolio.tsx` — `parseNum` importieren (lokale Def. an Z.23 entfernen); Editor um Stück/Ø-Kauf erweitern; `handleSave` normalisiert Ticker.
- **Modify** `scripts/api.py` — `_alloc_meta` Retry+Backoff, nur Erfolg cachen; `portfolio_allocation` `max_workers` 8→3.

---

## Task 1: Vitest-Setup

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: vitest installieren**

```bash
cd /Users/juliokoelle/projects/automation/frontend && npm install -D vitest@^2
```

- [ ] **Step 2: test-Script ergänzen**

In `frontend/package.json`, im `"scripts"`-Block nach `"preview": "vite preview"` ergänzen (Komma am Vorzeiger-Eintrag nicht vergessen):

```json
    "preview": "vite preview",
    "test": "vitest run"
```

- [ ] **Step 3: Verifizieren, dass vitest läuft**

Run: `cd /Users/juliokoelle/projects/automation/frontend && npx vitest run`
Expected: "No test files found" (Exit 0 oder Hinweis-Meldung) — vitest ist installiert.

- [ ] **Step 4: Commit**

```bash
cd /Users/juliokoelle/projects/automation && git add frontend/package.json frontend/package-lock.json && git commit -m "chore: add vitest for unit tests"
```

---

## Task 2: Smart-Dezimal-Parser (TDD)

**Files:**
- Create: `frontend/src/lib/parseNum.ts`
- Test: `frontend/src/lib/parseNum.test.ts`

- [ ] **Step 1: Failing-Test schreiben**

Create `frontend/src/lib/parseNum.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { parseNum } from './parseNum'

describe('parseNum', () => {
  it('dezimal-Punkt bleibt erhalten (Bug-Regression)', () => {
    expect(parseNum('162.66')).toBeCloseTo(162.66, 4)
    expect(parseNum('2.9131980000')).toBeCloseTo(2.913198, 6)
  })
  it('deutsches Format: Punkt = Tausender, Komma = Dezimal', () => {
    expect(parseNum('1.234,56')).toBeCloseTo(1234.56, 2)
    expect(parseNum('1.000.000,00')).toBeCloseTo(1000000, 2)
  })
  it('nur Komma = Dezimal-Komma', () => {
    expect(parseNum('162,66')).toBeCloseTo(162.66, 2)
  })
  it('mehrfache Punkte: letzter Block >2 Stellen = Tausender', () => {
    expect(parseNum('1.234.567')).toBeCloseTo(1234567, 0)
  })
  it('mehrfache Punkte: letzter Block <=2 Stellen = Dezimal', () => {
    expect(parseNum('1.234.56')).toBeCloseTo(1234.56, 2)
  })
  it('keine Trenner = parseFloat', () => {
    expect(parseNum('5000')).toBe(5000)
  })
  it('Währungssymbole/Leerzeichen werden ignoriert', () => {
    expect(parseNum('€ 1.626,58')).toBeCloseTo(1626.58, 2)
  })
  it('negativ', () => {
    expect(parseNum('-162.66')).toBeCloseTo(-162.66, 2)
  })
  it('leer/Müll = NaN', () => {
    expect(Number.isNaN(parseNum(''))).toBe(true)
    expect(Number.isNaN(parseNum('abc'))).toBe(true)
  })
})
```

- [ ] **Step 2: Test ausführen, Fehlschlag bestätigen**

Run: `cd /Users/juliokoelle/projects/automation/frontend && npx vitest run src/lib/parseNum.test.ts`
Expected: FAIL — "Cannot find module './parseNum'".

- [ ] **Step 3: Parser implementieren**

Create `frontend/src/lib/parseNum.ts`:

```ts
/**
 * Format-erkennender Dezimal-Parser.
 * - Punkt UND Komma -> deutsch: Punkt = Tausender, Komma = Dezimal.
 * - Nur Komma       -> Dezimal-Komma.
 * - Nur Punkt       -> Dezimal-Punkt (NICHT entfernen); bei mehreren Punkten
 *                      Heuristik: letzter Block <=2 Stellen = Dezimal, sonst Tausender.
 * - Keine Trenner   -> parseFloat.
 * Währungssymbole/Leerzeichen werden vor dem Parsen entfernt.
 */
export function parseNum(s: string | null | undefined): number {
  if (s == null) return NaN
  const t = String(s).replace(/[^0-9.,-]/g, '')
  if (!t || t === '-' || t === '.' || t === ',') return NaN

  const hasDot = t.includes('.')
  const hasComma = t.includes(',')

  if (hasDot && hasComma) {
    return parseFloat(t.replace(/\./g, '').replace(',', '.'))
  }
  if (hasComma) {
    return parseFloat(t.replace(',', '.'))
  }
  if (hasDot) {
    const dotCount = (t.match(/\./g) || []).length
    if (dotCount === 1) return parseFloat(t)
    const idx = t.lastIndexOf('.')
    const lastBlock = t.slice(idx + 1)
    if (lastBlock.length <= 2) {
      return parseFloat(t.slice(0, idx).replace(/\./g, '') + '.' + lastBlock)
    }
    return parseFloat(t.replace(/\./g, ''))
  }
  return parseFloat(t)
}
```

- [ ] **Step 4: Test ausführen, Erfolg bestätigen**

Run: `cd /Users/juliokoelle/projects/automation/frontend && npx vitest run src/lib/parseNum.test.ts`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/juliokoelle/projects/automation && git add frontend/src/lib/parseNum.ts frontend/src/lib/parseNum.test.ts && git commit -m "feat: smart locale-aware number parser"
```

---

## Task 3: Ticker-Alias (TDD)

**Files:**
- Create: `frontend/src/lib/ticker.ts`
- Test: `frontend/src/lib/ticker.test.ts`

- [ ] **Step 1: Failing-Test schreiben**

Create `frontend/src/lib/ticker.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { normalizeTicker } from './ticker'

describe('normalizeTicker', () => {
  it('TELEKOM -> DTE.DE', () => {
    expect(normalizeTicker('TELEKOM')).toBe('DTE.DE')
    expect(normalizeTicker(' telekom ')).toBe('DTE.DE')
  })
  it('unbekannte Ticker bleiben (getrimmt, upper)', () => {
    expect(normalizeTicker('vwce.de')).toBe('VWCE.DE')
  })
})
```

- [ ] **Step 2: Test ausführen, Fehlschlag bestätigen**

Run: `cd /Users/juliokoelle/projects/automation/frontend && npx vitest run src/lib/ticker.test.ts`
Expected: FAIL — "Cannot find module './ticker'".

- [ ] **Step 3: Implementieren**

Create `frontend/src/lib/ticker.ts`:

```ts
/** Bekannte Falsch-Ticker -> gültiges Yahoo-Symbol. */
export const TICKER_ALIASES: Record<string, string> = {
  TELEKOM: 'DTE.DE',
}

export function normalizeTicker(raw: string): string {
  const t = (raw ?? '').trim().toUpperCase()
  return TICKER_ALIASES[t] ?? t
}
```

- [ ] **Step 4: Test ausführen, Erfolg bestätigen**

Run: `cd /Users/juliokoelle/projects/automation/frontend && npx vitest run src/lib/ticker.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/juliokoelle/projects/automation && git add frontend/src/lib/ticker.ts frontend/src/lib/ticker.test.ts && git commit -m "feat: ticker alias normalization (TELEKOM->DTE.DE)"
```

---

## Task 4: Portfolio.tsx auf neuen Parser umstellen

**Files:**
- Modify: `frontend/src/pages/Portfolio.tsx:1-3` (Import), `:23` (lokale parseNum-Def entfernen)

- [ ] **Step 1: Import ergänzen**

In `frontend/src/pages/Portfolio.tsx` nach Zeile 3 (`import { DonutSvg } ...`) einfügen:

```ts
import { parseNum } from '../lib/parseNum'
import { normalizeTicker } from '../lib/ticker'
```

- [ ] **Step 2: Lokale parseNum-Definition entfernen**

In `parseTRCsv` die Zeile (aktuell Z.23) löschen:

```ts
  const parseNum = (s: string) => parseFloat(s.replace(/\./g, '').replace(',', '.'))
```

(Die Aufrufe an Z.54/55 und Z.89-91 bleiben unverändert — sie nutzen jetzt die importierte Funktion.)

- [ ] **Step 3: Build/Typecheck verifizieren**

Run: `cd /Users/juliokoelle/projects/automation/frontend && npx tsc -b`
Expected: Kein Fehler (parseNum-Signatur `string | null | undefined` akzeptiert die `cells[...] ?? ''`-Aufrufe).

- [ ] **Step 4: Commit**

```bash
cd /Users/juliokoelle/projects/automation && git add frontend/src/pages/Portfolio.tsx && git commit -m "fix: use smart parser in TR-CSV import (fixes corrupted shares)"
```

---

## Task 5: Editor um Stück + Ø-Kaufpreis erweitern

**Files:**
- Modify: `frontend/src/pages/Portfolio.tsx:480-483` (Helper), `:535-540` (handleSave), `:622-650` (Grid)

- [ ] **Step 1: Update-Helper ergänzen**

In `Portfolio.tsx` nach Zeile 483 (`updateInvestment`) einfügen:

```ts
  function updateShares(i: number, raw: string) {
    const v = parseNum(raw)
    setPositions(p => p.map((r, j) => {
      if (j !== i) return r
      const shares = Number.isNaN(v) ? undefined : v
      const investment = shares != null && r.avg_buy != null
        ? parseFloat((shares * r.avg_buy).toFixed(2)) : r.investment
      return { ...r, shares, investment }
    }))
  }
  function updateAvgBuy(i: number, raw: string) {
    const v = parseNum(raw)
    setPositions(p => p.map((r, j) => {
      if (j !== i) return r
      const avg_buy = Number.isNaN(v) ? undefined : v
      const investment = avg_buy != null && r.shares != null
        ? parseFloat((avg_buy * r.shares).toFixed(2)) : r.investment
      return { ...r, avg_buy, investment }
    }))
  }
```

- [ ] **Step 2: handleSave Ticker normalisieren**

`handleSave` (Z.535-540) ersetzen durch:

```ts
  async function handleSave() {
    setSaving(true)
    const cleaned = positions
      .filter(p => p.ticker)
      .map(p => ({ ...p, ticker: normalizeTicker(p.ticker) }))
    try {
      await savePortfolio(cleaned)
      setPositions(prev => prev.map(p => p.ticker ? { ...p, ticker: normalizeTicker(p.ticker) } : p))
      showToast('Portfolio saved')
    }
    catch { showToast('Save failed') }
    finally { setSaving(false) }
  }
```

- [ ] **Step 3: Grid um zwei Spalten erweitern**

Die Grid-Definition (Z.622) ändern:

```tsx
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px 110px 130px 28px 28px', gap: '.5rem .5rem', minWidth: 480 }}>
```

Die Header-Zeile (Z.623-625) ersetzen durch:

```tsx
              <p style={labelStyle}>Ticker</p>
              <p style={labelStyle}>Stück</p>
              <p style={labelStyle}>Ø Kauf (€)</p>
              <p style={labelStyle}>Investment (€)</p>
              <span /><span />
```

Im `positions.map`-Block (Z.626-649) den `<TickerInput .../>` (Z.628) lassen und direkt davor/danach so umbauen, dass die Reihenfolge Ticker → Stück → Ø Kauf → Investment ist — d.h. die zwei neuen Inputs zwischen TickerInput und dem bestehenden Investment-Input einfügen:

```tsx
                  <TickerInput key={`t${i}`} value={p.ticker} onChange={v => updateTicker(i, v)} />
                  <input
                    key={`s${i}`}
                    type="text"
                    inputMode="decimal"
                    defaultValue={p.shares ?? ''}
                    onBlur={e => updateShares(i, e.target.value)}
                    placeholder="z.B. 2,91"
                    style={inputStyle}
                  />
                  <input
                    key={`a${i}`}
                    type="text"
                    inputMode="decimal"
                    defaultValue={p.avg_buy ?? ''}
                    onBlur={e => updateAvgBuy(i, e.target.value)}
                    placeholder="z.B. 162,66"
                    style={inputStyle}
                  />
                  <input
                    key={`v${i}`}
                    type="number"
                    value={p.investment || ''}
                    onChange={e => updateInvestment(i, parseFloat(e.target.value) || 0)}
                    placeholder="5000"
                    style={inputStyle}
                  />
```

(Stück/Ø-Kauf nutzen `defaultValue` + `onBlur`, damit der Smart-Parser erst bei Verlassen des Felds läuft und Tippen mit Komma/Punkt nicht stört. Investment bleibt `value`-gebunden, weil es aus Stück×Ø abgeleitet wird.)

- [ ] **Step 4: Build/Typecheck + Tests**

Run: `cd /Users/juliokoelle/projects/automation/frontend && npx tsc -b && npx vitest run`
Expected: tsc kein Fehler; vitest PASS (11 tests gesamt).

- [ ] **Step 5: Commit**

```bash
cd /Users/juliokoelle/projects/automation && git add frontend/src/pages/Portfolio.tsx && git commit -m "feat: manual shares + avg-buy editor fields with derived investment"
```

---

## Task 6: Allocation Throttle-Fix (Backend)

**Files:**
- Modify: `scripts/api.py:674-699` (`_alloc_meta`), `:711` (`max_workers`)

- [ ] **Step 1: `_alloc_meta` mit Retry+Backoff, nur Erfolg cachen**

`_alloc_meta` (Z.674-699) ersetzen durch:

```python
def _alloc_meta(ticker: str) -> dict:
    """Cached sector + country for a ticker (ETFs flagged as 'ETF'/'Global').

    Retries against Yahoo throttling; caches only successful fetches so a
    throttled failure does not poison the cache as 'Unknown'.
    """
    key = f"allocmeta:{ticker}"
    cached = _cache_get(key, _TTL_NAME)
    if cached is not None:
        return cached  # type: ignore[return-value]
    import time
    import yfinance as yf
    sector, country = "Unknown", "Unknown"
    fetched = False
    for attempt in range(3):
        try:
            info = yf.Ticker(ticker).info or {}
            quote_type = info.get("quoteType", "")
            is_etf = (
                quote_type in ("ETF", "MUTUALFUND")
                or bool(info.get("fundFamily"))
                or bool(info.get("categoryName"))
            )
            if is_etf:
                sector, country = "ETF", "Global"
            else:
                sector = info.get("sector") or "Unknown"
                country = info.get("country") or "Unknown"
            fetched = True
            break
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    meta = {"sector": sector, "country": country}
    if fetched:
        _cache_set(key, meta)
    return meta
```

- [ ] **Step 2: `max_workers` senken**

In `portfolio_allocation` (Z.711) ändern:

```python
    with ThreadPoolExecutor(max_workers=3) as ex:
```

- [ ] **Step 3: Backend lokal starten und Endpoint smoke-testen**

Backend starten (falls nicht läuft) und Allocation mit ~11 Holdings testen:

```bash
cd /Users/juliokoelle/projects/automation && (lsof -ti:8000 >/dev/null || (venv/bin/uvicorn scripts.api:app --port 8000 >/tmp/api.log 2>&1 &)) && sleep 5 && curl -s -X POST http://localhost:8000/portfolio/allocation -H 'Content-Type: application/json' -d '{"holdings":[{"ticker":"VWCE.DE","value":5000},{"ticker":"AVGO","value":3000},{"ticker":"DTE.DE","value":2000},{"ticker":"AAPL","value":2500},{"ticker":"MSFT","value":2200},{"ticker":"NVDA","value":1800},{"ticker":"ASML.AS","value":1500},{"ticker":"TSM","value":1200},{"ticker":"AMZN","value":1100},{"ticker":"GOOGL","value":900},{"ticker":"META","value":800}]}'
```

Expected: `bySector` und `byContinent` enthalten echte Labels (z.B. "Technology", "North America", "ETF"), NICHT 100% "Unknown"/"Other".

- [ ] **Step 4: Commit**

```bash
cd /Users/juliokoelle/projects/automation && git add scripts/api.py && git commit -m "fix: throttle-resistant allocation meta (retry+backoff, workers 8->3, cache only success)"
```

---

## Task 7: Build + Deploy

**Files:** keine neuen — Deploy von Frontend-`dist` + Backend-`scripts/api.py`.

- [ ] **Step 1: Komplette Test-Suite grün**

Run: `cd /Users/juliokoelle/projects/automation/frontend && npx vitest run && npx tsc -b`
Expected: alle Tests PASS, tsc kein Fehler.

- [ ] **Step 2: Frontend bauen + deployen (baut dist, committet, pusht)**

Run: `cd /Users/juliokoelle/projects/automation/frontend && npm run deploy`
Expected: `tsc -b && vite build` erfolgreich; `frontend/dist` committet + gepusht.

- [ ] **Step 3: Backend-Push sicherstellen**

`npm run deploy` committet nur `frontend/dist`. Backend-Commit (`scripts/api.py`, aus Task 6) und Lib/Plan-Commits mitpushen:

```bash
cd /Users/juliokoelle/projects/automation && git push
```

Expected: Render autoDeploy triggert für Backend + Frontend.

- [ ] **Step 4: Prod verifizieren (nach ~2-3 Min Render-Deploy)**

```bash
curl -s -X POST https://market-tools-backend-my0v.onrender.com/portfolio/allocation -H 'Content-Type: application/json' -d '{"holdings":[{"ticker":"VWCE.DE","value":5000},{"ticker":"AVGO","value":3000}]}'
```

Expected: echte Sector/Continent-Verteilung. Frontend-Seite `market-tools-frontend.onrender.com/market/portfolio` zeigt nach Reload realistische Euro-Beträge.

---

## Erfolgskriterien (aus Spec)

- [x] Live-P&L realistische Euro-Beträge → Task 2 (Parser) + Task 4 (Import nutzt Parser).
- [x] Stück/Ø-Kauf manuell editierbar + persistent → Task 5.
- [x] TELEKOM korrekt als DTE.DE → Task 3 + Task 5 (handleSave).
- [x] Allocation Sector/Continent/Market echte Verteilung → Task 6.
- [x] Smart-Parser per Unit-Test (deutsch + dezimal-Punkt) → Task 2.

## Verweise
- Spec: `docs/superpowers/specs/2026-06-16-portfolio-data-integrity-design.md`
- Memory: `project_market_tools_redesign.md`, `reference_add_app_to_market_tools.md`
- Deploy: `npm run deploy` baut nur dist; Backend braucht Push von `scripts/api.py` (Render autoDeploy on push to main).
