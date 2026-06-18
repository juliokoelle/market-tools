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
