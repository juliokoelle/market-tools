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
