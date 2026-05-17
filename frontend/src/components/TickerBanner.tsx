import { useEffect, useState } from 'react'
import { getMarketPrices } from '../services/api'

const TICKERS = '^GSPC,GC=F,EURUSD=X,CL=F,^VIX'
const LABELS: Record<string, string> = {
  '^GSPC': 'S&P 500', 'GC=F': 'Gold', 'EURUSD=X': 'EUR/USD', 'CL=F': 'Brent', '^VIX': 'VIX',
}

function fmt(ticker: string, price: number) {
  if (ticker === 'EURUSD=X') return price.toFixed(4)
  if (ticker === '^GSPC') return price.toLocaleString('en-US', { maximumFractionDigits: 0 })
  return price.toFixed(2)
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

  const segments = tickers.map(t => {
    const d = prices[t]
    const label = LABELS[t]
    if (!d) return `<span style="color:#888;margin-right:.3rem">${label}</span><span style="color:#555">···</span>`
    const sign = d.change_pct >= 0 ? '▲' : '▼'
    const color = d.change_pct >= 0 ? '#4ade80' : '#f87171'
    const changeStr = `${sign} ${Math.abs(d.change_pct).toFixed(2)}%`
    return `<span style="color:#aaa;margin-right:.3rem">${label}</span><span style="color:#fff;font-weight:700;margin-right:.35rem">${fmt(t, d.price)}</span><span style="color:${color}">${changeStr}</span>`
  })

  const separator = `<span style="color:#444;margin:0 .8rem">|</span>`
  const track = segments.join(separator)
  const repeated = `${track}${separator}${track}${separator}`

  return (
    <div className="ticker-banner">
      <div className="ticker-track ticker-animate" dangerouslySetInnerHTML={{ __html: repeated }} />
    </div>
  )
}
