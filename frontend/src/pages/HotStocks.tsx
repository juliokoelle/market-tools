import { useEffect, useState } from 'react'
import { getHotStocks, type StockRow } from '../services/api'
import { LoadingOverlay } from '../components/LoadingOverlay'

type Tab = 'gainers' | 'losers' | 'bull_high' | 'bull_low'

const TABS: { id: Tab; label: string }[] = [
  { id: 'gainers',  label: 'Top Gainers' },
  { id: 'losers',   label: 'Top Losers' },
  { id: 'bull_high',label: 'Highest Bull Score' },
  { id: 'bull_low', label: 'Lowest Bull Score' },
]

export default function HotStocks() {
  const [data, setData] = useState<Record<Tab, StockRow[]>>({ gainers: [], losers: [], bull_high: [], bull_low: [] })
  const [tab, setTab]   = useState<Tab>('gainers')
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    getHotStocks()
      .then(d => setData(d as Record<Tab, StockRow[]>))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const PAGE_SIZE = 10
  const rows = data[tab] ?? []
  const page_rows = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const total_pages = Math.ceil(rows.length / PAGE_SIZE)

  function switchTab(t: Tab) { setTab(t); setPage(0) }

  return (
    <main className="page-enter section">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Hot Stocks</h1>
        <button onClick={load} className="btn btn-outline" style={{ fontSize: '.8rem' }} disabled={loading}>
          {loading ? 'Loading…' : '↺ Refresh'}
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '.35rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => switchTab(t.id)}
            className="btn btn-outline"
            style={{
              fontSize: '.8rem',
              background: tab === t.id ? 'var(--primary)' : undefined,
              color: tab === t.id ? '#fff' : undefined,
              borderColor: tab === t.id ? 'var(--primary)' : undefined,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="card table-scroll" style={{ padding: 0, position: 'relative' }}>
        <LoadingOverlay visible={loading} />
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.875rem', minWidth: 500 }}>
          <thead>
            <tr style={{ background: 'var(--surface-alt)', borderBottom: '1px solid var(--border)' }}>
              {['#', 'Ticker', 'Name', 'Price', 'Change', tab.startsWith('bull') ? 'Bull Score' : ''].filter(Boolean).map(h => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading
              ? <tr><td colSpan={6} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-faint)' }}>Loading…</td></tr>
              : page_rows.length === 0
                ? <tr><td colSpan={6} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-faint)' }}>No data</td></tr>
                : page_rows.map((s, i) => (
                  <tr key={s.ticker} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={tdStyle}><span style={{ color: 'var(--text-faint)', fontSize: '.8rem' }}>{page * PAGE_SIZE + i + 1}</span></td>
                    <td style={tdStyle}>
                      <a href={`https://finance.yahoo.com/quote/${s.ticker}`} target="_blank" rel="noopener noreferrer"
                        style={{ fontWeight: 700, color: 'var(--primary)' }}>{s.ticker}</a>
                    </td>
                    <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{s.name}</td>
                    <td style={tdStyle}>${s.price.toFixed(2)}</td>
                    <td style={tdStyle}>
                      <span style={{ color: s.change_pct >= 0 ? '#059669' : '#dc2626', fontWeight: 600 }}>
                        {s.change_pct >= 0 ? '+' : ''}{s.change_pct.toFixed(2)}%
                      </span>
                    </td>
                    {tab.startsWith('bull') && s.bull_score !== undefined && (
                      <td style={tdStyle}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
                          <div style={{ width: 60, height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ width: `${s.bull_score}%`, height: '100%', background: s.bull_score > 60 ? '#059669' : s.bull_score > 40 ? '#d97706' : '#dc2626', borderRadius: 3 }} />
                          </div>
                          <span style={{ fontSize: '.8rem', fontWeight: 600 }}>{s.bull_score}</span>
                        </div>
                      </td>
                    )}
                  </tr>
                ))
            }
          </tbody>
        </table>
      </div>

      {total_pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '.5rem', marginTop: '1rem' }}>
          <button className="btn btn-outline" style={{ fontSize: '.8rem' }} disabled={page === 0} onClick={() => setPage(p => p - 1)}>← Prev</button>
          <span style={{ padding: '.5rem .75rem', fontSize: '.875rem', color: 'var(--text-muted)' }}>{page + 1} / {total_pages}</span>
          <button className="btn btn-outline" style={{ fontSize: '.8rem' }} disabled={page === total_pages - 1} onClick={() => setPage(p => p + 1)}>Next →</button>
        </div>
      )}
    </main>
  )
}

const thStyle: React.CSSProperties = { padding: '.6rem 1rem', textAlign: 'left', fontSize: '.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.04em' }
const tdStyle: React.CSSProperties = { padding: '.6rem 1rem' }
