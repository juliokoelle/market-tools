import { useEffect, useState } from 'react'
import { getHotStocks, type StockRow } from '../services/api'

type Tab = 'gainers' | 'losers' | 'bull_high' | 'bull_low'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'gainers',   label: 'Top Gainers',       icon: '📈' },
  { id: 'losers',    label: 'Top Losers',         icon: '📉' },
  { id: 'bull_high', label: 'Highest Bull Score', icon: '🐂' },
  { id: 'bull_low',  label: 'Lowest Bull Score',  icon: '🐻' },
]

let _cache: { data: Record<Tab, StockRow[]>; ts: number } | null = null
const CACHE_TTL = 5 * 60 * 1000

export default function HotStocks() {
  const [data, setData] = useState<Record<Tab, StockRow[]>>(
    () => _cache ? _cache.data : { gainers: [], losers: [], bull_high: [], bull_low: [] }
  )
  const [tab, setTab]     = useState<Tab>('gainers')
  const [loading, setLoading] = useState(!_cache)

  function load(force = false) {
    if (!force && _cache && Date.now() - _cache.ts < CACHE_TTL) return
    setLoading(true)
    getHotStocks()
      .then(d => {
        const typed = d as Record<Tab, StockRow[]>
        _cache = { data: typed, ts: Date.now() }
        setData(typed)
      })
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '1rem' }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card" style={{ height: 110, opacity: .4, background: 'var(--surface-alt)' }} />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p style={{ color: 'var(--text-3)', fontSize: '.875rem', padding: '2rem 0' }}>No data available.</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '1rem' }}>
          {rows.map((s, i) => (
            <a key={s.ticker} href={`https://finance.yahoo.com/quote/${s.ticker}`} target="_blank" rel="noopener noreferrer"
              className="card"
              style={{ display: 'flex', flexDirection: 'column', gap: '.5rem', padding: '1rem', textDecoration: 'none', transition: 'box-shadow .15s, transform .15s' }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 24px -4px rgba(0,0,0,.12)'; (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = ''; (e.currentTarget as HTMLElement).style.transform = '' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '.68rem', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.04em' }}>#{i + 1}</span>
                <span style={{ color: s.change_pct >= 0 ? '#059669' : '#dc2626', fontWeight: 700, fontSize: '.85rem' }}>
                  {s.change_pct >= 0 ? '+' : ''}{s.change_pct.toFixed(2)}%
                </span>
              </div>
              <div>
                <p style={{ fontWeight: 700, fontSize: '.9rem', color: 'var(--teal)' }}>{s.ticker}</p>
                {s.name !== s.ticker && (
                  <p style={{ fontSize: '.78rem', color: 'var(--text-3)', marginTop: '.1rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</p>
                )}
              </div>
              <p style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text)' }}>${s.price.toFixed(2)}</p>
              {tab.startsWith('bull') && s.bull_score !== undefined && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem', marginTop: '.25rem' }}>
                  <div style={{ flex: 1, height: 5, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${s.bull_score}%`, height: '100%', borderRadius: 3,
                      background: s.bull_score > 60 ? '#059669' : s.bull_score > 40 ? '#d97706' : '#dc2626' }} />
                  </div>
                  <span style={{ fontSize: '.75rem', fontWeight: 600, minWidth: 24 }}>{s.bull_score}</span>
                </div>
              )}
            </a>
          ))}
        </div>
      )}
    </main>
  )
}
