// Market-Dashboard (Phase 6) — zentrale Übersicht aller Market-Tabs.
// Hero-Metric-Strip + 2-Spalten-Grid mit Kurzüberblicken, die in die Detail-Tabs verlinken.
// Nur echte Daten aus vorhandenen Endpoints; jede Quelle lädt unabhängig (graceful degradation).
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getPortfolio, getMarketPrices, getHotStocks, getWatchlist, getBriefingPreview,
  type WatchlistCategory, type StockDetail, type Position,
} from '../services/api'
import { computePnl, type PnlStats } from '../components/market/portfolio-panels'
import type { Tab, HotStockRow } from '../components/market/hot-stocks/hot-data'
import { topPositions, topMovers } from '../components/market/dashboard/dashboard-data'
import { HeroStrip } from '../components/market/dashboard/HeroStrip'
import { PortfolioSnapshot } from '../components/market/dashboard/PortfolioSnapshot'
import { HotStocksRadar } from '../components/market/dashboard/HotStocksRadar'
import { WatchlistMovers } from '../components/market/dashboard/WatchlistMovers'

type Quote = { price: number; change_pct: number }

export default function Dashboard() {
  const [pnl, setPnl] = useState<PnlStats | null>(null)
  const [market, setMarket] = useState<Record<string, Quote>>({})
  const [tabs, setTabs] = useState<Record<Tab, HotStockRow[]> | null>(null)
  const [movers, setMovers] = useState<StockDetail[]>([])
  const [preview, setPreview] = useState<{ preview: string; date: string } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Portfolio + Kurse (inkl. Indizes) in einem Marktdaten-Call.
    const portfolioFlow = getPortfolio()
      .then(async pf => {
        const tickers = pf.positions.map((p: Position) => p.ticker).filter(Boolean)
        const all = Array.from(new Set([...tickers, '^GSPC', '^VIX'])).join(',')
        const prices = await getMarketPrices(all).catch(() => ({} as Record<string, Quote>))
        setMarket(prices)
        setPnl(computePnl(pf.positions, prices))
      })
      .catch(() => {})

    const hotFlow = getHotStocks().then(setTabs).catch(() => {})
    const watchFlow = getWatchlist()
      .then((cats: WatchlistCategory[]) => setMovers(topMovers(cats)))
      .catch(() => {})
    const briefingFlow = getBriefingPreview().then(setPreview).catch(() => {})

    Promise.allSettled([portfolioFlow, hotFlow, watchFlow, briefingFlow]).finally(() => setLoading(false))
  }, [])

  const snapshot = pnl ? topPositions(pnl) : []

  return (
    <main className="page page-enter">
      <HeroStrip
        totalValue={pnl?.totalValue ?? 0}
        totalPnl={pnl?.totalPnl ?? 0}
        totalPnlPct={pnl?.totalPnlPct ?? 0}
        anyPnl={pnl?.anyPnl ?? false}
        sp={market['^GSPC']}
        vix={market['^VIX']}
      />

      <div className="grid-main-sidebar">
        {/* Hauptspalte: Snapshot + Hot-Stocks-Radar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <PortfolioSnapshot rows={snapshot} loading={loading} />
          <HotStocksRadar tabs={tabs} loading={loading} />
        </div>

        {/* Sidebar: Briefing-Preview + Watchlist-Movers */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
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

          <WatchlistMovers rows={movers} loading={loading} />
        </div>
      </div>
    </main>
  )
}
