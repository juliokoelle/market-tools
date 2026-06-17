import { useEffect, useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getWatchlist, searchTickers, type WatchlistCategory } from '../services/api'
import { Panel, Sparkline, Delta } from '../components/market/primitives'
import { ScoreBadge } from '../components/market/score'
import { fmtCurrencyExact } from '../lib/format'

const SEARCH_UNIVERSE = [
  "AAPL","MSFT","NVDA","GOOGL","GOOG","META","AVGO","AMD","ORCL","AMZN",
  "TSLA","ADBE","CRM","NOW","SNOW","PLTR","MU","INTC","QCOM","TXN",
  "IBM","AMAT","LRCX","ASML","SAP","TSM","JPM","BAC","V","MA",
  "GS","MS","BRK-B","LLY","UNH","JNJ","PFE","ABBV","MRK","TMO",
  "XOM","CVX","COP","NEE","HD","NKE","SBUX","COST","WMT","NFLX",
  "DIS","PYPL","SQ","COIN","RIVN","NVO","LVMH.PA","VWCE.DE","4GLD.DE",
  "BAYN.DE","BMW.DE","SIE.DE","BABA","JD","PDD","NEM","FCX",
]

interface Suggestion { ticker: string; name: string }

function SearchBar({ onSearch }: { onSearch: (ticker: string) => void }) {
  const [q, setQ] = useState('')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const ref = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const runSearch = useCallback((v: string) => {
    const upper = v.toUpperCase().trim()
    if (!upper) { setSuggestions([]); return }
    const local = SEARCH_UNIVERSE.filter(t => t.startsWith(upper)).slice(0, 5).map(t => ({ ticker: t, name: t }))
    setSuggestions(local)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      searchTickers(v).then(results => {
        const remote = results.map(r => ({ ticker: r.ticker, name: r.name }))
        setSuggestions(prev => {
          const seen = new Set(prev.map(s => s.ticker))
          return [...prev, ...remote.filter(r => !seen.has(r.ticker))].slice(0, 8)
        })
      }).catch(() => {})
    }, 320)
  }, [])

  function pick(ticker: string) { setQ(''); setSuggestions([]); onSearch(ticker) }

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setSuggestions([])
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative', maxWidth: 340, marginBottom: '1.75rem' }}>
      <input
        value={q}
        onChange={e => { setQ(e.target.value); runSearch(e.target.value) }}
        onKeyDown={e => {
          if (e.key === 'Enter' && q.trim()) pick(q.trim().toUpperCase())
          else if (e.key === 'Escape') setSuggestions([])
        }}
        placeholder="Ticker oder Firma suchen…"
        autoComplete="off"
        spellCheck={false}
        style={{
          width: '100%',
          padding: '.55rem .75rem',
          border: '1px solid var(--border)',
          borderRadius: 10,
          fontSize: '.9rem',
          outline: 'none',
          background: 'var(--surface-alt)',
          color: 'var(--text)',
          fontFamily: 'inherit',
          boxSizing: 'border-box',
        }}
      />
      {suggestions.length > 0 && (
        <ul style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          zIndex: 99,
          margin: '.25rem 0 0',
          padding: 0,
          listStyle: 'none',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 10,
          boxShadow: 'var(--shadow-md)',
          overflow: 'hidden',
        }}>
          {suggestions.map(s => (
            <li
              key={s.ticker}
              onClick={() => pick(s.ticker)}
              style={{
                padding: '.45rem .75rem',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '.85rem',
                color: 'var(--text)',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-alt)')}
              onMouseLeave={e => (e.currentTarget.style.background = '')}
            >
              <span style={{ fontWeight: 600 }}>{s.ticker}</span>
              <span style={{ color: 'var(--text-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180 }}>{s.name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function Analyzer() {
  const navigate = useNavigate()
  const [categories, setCategories] = useState<WatchlistCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function go(ticker: string) {
    navigate('/market/analyzer/' + ticker)
  }

  useEffect(() => {
    getWatchlist()
      .then(cats => { setCategories(cats); setLoading(false) })
      .catch(e => { setError((e as Error).message ?? 'Fehler'); setLoading(false) })
  }, [])

  return (
    <main style={{ padding: '1.5rem', maxWidth: 900, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '.25rem' }}>Stock Analyzer</h1>
      <p style={{ color: 'var(--text-3)', fontSize: '.85rem', marginBottom: '1.5rem' }}>
        Watchlist durchsuchen — Klick für Detail-Analyse
      </p>

      <SearchBar onSearch={go} />

      {loading && <p style={{ color: 'var(--text-3)' }}>Lädt…</p>}
      {error && <p style={{ color: 'var(--loss)' }}>{error}</p>}

      {categories.map(cat => (
        <div key={cat.category} style={{ marginBottom: '2rem' }}>
          <h2 style={{
            fontSize: '.75rem',
            fontWeight: 700,
            letterSpacing: '.08em',
            textTransform: 'uppercase',
            color: 'var(--text-3)',
            marginBottom: '.75rem',
          }}>
            {cat.category}
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '.75rem' }}>
            {cat.stocks.map(s => (
              <div
                key={s.ticker}
                onClick={() => go(s.ticker)}
                onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(s.ticker) } }}
                role="button"
                tabIndex={0}
                style={{ cursor: 'pointer' }}
              >
                <Panel style={{ height: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ minWidth: 0 }}>
                      <p style={{ margin: 0, fontWeight: 700, fontSize: '.85rem', color: 'var(--text)' }}>{s.ticker}</p>
                      <p style={{
                        margin: '.1rem 0 0',
                        fontSize: '.7rem',
                        color: 'var(--text-3)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: 110,
                      }}>{s.name}</p>
                    </div>
                    <ScoreBadge score={s.bull_score} label="B" />
                  </div>
                  {s.spark && s.spark.length > 1 && (
                    <div style={{ margin: '.6rem 0' }}>
                      <Sparkline values={s.spark} width={170} height={32} />
                    </div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '.4rem' }}>
                    <span className="tabular" style={{ fontWeight: 700, fontSize: '.85rem' }}>
                      {s.price ? fmtCurrencyExact(s.price) : '—'}
                    </span>
                    <Delta value={s.change_pct} />
                  </div>
                </Panel>
              </div>
            ))}
          </div>
        </div>
      ))}
    </main>
  )
}
