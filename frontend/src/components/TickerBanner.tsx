import { useEffect, useState } from 'react'
import { getMarketPrices } from '../services/api'

const TICKERS = '^GSPC,GC=F,EURUSD=X,CL=F,^VIX'
const LABELS: Record<string, string> = {
  '^GSPC': 'S&P 500', 'GC=F': 'Gold', 'EURUSD=X': 'EUR/USD', 'CL=F': 'Brent', '^VIX': 'VIX',
}

function yahooUrl(ticker: string) {
  return `https://finance.yahoo.com/quote/${encodeURIComponent(ticker)}`
}

function fmt(ticker: string, price: number) {
  if (ticker === 'EURUSD=X') return price.toFixed(4)
  if (ticker === '^GSPC') return price.toLocaleString('en-US', { maximumFractionDigits: 0 })
  return price.toFixed(2)
}

function TickerItem({ ticker, prices }: { ticker: string; prices: Record<string, { price: number; change_pct: number }> }) {
  const d = prices[ticker]
  const label = LABELS[ticker]

  return (
    <a
      href={yahooUrl(ticker)}
      target="_blank"
      rel="noopener noreferrer"
      style={{ display: 'inline-flex', gap: '.35rem', alignItems: 'center', textDecoration: 'none', cursor: 'pointer' }}
    >
      <span style={{ color: '#aaa' }}>{label}</span>
      {d ? (
        <>
          <span style={{ color: '#fff', fontWeight: 700 }}>{fmt(ticker, d.price)}</span>
          <span style={{ color: d.change_pct >= 0 ? '#4ade80' : '#f87171' }}>
            {d.change_pct >= 0 ? '▲' : '▼'} {Math.abs(d.change_pct).toFixed(2)}%
          </span>
        </>
      ) : (
        <span style={{ color: '#555' }}>···</span>
      )}
    </a>
  )
}

const SEP = <span style={{ color: '#444', margin: '0 .8rem' }}>|</span>

export default function TickerBanner() {
  const [prices, setPrices] = useState<Record<string, { price: number; change_pct: number }>>({})
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    getMarketPrices(TICKERS).then(setPrices).catch(() => {})
    const id = setInterval(() => getMarketPrices(TICKERS).then(setPrices).catch(() => {}), 60_000)
    return () => clearInterval(id)
  }, [])

  const tickers = TICKERS.split(',')

  function renderSet(prefix: string) {
    return tickers.map((t, i) => (
      <span key={`${prefix}-${t}`} style={{ display: 'inline-flex', alignItems: 'center' }}>
        {i > 0 && SEP}
        <TickerItem ticker={t} prices={prices} />
      </span>
    ))
  }

  return (
    <div
      className="ticker-banner"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div
        className="ticker-track ticker-animate"
        style={{ animationPlayState: paused ? 'paused' : 'running' }}
      >
        {renderSet('a')}
        {SEP}
        {renderSet('b')}
        {SEP}
      </div>
    </div>
  )
}
