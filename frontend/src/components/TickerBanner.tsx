import { useEffect, useState } from 'react'
import { getMarketPrices } from '../services/api'

const TICKERS = '^GSPC,GC=F,EURUSD=X,CL=F,^VIX'
const LABELS: Record<string, string> = {
  '^GSPC': 'S&P 500', 'GC=F': 'Gold', 'EURUSD=X': 'EUR/USD', 'CL=F': 'Brent', '^VIX': 'VIX',
}
const UNITS: Record<string, string> = {
  '^GSPC': 'pts', 'GC=F': 'USD/oz', 'EURUSD=X': '', 'CL=F': 'USD/bbl', '^VIX': '',
}

function fmt(ticker: string, price: number) {
  if (ticker === 'EURUSD=X') return price.toFixed(4)
  if (ticker === '^GSPC') return price.toLocaleString('en-US', { maximumFractionDigits: 0 })
  return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function TickerBanner() {
  const [prices, setPrices] = useState<Record<string, { price: number; change_pct: number }>>({})

  useEffect(() => {
    getMarketPrices(TICKERS).then(setPrices).catch(() => {})
    const id = setInterval(() => {
      getMarketPrices(TICKERS).then(setPrices).catch(() => {})
    }, 60_000)
    return () => clearInterval(id)
  }, [])

  const tickers = TICKERS.split(',')
  const hasData = tickers.some(t => prices[t])

  const items = tickers.map(t => {
    const d = prices[t]
    if (!d) return `${LABELS[t]}  —`
    const unit = UNITS[t] ? ` ${UNITS[t]}` : ''
    const sign = d.change_pct >= 0 ? '▲' : '▼'
    return `${LABELS[t]}  ${fmt(t, d.price)}${unit}  ${sign} ${Math.abs(d.change_pct).toFixed(2)}%`
  }).join('     ·     ')

  const repeated = `${items}     ·     ${items}`

  return (
    <div className="ticker-banner">
      <div className={`ticker-track${hasData ? ' ticker-animate' : ''}`}>
        <span>{repeated}</span>
      </div>
    </div>
  )
}
