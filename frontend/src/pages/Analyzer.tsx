import { useEffect, useState } from 'react'
import { getWatchlist, getStockDetail, getStockAiSummary, type WatchlistCategory, type StockDetail } from '../services/api'

const BASE = import.meta.env.VITE_API_URL ?? '/api'

function BullRing({ score }: { score: number }) {
  const color = score > 60 ? '#059669' : score > 40 ? '#d97706' : '#dc2626'
  const r = 18, circ = 2 * Math.PI * r
  const dash = (score / 100) * circ
  return (
    <svg width="48" height="48" viewBox="0 0 48 48">
      <circle cx="24" cy="24" r={r} fill="none" stroke="var(--border)" strokeWidth="4" />
      <circle cx="24" cy="24" r={r} fill="none" stroke={color} strokeWidth="4"
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
        transform="rotate(-90 24 24)" />
      <text x="24" y="28" textAnchor="middle" fontSize="11" fontWeight="700" fill={color}>{score}</text>
    </svg>
  )
}

function StockModal({ ticker, onClose }: { ticker: string; onClose: () => void }) {
  const [detail, setDetail] = useState<StockDetail | null>(null)
  const [summary, setSummary] = useState<string>('')
  const [period, setPeriod] = useState('3mo')

  useEffect(() => {
    getStockDetail(ticker).then(setDetail).catch(() => {})
    getStockAiSummary(ticker).then(d => setSummary(d.summary)).catch(() => {})
  }, [ticker])

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }} onClick={onClose}>
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', width: '100%', maxWidth: 600, maxHeight: '85vh', overflow: 'auto', padding: '1.5rem' }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>{ticker}</h2>
            {detail && <p style={{ fontSize: '.85rem', color: 'var(--text-muted)' }}>{detail.name} · {detail.sector}</p>}
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.5rem', color: 'var(--text-muted)', cursor: 'pointer' }}>×</button>
        </div>

        {detail && (
          <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
            {[
              { label: 'Price', value: `$${detail.price.toFixed(2)}` },
              { label: 'Bull Score', value: detail.bull_score },
              { label: '52W High', value: `$${detail.week_52_high?.toFixed(2) ?? '—'}` },
              { label: '52W Low',  value: `$${detail.week_52_low?.toFixed(2) ?? '—'}` },
              { label: 'P/E', value: detail.pe_ratio?.toFixed(1) ?? '—' },
              { label: 'Market Cap', value: detail.market_cap ? `$${(detail.market_cap / 1e9).toFixed(1)}B` : '—' },
            ].map(m => (
              <div key={m.label} style={{ padding: '.6rem', background: 'var(--surface-alt)', borderRadius: 6 }}>
                <p style={{ fontSize: '.7rem', color: 'var(--text-muted)', marginBottom: '.15rem' }}>{m.label}</p>
                <p style={{ fontWeight: 700, fontSize: '.95rem' }}>{m.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Chart period selector */}
        <div style={{ marginBottom: '1rem' }}>
          <div style={{ display: 'flex', gap: '.35rem', marginBottom: '.75rem' }}>
            {['1mo', '3mo', '6mo', '1y'].map(p => (
              <button key={p} onClick={() => setPeriod(p)} className="btn btn-outline"
                style={{ fontSize: '.75rem', padding: '.3rem .6rem', background: period === p ? 'var(--primary)' : undefined, color: period === p ? '#fff' : undefined }}>
                {p}
              </button>
            ))}
          </div>
          <a href={`${BASE}/stock/${ticker}/chart?period=${period}`} target="_blank" rel="noopener noreferrer"
            style={{ fontSize: '.75rem', color: 'var(--primary)' }}>↗ Raw chart data</a>
        </div>

        {summary && (
          <div style={{ padding: '1rem', background: 'var(--surface-alt)', borderRadius: 8, borderLeft: '3px solid var(--primary)' }}>
            <p style={{ fontSize: '.75rem', fontWeight: 600, color: 'var(--primary)', marginBottom: '.5rem', textTransform: 'uppercase', letterSpacing: '.05em' }}>AI Analysis</p>
            <p style={{ fontSize: '.875rem', lineHeight: 1.7, color: 'var(--text)' }}>{summary}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Analyzer() {
  const [categories, setCategories] = useState<WatchlistCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    getWatchlist()
      .then(setCategories)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <main className="page-enter section">
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1.5rem' }}>Stock Analyzer</h1>

      {loading && <p style={{ color: 'var(--text-faint)', fontSize: '.875rem' }}>Loading watchlist…</p>}

      {categories.map(cat => (
        <div key={cat.category} style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontWeight: 700, marginBottom: '1rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.06em', fontSize: '.8rem' }}>
            {cat.category}
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
            {cat.stocks.map(s => (
              <div
                key={s.ticker}
                className="card"
                style={{ cursor: 'pointer', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '.5rem', transition: 'box-shadow .15s' }}
                onClick={() => setSelected(s.ticker)}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <p style={{ fontWeight: 700, fontSize: '.95rem' }}>{s.ticker}</p>
                    <p style={{ fontSize: '.75rem', color: 'var(--text-muted)', maxWidth: 100, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.name}</p>
                  </div>
                  <BullRing score={s.bull_score} />
                </div>
                <p style={{ fontSize: '.95rem', fontWeight: 600 }}>${s.price.toFixed(2)}</p>
                <span style={{ color: s.change_pct >= 0 ? '#059669' : '#dc2626', fontSize: '.8rem', fontWeight: 600 }}>
                  {s.change_pct >= 0 ? '+' : ''}{s.change_pct.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}

      {selected && <StockModal ticker={selected} onClose={() => setSelected(null)} />}
    </main>
  )
}
