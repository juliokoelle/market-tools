// Reine Helfer für den Stock-Analyzer. Keine Backend-/React-Kopplung.
import { fmtNumber } from './format'
import type { PeerRow, FinancialsRow } from '../services/api'

/** Position des Kurses in der 52W-Spanne als 0–100. Degeneriert -> 0. */
export function range52Position(low: number, high: number, price: number): number {
  if (!(high > low)) return 0
  const pct = ((price - low) / (high - low)) * 100
  return Math.max(0, Math.min(100, Math.round(pct)))
}

/** Relatives Volumen als Faktor-Label (deutsches Komma, ×-Suffix). */
export function fmtRelVolume(rel: number | null | undefined): string {
  if (rel === null || rel === undefined) return '—'
  return `${fmtNumber(rel, 1)}×`
}

/** income_stmt-Rows -> recharts-BarChart-Daten in Mio. EUR. */
export function financialsToBars(rows: FinancialsRow[]) {
  return rows.map(r => ({
    year: String(r.year),
    Revenue: Math.round((r.revenue ?? 0) / 1e6),
    EBITDA: Math.round((r.ebitda ?? 0) / 1e6),
    'Net Income': Math.round((r.net_income ?? 0) / 1e6),
  }))
}

/** Peers absteigend nach bull_score (Kopie, keine Mutation). */
export function sortPeers(peers: PeerRow[]): PeerRow[] {
  return [...peers].sort((a, b) => b.bull_score - a.bull_score)
}
