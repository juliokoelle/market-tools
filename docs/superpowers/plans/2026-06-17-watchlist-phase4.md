# Watchlist Phase 4 — Rich Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den persönlichen Watchlist-Tab in `Portfolio.tsx` durch eine reiche Tabellen-Ansicht (11 Spalten, EUR, Sparkline/Bull/Momentum/Market-Cap/Rel-Vol/Why-moving/Analyze) ersetzen — additiv, ohne Backend-Change.

**Architecture:** Reine Daten-Helfer (`watchlist-data.ts`, TDD-getestet) + eine Präsentations-/Lade-Komponente (`WatchlistPanel.tsx`). `Portfolio.tsx` behält die Membership-Liste (`/stock-watchlist`) + Add/Remove und rendert nur noch `<WatchlistPanel/>`. Daten: 1× `getWatchlist()` (schnell, gecacht) für Price/Day/Spark/Bull/Momentum, per-Ticker `getStockDetail()` (Hintergrund, concurrency-limitiert) für Market Cap + Rel Vol, `getStockAiSummary()` lazy on-demand für „Why moving".

**Tech Stack:** React + TypeScript, Vite, vitest, recharts/lucide bereits vorhanden. Wiederverwendung: `components/market/primitives.tsx` (`Sparkline`, `Delta`), `components/market/score.tsx` (`ScoreBadge`), `lib/format.ts` (`fmtCurrency`/`fmtMarketCap`/`fmtNumber`).

**Spec:** `docs/superpowers/specs/2026-06-17-watchlist-phase4-design.md`

---

## File Structure

- **Create:** `frontend/src/components/market/portfolio/watchlist-data.ts` — reine Helfer (Typen + Map-Bau + Row-Merge). Keine React-Imports.
- **Create:** `frontend/src/components/market/portfolio/watchlist-data.test.ts` — vitest-Unit-Tests.
- **Create:** `frontend/src/components/market/portfolio/WatchlistPanel.tsx` — Input + reiche Tabelle + Datenladen.
- **Modify:** `frontend/src/pages/Portfolio.tsx` — Watchlist-Tab-Block (~Z. 713–822) durch `<WatchlistPanel/>` ersetzen; altes `/market/prices`+`/market/names`-Laden für die Watchlist entfernen.

Bestätigte Fakten aus dem Code (nicht raten):
- `getWatchlist()` (api.ts:115) liefert `WatchlistCategory[]` = `{ category, stocks: StockDetail[] }`. Jede `stocks`-Zeile hat `ticker, name, price` (EUR), `change_pct, bull_score, spark, components.momentum`.
- `getStockDetail(ticker)` (api.ts:141) liefert `StockDetail` mit `market_cap` (EUR-konvertiert, Backend `/stock/detail` macht `_eur(market_cap)`, `currency:"EUR"`), `rel_volume` (oft `null`).
- `getStockAiSummary(ticker)` (api.ts:171) → `Promise<{ summary: string }>`.
- `getStockWatchlist/addStockToWatchlist/removeStockFromWatchlist` (api.ts:186-194) — Membership.
- `Sparkline({ values })`, `Delta({ value })`, `ScoreBadge({ score, label? })`.
- `fmtCurrency(n)`, `fmtMarketCap(n, 'EUR')`, `fmtNumber(n, max)`.

---

## Task 1: Pure data helpers (`watchlist-data.ts`)

**Files:**
- Create: `frontend/src/components/market/portfolio/watchlist-data.ts`
- Test: `frontend/src/components/market/portfolio/watchlist-data.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/components/market/portfolio/watchlist-data.test.ts
import { describe, it, expect } from 'vitest'
import { buildEnrichmentMap, mergeRow } from './watchlist-data'
import type { WatchlistCategory, StockDetail } from '../../../services/api'

const stock = (over: Partial<StockDetail>): StockDetail => ({
  ticker: 'X', name: 'X', price: 0, change_pct: 0, bull_score: 50,
  sector: '', market_cap: 0, pe_ratio: null, week_52_high: 0, week_52_low: 0,
  components: { momentum: 50, sentiment: 50, valuation: 50, analyst: 50 }, ...over,
})

describe('buildEnrichmentMap', () => {
  it('flattens categories into one ticker→entry map', () => {
    const cats: WatchlistCategory[] = [
      { category: 'Tech', stocks: [stock({ ticker: 'AAPL', name: 'Apple', price: 180 })] },
      { category: 'Meine Picks', stocks: [stock({ ticker: 'SAP', name: 'SAP SE', price: 200 })] },
    ]
    const map = buildEnrichmentMap(cats)
    expect(map.get('AAPL')?.name).toBe('Apple')
    expect(map.get('SAP')?.price).toBe(200)
  })

  it('dedups a ticker that appears in two categories (keeps first)', () => {
    const cats: WatchlistCategory[] = [
      { category: 'Tech', stocks: [stock({ ticker: 'AAPL', name: 'Apple', price: 180 })] },
      { category: 'Meine Picks', stocks: [stock({ ticker: 'AAPL', name: 'Apple Inc', price: 999 })] },
    ]
    const map = buildEnrichmentMap(cats)
    expect(map.size).toBe(1)
    expect(map.get('AAPL')?.price).toBe(180)
  })
})

describe('mergeRow', () => {
  it('uses enrichment for fast fields and null detail leaves marketCap/relVol null', () => {
    const enrich = stock({ ticker: 'AAPL', name: 'Apple', price: 180, change_pct: 1.2, bull_score: 72, spark: [1, 2, 3], components: { momentum: 80, sentiment: 50, valuation: 50, analyst: 50 } })
    const row = mergeRow('AAPL', enrich, undefined)
    expect(row.ticker).toBe('AAPL')
    expect(row.name).toBe('Apple')
    expect(row.price).toBe(180)
    expect(row.changePct).toBe(1.2)
    expect(row.bull).toBe(72)
    expect(row.momentum).toBe(80)
    expect(row.spark).toEqual([1, 2, 3])
    expect(row.marketCap).toBeNull()
    expect(row.relVol).toBeNull()
  })

  it('merges detail marketCap/relVol when present', () => {
    const enrich = stock({ ticker: 'AAPL', name: 'Apple' })
    const detail = stock({ ticker: 'AAPL', market_cap: 2_800_000_000_000, rel_volume: 1.4 })
    const row = mergeRow('AAPL', enrich, detail)
    expect(row.marketCap).toBe(2_800_000_000_000)
    expect(row.relVol).toBe(1.4)
  })

  it('falls back to ticker as name when nothing is loaded yet', () => {
    const row = mergeRow('TSLA', undefined, undefined)
    expect(row.name).toBe('TSLA')
    expect(row.price).toBeNull()
    expect(row.bull).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/market/portfolio/watchlist-data.test.ts`
Expected: FAIL — `Failed to resolve import './watchlist-data'`.

- [ ] **Step 3: Write minimal implementation**

```ts
// frontend/src/components/market/portfolio/watchlist-data.ts
import type { WatchlistCategory, StockDetail } from '../../../services/api'

/** Schnell-Felder aus /watchlist (eine Zeile je Ticker). */
export type EnrichedRow = StockDetail

/** Eine Watchlist-Tabellenzeile. `null` = noch nicht geladen / nicht verfügbar (→ UI „—"/„···"). */
export interface WatchRow {
  ticker: string
  name: string
  price: number | null
  changePct: number | null
  spark: number[]
  bull: number | null
  momentum: number | null
  marketCap: number | null
  relVol: number | null
}

/** Flacht alle Kategorien zu einer ticker→Zeile-Map. Erster Treffer gewinnt (dedup). */
export function buildEnrichmentMap(categories: WatchlistCategory[]): Map<string, EnrichedRow> {
  const map = new Map<string, EnrichedRow>()
  for (const cat of categories) {
    for (const s of cat.stocks) {
      if (!map.has(s.ticker)) map.set(s.ticker, s)
    }
  }
  return map
}

/** Kombiniert Schnell-Quelle (/watchlist) + Detail-Quelle (/stock/detail) zu einer Zeile. */
export function mergeRow(ticker: string, enrich?: EnrichedRow, detail?: StockDetail): WatchRow {
  return {
    ticker,
    name: enrich?.name ?? detail?.name ?? ticker,
    price: enrich?.price ?? detail?.price ?? null,
    changePct: enrich?.change_pct ?? detail?.change_pct ?? null,
    spark: enrich?.spark ?? [],
    bull: enrich?.bull_score ?? detail?.bull_score ?? null,
    momentum: enrich?.components?.momentum ?? detail?.components?.momentum ?? null,
    marketCap: detail?.market_cap ?? null,
    relVol: detail?.rel_volume ?? null,
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/market/portfolio/watchlist-data.test.ts`
Expected: PASS (2 describe blocks, 5 tests).

> Hinweis: `??` behandelt `0` als gültigen Wert — ein echter Preis 0 würde nicht zu detail durchfallen; das ist gewollt (0 ist ein geladener Wert, kein „fehlt").

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/market/portfolio/watchlist-data.ts frontend/src/components/market/portfolio/watchlist-data.test.ts
git commit -m "feat(watchlist): pure enrichment/merge helpers + tests (Phase 4)"
```

---

## Task 2: `WatchlistPanel.tsx` component

**Files:**
- Create: `frontend/src/components/market/portfolio/WatchlistPanel.tsx`

Keine DOM-Tests (Repo hat kein React-Testing-Setup; Verifikation über `tsc` + Prod-Smoke). Code vollständig unten.

- [ ] **Step 1: Write the component**

```tsx
// frontend/src/components/market/portfolio/WatchlistPanel.tsx
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Star } from 'lucide-react'
import { getWatchlist, getStockDetail, getStockAiSummary, type StockDetail } from '../../../services/api'
import { Sparkline, Delta } from '../primitives'
import { ScoreBadge } from '../score'
import { fmtCurrency, fmtMarketCap, fmtNumber } from '../../../lib/format'
import { buildEnrichmentMap, mergeRow, type EnrichedRow, type WatchRow } from './watchlist-data'

const DASH = '—'

interface Props {
  tickers: string[]
  portfolioTickers: Set<string>
  loading: boolean
  universe: string[]
  inputStyle: React.CSSProperties
  onAdd: (ticker: string) => void
  onRemove: (ticker: string) => void
  onTransfer: (t: { ticker: string; price: number }) => void
}

const TH = ['', 'Stock', 'Trend', 'Price', 'Day', 'Market Cap', 'Rel Vol', 'Bull', 'Mom', 'Why', '']

export default function WatchlistPanel({
  tickers, portfolioTickers, loading, universe, inputStyle, onAdd, onRemove, onTransfer,
}: Props) {
  const [enrich, setEnrich] = useState<Map<string, EnrichedRow>>(new Map())
  const [details, setDetails] = useState<Record<string, StockDetail>>({})
  const [why, setWhy] = useState<Record<string, string>>({})
  const [whyLoading, setWhyLoading] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLDivElement>(null)

  // Schnell-Quelle: /watchlist (gecacht, deckt 6 Spalten)
  useEffect(() => {
    if (!tickers.length) { setEnrich(new Map()); return }
    getWatchlist().then(cats => setEnrich(buildEnrichmentMap(cats))).catch(() => {})
  }, [tickers])

  // Hintergrund: per-Ticker Detail (Market Cap + Rel Vol), max 4 parallel
  useEffect(() => {
    if (!tickers.length) return
    let cancelled = false
    const queue = tickers.filter(t => !details[t])
    let i = 0
    const worker = async () => {
      while (!cancelled && i < queue.length) {
        const t = queue[i++]
        try {
          const d = await getStockDetail(t)
          if (!cancelled) setDetails(prev => ({ ...prev, [t]: d }))
        } catch { /* degrade to — */ }
      }
    }
    Promise.all(Array.from({ length: 4 }, worker))
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tickers])

  async function loadWhy(ticker: string) {
    if (why[ticker] || whyLoading) return
    setWhyLoading(ticker)
    try {
      const r = await getStockAiSummary(ticker)
      setWhy(prev => ({ ...prev, [ticker]: r.summary || 'Keine Zusammenfassung.' }))
    } catch {
      setWhy(prev => ({ ...prev, [ticker]: 'Konnte nicht geladen werden.' }))
    } finally {
      setWhyLoading(null)
    }
  }

  const rows: WatchRow[] = tickers.map(t => mergeRow(t, enrich.get(t), details[t]))
  const matches = input.length >= 1 ? universe.filter(t => t.startsWith(input) && !tickers.includes(t)).slice(0, 6) : []

  const cell: React.CSSProperties = { padding: '.7rem .9rem', fontSize: '.85rem', verticalAlign: 'middle' }
  const th: React.CSSProperties = { padding: '.6rem .9rem', textAlign: 'left', fontSize: '.62rem', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.06em' }

  return (
    <div>
      {/* Add ticker */}
      <div className="card" style={{ marginBottom: '1rem', padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', gap: '.75rem', alignItems: 'center' }}>
          <div ref={inputRef} style={{ position: 'relative', flex: 1 }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value.toUpperCase().replace(/\s/g, ''))}
              onKeyDown={e => { if (e.key === 'Enter' && input) { onAdd(input); setInput('') } }}
              placeholder="Search ticker (e.g. AAPL)"
              autoComplete="off" spellCheck={false} style={inputStyle}
            />
            {matches.length > 0 && (
              <ul className="dropdown-list" style={{
                position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
                background: 'var(--surface)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)', boxShadow: 'var(--shadow)',
                listStyle: 'none', margin: 0, padding: '.25rem 0',
              }}>
                {matches.map(s => (
                  <li key={s} onMouseDown={e => { e.preventDefault(); onAdd(s); setInput('') }}
                    style={{ padding: '.4rem .75rem', fontSize: '.875rem', cursor: 'pointer', color: 'var(--text)' }}>{s}</li>
                ))}
              </ul>
            )}
          </div>
          <button onClick={() => { if (input) { onAdd(input); setInput('') } }} className="btn btn-outline" style={{ fontSize: '.8rem', flexShrink: 0 }}>+ Add</button>
        </div>
      </div>

      {/* Rich table */}
      <div className="card table-scroll" style={{ padding: 0 }}>
        {loading ? (
          <p style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-3)', fontSize: '.875rem' }}>Loading…</p>
        ) : tickers.length === 0 ? (
          <p style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-3)', fontSize: '.875rem' }}>
            Your watchlist is empty. Search for a ticker above to add.
          </p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 900 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {TH.map((h, i) => <th key={i} style={th}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const inPf = portfolioTickers.has(r.ticker)
                return (
                  <tr key={r.ticker} style={{ borderBottom: i < rows.length - 1 ? '1px solid var(--border)' : 'none' }}>
                    <td style={cell}>
                      <button onClick={() => onRemove(r.ticker)} title="Remove from watchlist"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, lineHeight: 0 }}>
                        <Star size={15} fill="var(--brand)" color="var(--brand)" />
                      </button>
                    </td>
                    <td style={{ ...cell, fontWeight: 600 }}>
                      <Link to={`/market/analyzer/${encodeURIComponent(r.ticker)}`} style={{ color: 'inherit', textDecoration: 'none' }}>
                        {r.name !== r.ticker ? `${r.name} — ${r.ticker}` : r.ticker}
                      </Link>
                    </td>
                    <td style={cell}>{r.spark.length ? <Sparkline values={r.spark} width={72} height={22} /> : <span style={{ color: 'var(--text-3)' }}>{DASH}</span>}</td>
                    <td style={{ ...cell, color: 'var(--text-2)' }} className="tabular">{r.price != null ? fmtCurrency(r.price) : '···'}</td>
                    <td style={cell}>{r.changePct != null ? <Delta value={r.changePct} /> : <span style={{ color: 'var(--text-3)' }}>···</span>}</td>
                    <td style={{ ...cell, color: 'var(--text-2)' }} className="tabular">{r.marketCap != null ? fmtMarketCap(r.marketCap, 'EUR') : DASH}</td>
                    <td style={{ ...cell, color: 'var(--text-2)' }} className="tabular">{r.relVol != null ? `${fmtNumber(r.relVol, 2)}×` : DASH}</td>
                    <td style={cell}>{r.bull != null ? <ScoreBadge score={r.bull} /> : <span style={{ color: 'var(--text-3)' }}>···</span>}</td>
                    <td style={cell}>{r.momentum != null ? <ScoreBadge score={r.momentum} /> : <span style={{ color: 'var(--text-3)' }}>···</span>}</td>
                    <td style={{ ...cell, maxWidth: 220 }}>
                      {why[r.ticker] ? (
                        <span style={{ fontSize: '.78rem', color: 'var(--text-2)' }}>{why[r.ticker]}</span>
                      ) : (
                        <button onClick={() => loadWhy(r.ticker)} className="btn btn-outline" style={{ fontSize: '.72rem', padding: '.25rem .55rem' }}>
                          {whyLoading === r.ticker ? '…' : 'Why ↗'}
                        </button>
                      )}
                    </td>
                    <td style={cell}>
                      <div style={{ display: 'flex', gap: '.5rem', justifyContent: 'flex-end', alignItems: 'center' }}>
                        {inPf ? (
                          <span className="badge badge-teal" style={{ fontSize: '.65rem' }}>In Portfolio</span>
                        ) : (
                          <button onClick={() => onTransfer({ ticker: r.ticker, price: r.price ?? 0 })} className="btn btn-outline" style={{ fontSize: '.72rem', padding: '.25rem .55rem' }}>→ Portfolio</button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc -b`
Expected: PASS (keine Fehler). Falls `Star` nicht in `lucide-react` exportiert ist → durch `Bookmark` ersetzen.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/market/portfolio/WatchlistPanel.tsx
git commit -m "feat(watchlist): rich WatchlistPanel table component (Phase 4)"
```

---

## Task 3: Wire `WatchlistPanel` into `Portfolio.tsx`

**Files:**
- Modify: `frontend/src/pages/Portfolio.tsx`

- [ ] **Step 1: Add import** (oben bei den Komponenten-Imports)

```tsx
import WatchlistPanel from '../components/market/portfolio/WatchlistPanel'
```

- [ ] **Step 2: Replace the watchlist tab block**

Ersetze den gesamten Block `{tab === 'watchlist' && ( … )}` (ca. Z. 713–822, vom Kommentar `{/* ── Watchlist tab ── */}` bis zum schließenden `)}` vor `{detailTicker && …}`) durch:

```tsx
      {/* ── Watchlist tab ── */}
      {tab === 'watchlist' && (
        <WatchlistPanel
          tickers={watchlist}
          portfolioTickers={portfolioTickers}
          loading={watchLoading}
          universe={UNIVERSE}
          inputStyle={inputStyle}
          onAdd={addToWatchlist}
          onRemove={removeFromWatchlist}
          onTransfer={setTransferTicker}
        />
      )}
```

> Prüfe vor dem Ersetzen die echten Variablennamen im File: `watchlist`, `watchLoading`, `portfolioTickers`, `UNIVERSE`, `inputStyle`, `addToWatchlist`, `removeFromWatchlist`, `setTransferTicker`. Falls `setTransferTicker` eine andere Signatur erwartet, passe `onTransfer` entsprechend an (es bekommt `{ ticker, price }`).

- [ ] **Step 3: Remove now-dead watchlist data loading**

Entferne die nur noch für die alte Tabelle genutzten State/Effects in `Portfolio.tsx`:
- `watchPrices` / `setWatchPrices` State + der `getMarketPrices(watchlist…)`-Effect (~Z. 438–444).
- `watchNames` / `setWatchNames` State + der `getMarketNames(watchlist)`-Effect (~Z. 433–436).
- Den alten lokalen `watchInput` / `watchInputRef` State **nur falls** er nirgends sonst (außer der alten Tabelle) verwendet wird — der Input lebt jetzt im Panel.

Behalte: `watchlist`, `watchLoading`, `addToWatchlist`, `removeFromWatchlist`, das `getStockWatchlist()`-Mount-Laden (Z. ~425–429), den Tab-Badge-Count (`watchlist.length`).

> Wenn `getMarketPrices`/`getMarketNames` danach nirgends mehr genutzt werden, entferne sie aus dem `api`-Import, um TS6133 (unused) zu vermeiden.

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc -b`
Expected: PASS. Häufige Fehler: ungenutzte Imports (entfernen), `inputStyle` nicht definiert (es existiert bereits im File — sonst die lokale Konstante mitnehmen).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Portfolio.tsx
git commit -m "feat(watchlist): render WatchlistPanel in Portfolio tab, drop legacy table (Phase 4)"
```

---

## Task 4: Verify + Deploy

**Files:** keine Code-Änderung.

- [ ] **Step 1: Full test + type gate**

Run: `cd frontend && npx vitest run && npx tsc -b`
Expected: alle Tests grün, tsc ohne Fehler.

- [ ] **Step 2: Lokaler Smoke (optional, falls Dev-Server läuft)**

`npm run dev` → `/market/portfolio` → Tab „Watchlist": Tabelle zeigt Symbol/Name + Sparkline + Price (€) + Day sofort; Market Cap füllt nach; Rel Vol meist „—"; „Why ↗" lädt auf Klick; Star entfernt; „→ Portfolio" wechselt. Mobile: horizontal scrollbar (`.table-scroll`).

- [ ] **Step 3: Deploy Frontend**

Run: `npm run deploy`
(baut `dist` + commit/push; Backend unverändert — kein `git push` von `scripts/` nötig.)

- [ ] **Step 4: Prod-Smoke**

Öffne die Prod-URL `/market/portfolio` → Watchlist-Tab. Erwartung: reiche Spalten, EUR-Werte, fehlende Felder „—"/„···", keine gemockten Zahlen, keine Konsolen-Fehler.

---

## Self-Review (Plan ↔ Spec)

- **Spalten 1–11** (Spec-Tabelle) → alle in Task 2 gerendert: Star, Symbol+Name(Link=Analyze), Sparkline, Price, Day, Market Cap, Rel Vol, Bull, Momentum, Why (lazy), → Portfolio/Analyze.
- **Datenfluss** (Spec §Datenfluss) → Task 2 Effects: `getWatchlist` schnell, `getStockDetail` Hintergrund (max 4), `getStockAiSummary` lazy. ✓
- **Kein Backend-Change** → keine Task berührt `scripts/`. ✓
- **EUR/Degradation** → `fmtCurrency`/`fmtMarketCap(...,'EUR')`, `null`→`—`/`···`. ✓
- **Tab in Portfolio bleiben** → Task 3 ersetzt nur den Tab-Inhalt. ✓
- **Tests** → Task 1 deckt `buildEnrichmentMap` (flatten/dedup) + `mergeRow` (merge/degrade). ✓
- **Market-Cap-Währung** (Spec-Edge-Case) → im Code geklärt: Backend liefert EUR-konvertiert (`currency:"EUR"`), daher `fmtMarketCap(n,'EUR')`. ✓
