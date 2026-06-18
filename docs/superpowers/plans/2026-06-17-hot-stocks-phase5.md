# Hot Stocks Phase 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Hot-Stocks-Seite von Karten zu reichen Ranking-Listen aufwerten, gespeist aus einer angereicherten `/market/hot-stocks`-Response (echter `bull_score`, EUR-Preis, Market Cap, Rel Vol, Sektor), mit lazy „Why moving".

**Architecture:** Backend stellt `market_hot_stocks()` auf das bewährte `/watchlist`-Muster um (`_score_one_ticker` + `_fetch_meta` + `_eur_rate`) und ergänzt Market Cap (EUR) + Rel Vol + Sektor. Frontend bekommt eine pure, getestete Datenschicht (`hot-data.ts`), eine presentational Liste (`HotStockList.tsx`) und eine schlanke Page (`HotStocks.tsx`).

**Tech Stack:** FastAPI/yfinance (Backend), React + TypeScript + Vite + Vitest (Frontend), bestehende `primitives.tsx`/`score.tsx`/`format.ts`.

**Spec:** `docs/superpowers/specs/2026-06-17-hot-stocks-phase5-design.md`

---

### Task 1: Pure Datenschicht `hot-data.ts` + Tests (TDD)

**Files:**
- Create: `frontend/src/components/market/hot-stocks/hot-data.ts`
- Test: `frontend/src/components/market/hot-stocks/hot-data.test.ts`

- [ ] **Step 1: Write the failing test**

`frontend/src/components/market/hot-stocks/hot-data.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { mapHotStock, rankTabs, type RawHotStock, type HotStockRow } from './hot-data'

const raw = (over: Partial<RawHotStock>): RawHotStock => ({
  ticker: 'X', name: 'X Corp', sector: 'Tech', price: 100, change_pct: 1,
  spark: [1, 2, 3], bull_score: 60, market_cap: 1_000_000, rel_volume: 1.2,
  components: { momentum: { score: 70 }, sentiment: { score: 55 }, valuation: { score: 40 }, analyst: { score: 50 } },
  ...over,
})

const row = (over: Partial<HotStockRow>): HotStockRow => ({
  ticker: 'X', name: 'X', sector: null, price: 0, changePct: 0, spark: [],
  bull: 50, momentum: 50, valuation: 50, marketCap: null, relVol: null, ...over,
})

describe('mapHotStock', () => {
  it('maps a full raw stock', () => {
    const r = mapHotStock(raw({ ticker: 'NVDA', name: 'NVIDIA' }))
    expect(r.ticker).toBe('NVDA')
    expect(r.name).toBe('NVIDIA')
    expect(r.sector).toBe('Tech')
    expect(r.price).toBe(100)
    expect(r.changePct).toBe(1)
    expect(r.spark).toEqual([1, 2, 3])
    expect(r.bull).toBe(60)
    expect(r.momentum).toBe(70)
    expect(r.valuation).toBe(40)
    expect(r.marketCap).toBe(1_000_000)
    expect(r.relVol).toBe(1.2)
  })

  it('degrades missing fields to null and name to ticker', () => {
    const r = mapHotStock({ ticker: 'TSLA' })
    expect(r.name).toBe('TSLA')
    expect(r.sector).toBeNull()
    expect(r.price).toBeNull()
    expect(r.changePct).toBeNull()
    expect(r.spark).toEqual([])
    expect(r.bull).toBeNull()
    expect(r.momentum).toBeNull()
    expect(r.valuation).toBeNull()
    expect(r.marketCap).toBeNull()
    expect(r.relVol).toBeNull()
  })
})

describe('rankTabs', () => {
  const rows = [
    row({ ticker: 'A', changePct: 5, bull: 30 }),
    row({ ticker: 'B', changePct: -4, bull: 90 }),
    row({ ticker: 'C', changePct: 2, bull: 60 }),
  ]
  it('ranks gainers/losers by changePct', () => {
    const t = rankTabs(rows)
    expect(t.gainers.map(r => r.ticker)).toEqual(['A', 'C', 'B'])
    expect(t.losers[0].ticker).toBe('B')
  })
  it('ranks bull tabs by bull score', () => {
    const t = rankTabs(rows)
    expect(t.bull_high[0].ticker).toBe('B')
    expect(t.bull_low[0].ticker).toBe('A')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/market/hot-stocks/hot-data.test.ts`
Expected: FAIL — cannot resolve `./hot-data`.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/market/hot-stocks/hot-data.ts`:

```ts
// Pure data layer for the Hot Stocks page: shape mapping + tab ranking.
// No React, no fetch — unit-testable.

export type Tab = 'gainers' | 'losers' | 'bull_high' | 'bull_low'

/** Raw stock as returned by GET /market/hot-stocks (post-enrichment). */
export interface RawHotStock {
  ticker: string
  name?: string
  sector?: string | null
  price?: number | null
  change_pct?: number | null
  spark?: number[]
  bull_score?: number | null
  market_cap?: number | null
  rel_volume?: number | null
  components?: {
    momentum?: { score?: number }
    sentiment?: { score?: number }
    valuation?: { score?: number }
    analyst?: { score?: number }
  }
}

/** Presentational row — nulls degrade to “—”/“···” in the UI. */
export interface HotStockRow {
  ticker: string
  name: string
  sector: string | null
  price: number | null
  changePct: number | null
  spark: number[]
  bull: number | null
  momentum: number | null
  valuation: number | null
  marketCap: number | null
  relVol: number | null
}

const num = (v: unknown): number | null =>
  typeof v === 'number' && Number.isFinite(v) ? v : null

export function mapHotStock(raw: RawHotStock): HotStockRow {
  const c = raw.components ?? {}
  return {
    ticker: raw.ticker,
    name: raw.name && raw.name !== '' ? raw.name : raw.ticker,
    sector: raw.sector ?? null,
    price: num(raw.price),
    changePct: num(raw.change_pct),
    spark: Array.isArray(raw.spark) ? raw.spark : [],
    bull: num(raw.bull_score),
    momentum: num(c.momentum?.score),
    valuation: num(c.valuation?.score),
    marketCap: num(raw.market_cap),
    relVol: num(raw.rel_volume),
  }
}

export function rankTabs(rows: HotStockRow[]): Record<Tab, HotStockRow[]> {
  const byChange = [...rows].sort((a, b) => (b.changePct ?? -Infinity) - (a.changePct ?? -Infinity))
  const byBull = [...rows].sort((a, b) => (b.bull ?? -Infinity) - (a.bull ?? -Infinity))
  return {
    gainers:   byChange.slice(0, 5),
    losers:    byChange.slice(-5).reverse(),
    bull_high: byBull.slice(0, 5),
    bull_low:  byBull.slice(-5).reverse(),
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/market/hot-stocks/hot-data.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/market/hot-stocks/hot-data.ts frontend/src/components/market/hot-stocks/hot-data.test.ts
git commit -m "feat(hot-stocks): pure map/rank data layer + tests (Phase 5)"
```

---

### Task 2: Backend — `/market/hot-stocks` anreichern

**Files:**
- Modify: `scripts/api.py:1093-1146` (`market_hot_stocks` + `_enrich`)

- [ ] **Step 1: Replace the endpoint body**

Ersetze den gesamten Block von `@app.get("/market/hot-stocks")` bis zum `return result` (Z. 1093–1146) durch:

```python
@app.get("/market/hot-stocks")
def market_hot_stocks():
    cached = _cache_get("hot_stocks_enriched", _TTL_HOT_ENRICHED)
    if cached is not None:
        return cached

    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor

    stocks = get_hot_stocks(top_n=30)
    if not stocks:
        raise HTTPException(status_code=503, detail="Could not fetch market data. Try again shortly.")

    def _enrich(s: dict) -> dict:
        ticker = s["ticker"]
        try:
            score = _score_one_ticker(ticker)            # bull_score + components (5-min cache)
            meta  = _fetch_meta(ticker)                  # name + currency (30-min cache)
            cur   = meta.get("currency")
            rate, _ = _eur_rate(cur)
            md    = (score.get("components", {}).get("momentum", {}) or {}).get("details", {}) or {}
            price = md.get("price")
            price_eur = round(float(price) * rate, 2) if (price is not None and cur) else None

            market_cap = None
            rel_volume = None
            try:
                fast = yf.Ticker(ticker).fast_info
                mc = getattr(fast, "market_cap", None)
                market_cap = round(float(mc) * rate) if (mc and cur) else None
                last_vol = getattr(fast, "last_volume", None)
                avg_vol = s.get("volume_avg")
                if last_vol and avg_vol:
                    rel_volume = round(float(last_vol) / float(avg_vol), 2)
            except Exception:
                pass

            return {
                **score,
                "name":        meta.get("name", ticker),
                "sector":      _ticker_sector(ticker),
                "price":       price_eur,
                "change_pct":  md.get("change_pct"),
                "spark":       md.get("spark", []),
                "market_cap":  market_cap,
                "rel_volume":  rel_volume,
                "currency":    "EUR",
            }
        except Exception:
            return {
                "ticker": ticker, "name": ticker, "sector": None,
                "price": None, "change_pct": round(s.get("return", 0) * 100, 2),
                "spark": [], "bull_score": 50, "components": {},
                "market_cap": None, "rel_volume": None, "currency": "EUR",
            }

    with ThreadPoolExecutor(max_workers=10) as ex:
        enriched = list(ex.map(_enrich, stocks))

    enriched.sort(key=lambda x: x.get("change_pct") or 0, reverse=True)
    result = {"stocks": enriched, "total": len(enriched)}
    _cache_set("hot_stocks_enriched", result)
    return result
```

- [ ] **Step 2: Validate syntax**

Run: `cd /Users/juliokoelle/projects/automation && python -m py_compile scripts/api.py && echo OK`
Expected: `OK` (no SyntaxError).

- [ ] **Step 3: Commit**

```bash
git add scripts/api.py
git commit -m "feat(hot-stocks): enrich /market/hot-stocks with real bull_score, EUR price, market cap, rel vol, sector (Phase 5)"
```

---

### Task 3: `api.ts` — `getHotStocks` auf reiche Rows umstellen

**Files:**
- Modify: `frontend/src/services/api.ts:26-45` (`getHotStocks`)

- [ ] **Step 1: Check for other consumers of the old return shape**

Run: `cd frontend && grep -rn "getHotStocks" src/`
Expected: nur `services/api.ts` (Definition) und `pages/HotStocks.tsx` (Consumer, wird in Task 5 angepasst). Falls weitere Consumer → dort Tab-Zugriff prüfen.

- [ ] **Step 2: Replace getHotStocks**

Ersetze die `getHotStocks`-Definition (Z. 26–45) durch:

```ts
export const getHotStocks = () =>
  get<{ stocks?: RawHotStock[] }>('/market/hot-stocks').then(d =>
    rankTabs((d.stocks ?? []).filter(s => s.price != null).map(mapHotStock))
  )
```

- [ ] **Step 3: Add the import at the top of `api.ts`** (zu den bestehenden Imports):

```ts
import { mapHotStock, rankTabs, type RawHotStock } from '../components/market/hot-stocks/hot-data'
```

- [ ] **Step 4: Verify types compile**

Run: `cd frontend && npx tsc -b`
Expected: exit 0 (HotStocks.tsx kann hier noch `StockRow`-Bezug zeigen — Task 5 räumt das; falls tsc bricht, erst Task 5 ziehen und gemeinsam prüfen).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(hot-stocks): getHotStocks returns rich ranked rows (Phase 5)"
```

---

### Task 4: `HotStockList.tsx` — presentational Ranking-Liste

**Files:**
- Create: `frontend/src/components/market/hot-stocks/HotStockList.tsx`

- [ ] **Step 1: Create the component**

`frontend/src/components/market/hot-stocks/HotStockList.tsx`:

```tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getStockAiSummary } from '../../../services/api'
import { Sparkline, Delta } from '../primitives'
import { ScoreBadge } from '../score'
import { fmtCurrency, fmtMarketCap, fmtNumber } from '../../../lib/format'
import type { HotStockRow } from './hot-data'

const DASH = '—'
const AVATAR_TONES = ['var(--brand)', 'var(--gain)', 'var(--warn)', 'var(--loss)', 'var(--text-2)']

function avatarTone(ticker: string): string {
  let h = 0
  for (let i = 0; i < ticker.length; i++) h = (h * 31 + ticker.charCodeAt(i)) >>> 0
  return AVATAR_TONES[h % AVATAR_TONES.length]
}

export default function HotStockList({ rows }: { rows: HotStockRow[] }) {
  const [why, setWhy] = useState<Record<string, string>>({})
  const [whyLoading, setWhyLoading] = useState<string | null>(null)

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

  if (!rows.length) {
    return <p style={{ color: 'var(--text-3)', fontSize: '.875rem', padding: '2rem 0' }}>No data available.</p>
  }

  return (
    <div className="card" style={{ padding: 0, minWidth: 720 }}>
      {rows.map((r, i) => {
        const tone = avatarTone(r.ticker)
        return (
          <div key={r.ticker}
            style={{ display: 'flex', alignItems: 'center', gap: '1rem',
              padding: '.85rem 1.1rem', borderBottom: i < rows.length - 1 ? '1px solid var(--border)' : 'none' }}>
            <span className="tabular" style={{ fontSize: '.8rem', fontWeight: 700, color: 'var(--text-3)', minWidth: 22 }}>#{i + 1}</span>
            <div style={{ display: 'grid', placeItems: 'center', width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
              background: `color-mix(in srgb, ${tone} 16%, transparent)`, color: tone, fontSize: '.72rem', fontWeight: 800 }}>
              {r.ticker.slice(0, 2)}
            </div>
            <div style={{ flex: '1 1 150px', minWidth: 110 }}>
              <Link to={`/market/analyzer/${encodeURIComponent(r.ticker)}`}
                style={{ color: 'var(--text)', textDecoration: 'none', fontWeight: 700, fontSize: '.9rem' }}>{r.ticker}</Link>
              <p style={{ fontSize: '.72rem', color: 'var(--text-3)', marginTop: '.1rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 170 }}>
                {r.sector ?? (r.name !== r.ticker ? r.name : DASH)}
              </p>
            </div>
            <div style={{ flexShrink: 0 }}>
              {r.spark.length ? <Sparkline values={r.spark} width={72} height={24} /> : <span style={{ color: 'var(--text-3)' }}>{DASH}</span>}
            </div>
            <div style={{ minWidth: 92, textAlign: 'right' }}>
              <p className="tabular" style={{ fontSize: '.9rem', fontWeight: 700, color: 'var(--text)' }}>
                {r.price != null ? fmtCurrency(r.price) : '···'}
              </p>
              {r.changePct != null
                ? <Delta value={r.changePct} style={{ justifyContent: 'flex-end' }} />
                : <span style={{ color: 'var(--text-3)', fontSize: '.8rem' }}>···</span>}
            </div>
            <div style={{ minWidth: 86, textAlign: 'right' }}>
              <p className="tabular" style={{ fontSize: '.78rem', color: 'var(--text-2)' }}>
                {r.marketCap != null ? fmtMarketCap(r.marketCap, 'EUR') : DASH}
              </p>
              <p className="tabular" style={{ fontSize: '.72rem', color: 'var(--text-3)', marginTop: '.1rem' }}>
                {r.relVol != null ? `${fmtNumber(r.relVol, 2)}× Vol` : DASH}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '.3rem', flexShrink: 0 }}>
              {r.bull != null && <ScoreBadge score={r.bull} label="B" />}
              {r.momentum != null && <ScoreBadge score={r.momentum} label="M" />}
              {r.valuation != null && <ScoreBadge score={r.valuation} label="V" />}
            </div>
            <div style={{ flex: '1 1 180px', minWidth: 150, maxWidth: 280 }}>
              {why[r.ticker] ? (
                <span style={{ fontSize: '.75rem', color: 'var(--text-2)' }}>{why[r.ticker]}</span>
              ) : (
                <button onClick={() => loadWhy(r.ticker)} className="btn btn-outline" style={{ fontSize: '.72rem', padding: '.25rem .55rem' }}>
                  {whyLoading === r.ticker ? '…' : 'Why ↗'}
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/market/hot-stocks/HotStockList.tsx
git commit -m "feat(hot-stocks): HotStockList ranking row with lazy why-moving (Phase 5)"
```

---

### Task 5: `HotStocks.tsx` — Page auf Listen umstellen

**Files:**
- Modify (full rewrite): `frontend/src/pages/HotStocks.tsx`

- [ ] **Step 1: Replace the whole file**

`frontend/src/pages/HotStocks.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { getHotStocks } from '../services/api'
import type { Tab, HotStockRow } from '../components/market/hot-stocks/hot-data'
import HotStockList from '../components/market/hot-stocks/HotStockList'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'gainers',   label: 'Top Gainers',       icon: '📈' },
  { id: 'losers',    label: 'Top Losers',         icon: '📉' },
  { id: 'bull_high', label: 'Highest Bull Score', icon: '🐂' },
  { id: 'bull_low',  label: 'Lowest Bull Score',  icon: '🐻' },
]

type TabData = Record<Tab, HotStockRow[]>
const EMPTY: TabData = { gainers: [], losers: [], bull_high: [], bull_low: [] }

let _cache: { data: TabData; ts: number } | null = null
const CACHE_TTL = 5 * 60 * 1000

export default function HotStocks() {
  const [data, setData] = useState<TabData>(() => (_cache ? _cache.data : EMPTY))
  const [tab, setTab] = useState<Tab>('gainers')
  const [loading, setLoading] = useState(!_cache)

  function load(force = false) {
    if (!force && _cache && Date.now() - _cache.ts < CACHE_TTL) return
    setLoading(true)
    getHotStocks()
      .then(d => { _cache = { data: d, ts: Date.now() }; setData(d) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const rows = data[tab] ?? []

  return (
    <main className="page-enter section">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Hot Stocks</h1>
        <button onClick={() => load(true)} className="btn btn-outline" style={{ fontSize: '.8rem' }} disabled={loading}>
          {loading ? 'Loading…' : '↺ Refresh'}
        </button>
      </div>

      <div style={{ display: 'flex', gap: '.35rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} className="btn btn-outline"
            style={{ fontSize: '.8rem', background: tab === t.id ? 'var(--teal)' : undefined, color: tab === t.id ? '#fff' : undefined, borderColor: tab === t.id ? 'var(--teal)' : undefined }}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="card" style={{ padding: 0 }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} style={{ height: 58, borderBottom: i < 4 ? '1px solid var(--border)' : 'none', background: 'var(--surface-alt)', animation: `pulse 1.4s ease-in-out ${i * 120}ms infinite` }} />
          ))}
        </div>
      ) : (
        <div className="table-scroll">
          <HotStockList rows={rows} />
        </div>
      )}
    </main>
  )
}
```

- [ ] **Step 2: Verify the full gate (tests + types)**

Run: `cd frontend && npx vitest run && npx tsc -b`
Expected: Vitest all green (inkl. neuer hot-data-Tests), `tsc -b` exit 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/HotStocks.tsx
git commit -m "feat(hot-stocks): rank-list page using HotStockList, drop card grid (Phase 5)"
```

---

### Task 6: Deploy + Prod-Smoke

**Files:** keine (Build + Push).

- [ ] **Step 1: Build + deploy frontend**

Run: `cd frontend && npm run deploy`
Expected: tsc-check + Vite-Build grün, dist committed+gepusht (Vercel/Render autoDeploy).

- [ ] **Step 2: Push backend**

Run: `cd /Users/juliokoelle/projects/automation && git push`
Expected: `scripts/api.py`-Commit auf `main` → Render autoDeploy.

- [ ] **Step 3: Prod-Smoke (manuell)**

Nach Render-Build: `market-tools-frontend.onrender.com/market/hot-stocks` öffnen. Prüfen:
- 4 Tabs schalten; Gainers/Losers nach Tagesveränderung, Bull-Tabs nach echtem Score (nicht alle 50).
- Pro Zeile: Rang, Avatar, Symbol+Sektor, Sparkline, EUR-Preis+Day, Market Cap (EUR), Rel Vol (oft „—"), B/M/V-Badges.
- „Why ↗" lädt on click eine Zusammenfassung.
- Mobile: Liste horizontal scrollbar (`.table-scroll`), kein Layout-Bruch.

- [ ] **Step 4: Obsidian-Doku** (nach Abnahme) in `30_Projects/market-tools/` — Ziel/Vorgehen/Annahmen/Lessons/Ergebnisse/offene Punkte/Status (CLAUDE.md-Protokoll).

---

## Notes
- `_score_one_ticker`, `_fetch_meta`, `_eur_rate`, `_ticker_sector` existieren bereits in `scripts/api.py` — keine neuen Helfer.
- Kosten: ≤30 Haiku-Calls/5-Min-Cache-Fenster (Sentiment in `bull_score`), bewusst akzeptiert (Spec).
- Out of scope: Zeitfenster-Switch (bis Backend `period`-Param), Dashboard-Radar (Phase 6), Komma-Bug Portfolio-Editor.
