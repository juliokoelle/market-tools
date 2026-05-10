import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMarketPrices, getBriefingPreview } from '../services/api'

const MARKET_TICKERS = '^GSPC,GC=F,EURUSD=X,CL=F,^VIX'
const TICKER_LABELS: Record<string, string> = {
  '^GSPC': 'S&P 500', 'GC=F': 'Gold', 'EURUSD=X': 'EUR/USD',
  'CL=F': 'Brent Oil', '^VIX': 'VIX',
}

function PctBadge({ v }: { v: number }) {
  const pos = v >= 0
  return (
    <span className={`badge ${pos ? 'badge-green' : 'badge-red'}`}>
      {pos ? '+' : ''}{v.toFixed(2)}%
    </span>
  )
}

function MarketCard({ ticker, price, change_pct }: { ticker: string; price: number; change_pct: number }) {
  const label = TICKER_LABELS[ticker] ?? ticker
  const isIdx = ticker.startsWith('^') && ticker !== '^VIX'
  const isFx  = ticker.includes('USD')
  const fmt = isIdx
    ? price.toLocaleString('en-US', { minimumFractionDigits: 2 })
    : isFx
      ? price.toFixed(4)
      : `$${price.toLocaleString('en-US', { minimumFractionDigits: 2 })}`

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '.4rem' }}>
      <p style={{ fontSize: '.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.04em' }}>{label}</p>
      <p style={{ fontSize: '1.4rem', fontWeight: 700, letterSpacing: '-.5px' }}>{fmt}</p>
      <PctBadge v={change_pct} />
    </div>
  )
}

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

  return (
    <main className="page-enter section">
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Dashboard</h1>
        <p style={{ fontSize: '.8rem', color: 'var(--text-faint)' }}>
          {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* Market Snapshot */}
      <div className="grid-4" style={{ marginBottom: '1.75rem' }}>
        {tickers.map(t => prices[t]
          ? <MarketCard key={t} ticker={t} price={prices[t].price} change_pct={prices[t].change_pct} />
          : <div key={t} className="card" style={{ minHeight: 96, background: loading ? '#f9fafb' : 'var(--surface)' }} />
        )}
      </div>

      {/* Briefing Preview */}
      <div className="card" style={{ marginBottom: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1rem', fontWeight: 700 }}>Today's Briefing</h2>
            {preview && <p style={{ fontSize: '.75rem', color: 'var(--text-faint)', marginTop: '.15rem' }}>{preview.date}</p>}
          </div>
          <Link to="/market/briefing" className="btn btn-outline" style={{ fontSize: '.8rem' }}>
            Read full →
          </Link>
        </div>
        {preview
          ? <p style={{ fontSize: '.9rem', color: 'var(--text-muted)', lineHeight: 1.7, whiteSpace: 'pre-line' }}>
              {preview.preview}
            </p>
          : <p style={{ fontSize: '.875rem', color: 'var(--text-faint)' }}>
              {loading ? 'Loading briefing…' : 'No briefing available today.'}
            </p>
        }
      </div>

      {/* Quick Links */}
      <div className="grid-3">
        {[
          { to: '/market/portfolio', label: 'Portfolio', icon: '💼', desc: 'Analyze your holdings' },
          { to: '/market/hot-stocks', label: 'Hot Stocks', icon: '🔥', desc: 'Top movers today' },
          { to: '/market/analyzer', label: 'Stock Analyzer', icon: '📊', desc: 'Watchlist + bull scores' },
        ].map(l => (
          <Link key={l.to} to={l.to} style={{ display: 'contents' }}>
            <div className="card" style={{ cursor: 'pointer', transition: 'box-shadow .15s' }}>
              <p style={{ fontSize: '1.5rem', marginBottom: '.4rem' }}>{l.icon}</p>
              <p style={{ fontWeight: 600, marginBottom: '.2rem' }}>{l.label}</p>
              <p style={{ fontSize: '.8rem', color: 'var(--text-muted)' }}>{l.desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </main>
  )
}
