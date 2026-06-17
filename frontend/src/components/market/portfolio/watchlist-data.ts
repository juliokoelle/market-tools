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
