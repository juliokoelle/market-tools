import { useEffect, useState } from 'react'
import { getHotStocks } from '../services/api'
import type { Tab, HotStockRow } from '../components/market/hot-stocks/hot-data'
import HotStockList from '../components/market/hot-stocks/HotStockList'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'gainers',   label: 'Top Gainers',       icon: '📈' },
  { id: 'losers',    label: 'Top Losers',         icon: '📉' },
  { id: 'bull_high', label: 'Highest Bull Score', icon: '🐂' },
  { id: 'bull_low',  label: 'Lowest Bull Score',  icon: '🐻' },
]

type TabData = Record<Tab, HotStockRow[]>
const EMPTY: TabData = { gainers: [], losers: [], bull_high: [], bull_low: [] }

let _cache: { data: TabData; ts: number } | null = null
const CACHE_TTL = 5 * 60 * 1000

export default function HotStocks() {
  const [data, setData] = useState<TabData>(() => (_cache ? _cache.data : EMPTY))
  const [tab, setTab] = useState<Tab>('gainers')
  const [loading, setLoading] = useState(!_cache)

  function load(force = false) {
    if (!force && _cache && Date.now() - _cache.ts < CACHE_TTL) return
    setLoading(true)
    getHotStocks()
      .then(d => { _cache = { data: d, ts: Date.now() }; setData(d) })
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
        <div className="card" style={{ padding: 0 }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} style={{ height: 58, borderBottom: i < 4 ? '1px solid var(--border)' : 'none', background: 'var(--surface-alt)', animation: `pulse 1.4s ease-in-out ${i * 120}ms infinite` }} />
          ))}
        </div>
      ) : (
        <div className="table-scroll">
          <HotStockList rows={rows} />
        </div>
      )}
    </main>
  )
}
