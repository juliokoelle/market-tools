// Pure data layer for the Market-Dashboard: top-positions + top-movers ranking.
// No React, no fetch — unit-testable. P&L itself comes from computePnl (not duplicated here).
import type { PnlStats } from '../portfolio-panels'
import type { WatchlistCategory, StockDetail } from '../../../services/api'

/** Snapshot row: a position reduced to ticker, EUR value and portfolio weight (%). */
export interface SnapshotRow {
  ticker: string
  value: number
  weight: number
}

/**
 * Top-N positions by EUR value (desc). Weight is the share of total portfolio value
 * in percent; 0 when the portfolio has no value yet.
 */
export function topPositions(stats: PnlStats, n = 5): SnapshotRow[] {
  const total = stats.totalValue
  return [...stats.items]
    .sort((a, b) => b.value - a.value)
    .slice(0, n)
    .map(it => ({
      ticker: it.ticker,
      value: it.value,
      weight: total > 0 ? (it.value / total) * 100 : 0,
    }))
}

/**
 * Top-N watchlist movers by absolute daily change (desc). Flattens all categories;
 * a ticker appearing in two categories is deduped (first occurrence wins).
 */
export function topMovers(cats: WatchlistCategory[], n = 5): StockDetail[] {
  const seen = new Set<string>()
  const flat: StockDetail[] = []
  for (const cat of cats) {
    for (const s of cat.stocks) {
      if (seen.has(s.ticker)) continue
      seen.add(s.ticker)
      flat.push(s)
    }
  }
  return flat
    .sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct))
    .slice(0, n)
}
