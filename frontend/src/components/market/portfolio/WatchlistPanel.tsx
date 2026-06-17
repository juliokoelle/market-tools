import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Star } from 'lucide-react'
import { getWatchlist, getStockDetail, getStockAiSummary, type StockDetail } from '../../../services/api'
import { Sparkline, Delta } from '../primitives'
import { ScoreBadge } from '../score'
import { fmtCurrency, fmtMarketCap, fmtNumber } from '../../../lib/format'
import { buildEnrichmentMap, mergeRow, type EnrichedRow, type WatchRow } from './watchlist-data'

const DASH = '—'

interface Props {
  tickers: string[]
  portfolioTickers: Set<string>
  loading: boolean
  universe: string[]
  inputStyle: React.CSSProperties
  onAdd: (ticker: string) => void
  onRemove: (ticker: string) => void
  onTransfer: (t: { ticker: string; price: number }) => void
}

const TH = ['', 'Stock', 'Trend', 'Price', 'Day', 'Market Cap', 'Rel Vol', 'Bull', 'Mom', 'Why', '']

export default function WatchlistPanel({
  tickers, portfolioTickers, loading, universe, inputStyle, onAdd, onRemove, onTransfer,
}: Props) {
  const [enrich, setEnrich] = useState<Map<string, EnrichedRow>>(new Map())
  const [details, setDetails] = useState<Record<string, StockDetail>>({})
  const [why, setWhy] = useState<Record<string, string>>({})
  const [whyLoading, setWhyLoading] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLDivElement>(null)

  // Schnell-Quelle: /watchlist (gecacht, deckt 6 Spalten)
  useEffect(() => {
    if (!tickers.length) { setEnrich(new Map()); return }
    getWatchlist().then(cats => setEnrich(buildEnrichmentMap(cats))).catch(() => {})
  }, [tickers])

  // Hintergrund: per-Ticker Detail (Market Cap + Rel Vol), max 4 parallel
  useEffect(() => {
    if (!tickers.length) return
    let cancelled = false
    const queue = tickers.filter(t => !details[t])
    let i = 0
    const worker = async () => {
      while (!cancelled && i < queue.length) {
        const t = queue[i++]
        try {
          const d = await getStockDetail(t)
          if (!cancelled) setDetails(prev => ({ ...prev, [t]: d }))
        } catch { /* degrade to — */ }
      }
    }
    Promise.all(Array.from({ length: 4 }, worker))
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tickers])

  async function loadWhy(ticker: string) {
    if (why[ticker] || whyLoading) return
    setWhyLoading(ticker)
    try {
      const r = await getStockAiSummary(ticker)
      setWhy(prev => ({ ...prev, [ticker]: r.summary || 'Keine Zusammenfassung.' }))
    } catch {
      setWhy(prev => ({ ...prev, [ticker]: 'Konnte nicht geladen werden.' }))
    } finally {
      setWhyLoading(null)
    }
  }

  const rows: WatchRow[] = tickers.map(t => mergeRow(t, enrich.get(t), details[t]))
  const matches = input.length >= 1 ? universe.filter(t => t.startsWith(input) && !tickers.includes(t)).slice(0, 6) : []

  const cell: React.CSSProperties = { padding: '.7rem .9rem', fontSize: '.85rem', verticalAlign: 'middle' }
  const th: React.CSSProperties = { padding: '.6rem .9rem', textAlign: 'left', fontSize: '.62rem', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.06em' }

  return (
    <div>
      {/* Add ticker */}
      <div className="card" style={{ marginBottom: '1rem', padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', gap: '.75rem', alignItems: 'center' }}>
          <div ref={inputRef} style={{ position: 'relative', flex: 1 }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value.toUpperCase().replace(/\s/g, ''))}
              onKeyDown={e => { if (e.key === 'Enter' && input) { onAdd(input); setInput('') } }}
              placeholder="Search ticker (e.g. AAPL)"
              autoComplete="off" spellCheck={false} style={inputStyle}
            />
            {matches.length > 0 && (
              <ul className="dropdown-list" style={{
                position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
                background: 'var(--surface)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)', boxShadow: 'var(--shadow)',
                listStyle: 'none', margin: 0, padding: '.25rem 0',
              }}>
                {matches.map(s => (
                  <li key={s} onMouseDown={e => { e.preventDefault(); onAdd(s); setInput('') }}
                    style={{ padding: '.4rem .75rem', fontSize: '.875rem', cursor: 'pointer', color: 'var(--text)' }}>{s}</li>
                ))}
              </ul>
            )}
          </div>
          <button onClick={() => { if (input) { onAdd(input); setInput('') } }} className="btn btn-outline" style={{ fontSize: '.8rem', flexShrink: 0 }}>+ Add</button>
        </div>
      </div>

      {/* Rich table */}
      <div className="card table-scroll" style={{ padding: 0 }}>
        {loading ? (
          <p style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-3)', fontSize: '.875rem' }}>Loading…</p>
        ) : tickers.length === 0 ? (
          <p style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-3)', fontSize: '.875rem' }}>
            Your watchlist is empty. Search for a ticker above to add.
          </p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 900 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {TH.map((h, i) => <th key={i} style={th}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const inPf = portfolioTickers.has(r.ticker)
                return (
                  <tr key={r.ticker} style={{ borderBottom: i < rows.length - 1 ? '1px solid var(--border)' : 'none' }}>
                    <td style={cell}>
                      <button onClick={() => onRemove(r.ticker)} title="Remove from watchlist"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, lineHeight: 0 }}>
                        <Star size={15} fill="var(--brand)" color="var(--brand)" />
                      </button>
                    </td>
                    <td style={{ ...cell, fontWeight: 600 }}>
                      <Link to={`/market/analyzer/${encodeURIComponent(r.ticker)}`} style={{ color: 'inherit', textDecoration: 'none' }}>
                        {r.name !== r.ticker ? `${r.name} — ${r.ticker}` : r.ticker}
                      </Link>
                    </td>
                    <td style={cell}>{r.spark.length ? <Sparkline values={r.spark} width={72} height={22} /> : <span style={{ color: 'var(--text-3)' }}>{DASH}</span>}</td>
                    <td style={{ ...cell, color: 'var(--text-2)' }} className="tabular">{r.price != null ? fmtCurrency(r.price) : '···'}</td>
                    <td style={cell}>{r.changePct != null ? <Delta value={r.changePct} /> : <span style={{ color: 'var(--text-3)' }}>···</span>}</td>
                    <td style={{ ...cell, color: 'var(--text-2)' }} className="tabular">{r.marketCap != null ? fmtMarketCap(r.marketCap, 'EUR') : DASH}</td>
                    <td style={{ ...cell, color: 'var(--text-2)' }} className="tabular">{r.relVol != null ? `${fmtNumber(r.relVol, 2)}×` : DASH}</td>
                    <td style={cell}>{r.bull != null ? <ScoreBadge score={r.bull} /> : <span style={{ color: 'var(--text-3)' }}>···</span>}</td>
                    <td style={cell}>{r.momentum != null ? <ScoreBadge score={r.momentum} /> : <span style={{ color: 'var(--text-3)' }}>···</span>}</td>
                    <td style={{ ...cell, maxWidth: 220 }}>
                      {why[r.ticker] ? (
                        <span style={{ fontSize: '.78rem', color: 'var(--text-2)' }}>{why[r.ticker]}</span>
                      ) : (
                        <button onClick={() => loadWhy(r.ticker)} className="btn btn-outline" style={{ fontSize: '.72rem', padding: '.25rem .55rem' }}>
                          {whyLoading === r.ticker ? '…' : 'Why ↗'}
                        </button>
                      )}
                    </td>
                    <td style={cell}>
                      <div style={{ display: 'flex', gap: '.5rem', justifyContent: 'flex-end', alignItems: 'center' }}>
                        {inPf ? (
                          <span className="badge badge-teal" style={{ fontSize: '.65rem' }}>In Portfolio</span>
                        ) : (
                          <button onClick={() => onTransfer({ ticker: r.ticker, price: r.price ?? 0 })} className="btn btn-outline" style={{ fontSize: '.72rem', padding: '.25rem .55rem' }}>→ Portfolio</button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
