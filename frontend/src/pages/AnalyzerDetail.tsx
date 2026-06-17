import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { AlertCircle } from 'lucide-react'
import { getStockDetail, addStockToWatchlist, type StockDetail } from '../services/api'
import { EmptyState } from '../components/market/primitives'
import { CompanyHeader } from '../components/market/analyzer/CompanyHeader'
import { ScorePanel } from '../components/market/analyzer/ScorePanel'
import { PriceChart } from '../components/market/analyzer/PriceChart'
import { FinancialsBars } from '../components/market/analyzer/FinancialsBars'
import { PeerTable } from '../components/market/analyzer/PeerTable'
import { AiSummaryPanel } from '../components/market/analyzer/AiSummaryPanel'

export default function AnalyzerDetail() {
  const { symbol = '' } = useParams()
  const ticker = symbol.toUpperCase()
  const [detail, setDetail] = useState<StockDetail | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true
    setDetail(null); setError(false)
    getStockDetail(ticker)
      .then(d => { if (active) setDetail(d) })
      .catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [ticker])

  return (
    <main className="page-enter section" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {error && (
        <EmptyState
          icon={AlertCircle}
          title={`Keine Daten für ${ticker}`}
          description="Der Ticker konnte nicht geladen werden. Bitte versuche es später erneut."
        />
      )}
      {!error && !detail && (
        <p style={{ color: 'var(--text-3)', fontSize: '.875rem' }}>Lädt {ticker}…</p>
      )}
      {detail && (
        <>
          <CompanyHeader
            detail={detail}
            onWatch={() => addStockToWatchlist(ticker, detail.name).catch(() => {})}
          />
          <ScorePanel detail={detail} />
          <PriceChart ticker={ticker} />
          <FinancialsBars ticker={ticker} />
          <PeerTable ticker={ticker} />
          <AiSummaryPanel ticker={ticker} />
        </>
      )}
    </main>
  )
}
