import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMarketPrices, getBriefingPreview } from '../services/api'
import { LoadingOverlay } from '../components/LoadingOverlay'

const MARKET_TICKERS = '^GSPC,GC=F,EURUSD=X,CL=F,^VIX'
const TICKER_META: Record<string, { label: string; unit: string; prefix: string }> = {
  '^GSPC':   { label: 'S&P 500',  unit: 'pts',    prefix: '' },
  'GC=F':    { label: 'Gold',     unit: 'USD/oz', prefix: '$' },
  'EURUSD=X':{ label: 'EUR/USD',  unit: '',       prefix: '' },
  'CL=F':    { label: 'Brent',    unit: 'USD/bbl',prefix: '$' },
  '^VIX':    { label: 'VIX',      unit: '',       prefix: '' },
}

function formatPrice(ticker: string, price: number) {
  const m = TICKER_META[ticker]
  if (!m) return price.toFixed(2)
  if (ticker === 'EURUSD=X') return price.toFixed(4)
  if (ticker === '^GSPC') return m.prefix + price.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  return m.prefix + price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function ChangePill({ v }: { v: number }) {
  const pos = v >= 0
  return (
    <span className={`badge ${pos ? 'badge-teal' : 'badge-red'}`} style={pos ? {} : { background: '#fee2e2', color: '#991b1b' }}>
      {pos ? '▲' : '▼'} {Math.abs(v).toFixed(2)}%
    </span>
  )
}

function MarketStatCard({ ticker, data }: { ticker: string; data?: { price: number; change_pct: number } }) {
  const meta = TICKER_META[ticker]
  return (
    <div className="card card-sm">
      <p className="stat-label">{meta?.label ?? ticker}</p>
      {data ? (
        <>
          <p className="stat-num" style={{ fontSize: '1.6rem', marginTop: '.4rem' }}>
            {formatPrice(ticker, data.price)}
          </p>
          <div style={{ marginTop: '.6rem' }}>
            <ChangePill v={data.change_pct} />
          </div>
          {meta?.unit && (
            <p style={{ fontSize: '.65rem', color: 'var(--text-3)', marginTop: '.35rem' }}>{meta.unit}</p>
          )}
        </>
      ) : (
        <div style={{ height: 52, marginTop: '.4rem', background: 'var(--border-soft)', borderRadius: 8, animation: 'pulse 1.4s infinite' }} />
      )}
    </div>
  )
}

const QUICK_LINKS = [
  { to: '/market/portfolio',  label: 'Portfolio',      desc: 'Analyze your holdings'      },
  { to: '/market/hot-stocks', label: 'Hot Stocks',     desc: 'Top movers & gainers'       },
  { to: '/market/analyzer',   label: 'Stock Analyzer', desc: 'Watchlist & bull scores'    },
  { to: '/market/briefing',   label: 'Full Briefing',  desc: "Today's economic analysis"  },
]

export default function Dashboard() {
  const [prices, setPrices] = useState<Record<string, { price: number; change_pct: number }>>({})
  const [preview, setPreview] = useState<{ preview: string; date: string } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getMarketPrices(MARKET_TICKERS).then(setPrices).catch(() => {}),
      getBriefingPreview().then(setPreview).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  const tickers = MARKET_TICKERS.split(',')
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })

  return (
    <main className="page page-enter">
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">{today}</p>
        </div>
      </div>

      {/* Market snapshot */}
      <div style={{ position: 'relative', marginBottom: '1.5rem', borderRadius: 'var(--radius)' }}>
        <LoadingOverlay visible={loading} />
        <div className="grid-5">
          {tickers.map(t => (
            <MarketStatCard key={t} ticker={t} data={prices[t]} />
          ))}
        </div>
      </div>

      {/* Briefing + Quick links */}
      <div className="grid-main-sidebar" style={{ marginBottom: '1.5rem' }}>
        {/* Briefing preview */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div>
              <p className="stat-label">Today's Briefing</p>
              {preview && <p style={{ fontSize: '.75rem', color: 'var(--text-3)', marginTop: '.2rem' }}>{preview.date}</p>}
            </div>
            <Link to="/market/briefing" className="btn btn-outline">Read full →</Link>
          </div>
          <div className="stat-divider" />
          {preview ? (
            <p style={{ fontSize: '.875rem', color: 'var(--text-2)', lineHeight: 1.75, whiteSpace: 'pre-line', marginTop: '1rem' }}>
              {preview.preview}
            </p>
          ) : (
            <p style={{ fontSize: '.85rem', color: 'var(--text-3)', marginTop: '1rem' }}>
              {loading ? 'Loading briefing…' : 'No briefing available today.'}
            </p>
          )}
        </div>

        {/* Quick links */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
          {QUICK_LINKS.map(l => (
            <Link key={l.to} to={l.to} style={{ display: 'block' }}>
              <div
                className="card card-sm"
                style={{
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '.9rem',
                  transition: 'box-shadow .15s, border-color .15s',
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--teal-muted)'
                  ;(e.currentTarget as HTMLDivElement).style.boxShadow = 'var(--shadow)'
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = ''
                  ;(e.currentTarget as HTMLDivElement).style.boxShadow = ''
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--teal)', flexShrink: 0 }} />
                <div>
                  <p style={{ fontSize: '.875rem', fontWeight: 600, color: 'var(--text)' }}>{l.label}</p>
                  <p style={{ fontSize: '.75rem', color: 'var(--text-3)', marginTop: '.1rem' }}>{l.desc}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </main>
  )
}
