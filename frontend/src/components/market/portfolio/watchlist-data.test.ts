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
