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
