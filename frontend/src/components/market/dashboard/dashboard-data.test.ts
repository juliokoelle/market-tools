import { describe, it, expect } from 'vitest'
import { topPositions, topMovers } from './dashboard-data'
import type { PnlStats, PnlItem } from '../portfolio-panels'
import type { WatchlistCategory, StockDetail } from '../../../services/api'

const item = (over: Partial<PnlItem>): PnlItem => ({
  ticker: 'X', hasQty: false, investment: 0, cost: 0, value: 0,
  pnl: 0, pnlPct: 0, day: 0, ...over,
})

const statsOf = (items: PnlItem[]): PnlStats => {
  const totalValue = items.reduce((s, i) => s + i.value, 0)
  return { items, totalCost: 0, totalValue, totalPnl: 0, totalPnlPct: 0, dayPnl: 0, dayPnlPct: 0, anyPnl: false }
}

const stock = (over: Partial<StockDetail>): StockDetail => ({
  ticker: 'X', name: 'X', price: 0, change_pct: 0, bull_score: 50,
  sector: '', market_cap: 0, pe_ratio: null, week_52_high: 0, week_52_low: 0,
  components: { momentum: 50, sentiment: 50, valuation: 50, analyst: 50 }, ...over,
})

describe('topPositions', () => {
  it('sorts by value desc, slices to n, and computes weights', () => {
    const stats = statsOf([
      item({ ticker: 'A', value: 200 }),
      item({ ticker: 'B', value: 600 }),
      item({ ticker: 'C', value: 200 }),
    ])
    const top = topPositions(stats, 2)
    expect(top.map(r => r.ticker)).toEqual(['B', 'A'])
    expect(top[0].weight).toBeCloseTo(60)
    expect(top[1].weight).toBeCloseTo(20)
  })

  it('defaults to top-5 and degrades weight to 0 when total value is 0', () => {
    const stats = statsOf([item({ ticker: 'A', value: 0 }), item({ ticker: 'B', value: 0 })])
    const top = topPositions(stats)
    expect(top.length).toBe(2)
    expect(top[0].weight).toBe(0)
  })
})

describe('topMovers', () => {
  it('flattens categories and ranks by absolute change desc', () => {
    const cats: WatchlistCategory[] = [
      { category: 'Tech', stocks: [stock({ ticker: 'AAPL', change_pct: 1.5 }), stock({ ticker: 'NVDA', change_pct: -4.2 })] },
      { category: 'Picks', stocks: [stock({ ticker: 'SAP', change_pct: 0.3 })] },
    ]
    expect(topMovers(cats).map(s => s.ticker)).toEqual(['NVDA', 'AAPL', 'SAP'])
  })

  it('dedups a ticker across categories (keeps first) and slices to n', () => {
    const cats: WatchlistCategory[] = [
      { category: 'A', stocks: [stock({ ticker: 'AAPL', change_pct: 2 })] },
      { category: 'B', stocks: [stock({ ticker: 'AAPL', change_pct: -9 }), stock({ ticker: 'MSFT', change_pct: 1 })] },
    ]
    const top = topMovers(cats, 5)
    expect(top.map(s => s.ticker)).toEqual(['AAPL', 'MSFT'])
    expect(top[0].change_pct).toBe(2)
  })
})
