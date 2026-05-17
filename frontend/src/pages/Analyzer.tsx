import { useEffect, useRef, useState, useCallback } from 'react'
import { getWatchlist, getStockDetail, getStockAiSummary, getStockChart, searchTickers, type WatchlistCategory, type StockDetail, type ChartPoint } from '../services/api'

const SEARCH_UNIVERSE = [
  "AAPL","MSFT","NVDA","GOOGL","GOOG","META","AVGO","AMD","ORCL","AMZN",
  "TSLA","ADBE","CRM","NOW","SNOW","PLTR","MU","INTC","QCOM","TXN",
  "IBM","AMAT","LRCX","ASML","SAP","TSM","JPM","BAC","V","MA",
  "GS","MS","BRK-B","LLY","UNH","JNJ","PFE","ABBV","MRK","TMO",
  "XOM","CVX","COP","NEE","HD","NKE","SBUX","COST","WMT","NFLX",
  "DIS","PYPL","SQ","COIN","RIVN","NVO","LVMH.PA","VWCE.DE","4GLD.DE",
  "BAYN.DE","BMW.DE","SIE.DE","BABA","JD","PDD","NEM","FCX",
]

function BullRing({ score }: { score: number }) {
  const color = score > 60 ? '#059669' : score > 40 ? '#d97706' : '#dc2626'
  const r = 18, circ = 2 * Math.PI * r
  const dash = (score / 100) * circ
  return (
    <svg width="48" height="48" viewBox="0 0 48 48">
      <circle cx="24" cy="24" r={r} fill="none" stroke="var(--border)" strokeWidth="4" />
      <circle cx="24" cy="24" r={r} fill="none" stroke={color} strokeWidth="4"
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
        transform="rotate(-90 24 24)" />
      <text x="24" y="28" textAnchor="middle" fontSize="11" fontWeight="700" fill={color}>{score}</text>
    </svg>
  )
}

function CandlestickChart({ data }: { data: ChartPoint[] }) {
  if (!data.length) return null
  const W = 540, H = 160, padL = 45, padR = 8, padT = 8, padB = 20
  const prices = data.flatMap(d => [d.high, d.low])
  const minP = Math.min(...prices), maxP = Math.max(...prices)
  const range = maxP - minP || 1
  const scaleY = (p: number) => padT + (1 - (p - minP) / range) * (H - padT - padB)
  const n = data.length
  const slotW = (W - padL - padR) / n
  const candleW = Math.max(2, slotW - 2)
  const cx = (i: number) => padL + (i + 0.5) * slotW

  const yLabels = [0, 0.25, 0.5, 0.75, 1].map(t => ({
    price: minP + t * range,
    y: padT + (1 - t) * (H - padT - padB),
  }))

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      {yLabels.map(({ price, y }) => (
        <g key={y}>
          <line x1={padL - 3} y1={y} x2={W - padR} y2={y} stroke="var(--border)" strokeWidth="0.5" />
          <text x={padL - 6} y={y + 3.5} textAnchor="end" fontSize="8" fill="var(--text-3)">${price.toFixed(0)}</text>
        </g>
      ))}
      {data.map((d, i) => {
        const bull = d.close >= d.open
        const color = bull ? '#059669' : '#dc2626'
        const bodyTop = scaleY(Math.max(d.open, d.close))
        const bodyBot = scaleY(Math.min(d.open, d.close))
        return (
          <g key={i}>
            <line x1={cx(i)} y1={scaleY(d.high)} x2={cx(i)} y2={scaleY(d.low)} stroke={color} strokeWidth="1" />
            <rect
              x={cx(i) - candleW / 2} y={bodyTop}
              width={candleW} height={Math.max(1, bodyBot - bodyTop)}
              fill={bull ? color : 'transparent'} stroke={color} strokeWidth="1"
            />
          </g>
        )
      })}
    </svg>
  )
}

interface Suggestion { ticker: string; name: string }

function SearchBar({ onSearch }: { onSearch: (ticker: string) => void }) {
  const [q, setQ] = useState('')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const ref = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const runSearch = useCallback((v: string) => {
    const upper = v.toUpperCase().trim()
    if (!upper) { setSuggestions([]); return }

    // Instant local prefix-match
    const local = SEARCH_UNIVERSE
      .filter(t => t.startsWith(upper))
      .slice(0, 5)
      .map(t => ({ ticker: t, name: t }))
    setSuggestions(local)

    // Debounced remote search (name + ticker)
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

  function pick(ticker: string) {
    setQ('')
    setSuggestions([])
    onSearch(ticker)
  }

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setSuggestions([])
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative', maxWidth: 320, marginBottom: '1.75rem' }}>
      <input
        value={q}
        onChange={e => { setQ(e.target.value); runSearch(e.target.value) }}
        onKeyDown={e => {
          if (e.key === 'Enter' && q.trim()) pick(q.trim().toUpperCase())
          else if (e.key === 'Escape') setSuggestions([])
        }}
        placeholder="Search ticker or company name…"
        autoComplete="off"
        spellCheck={false}
        style={{
          width: '100%', padding: '.5rem .75rem .5rem 2.2rem',
          border: '1px solid var(--border)', borderRadius: 8, fontSize: '.875rem',
          outline: 'none', background: 'var(--surface-alt)', color: 'var(--text)',
          fontFamily: 'inherit', boxSizing: 'border-box',
        }}
      />
      <svg style={{ position: 'absolute', left: '.65rem', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}
        width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-3)" strokeWidth="2.5" strokeLinecap="round">
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      {suggestions.length > 0 && (
        <ul style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 8, boxShadow: 'var(--shadow)',
          listStyle: 'none', margin: '.25rem 0 0', padding: '.25rem 0',
        }}>
          {suggestions.map(s => (
            <li key={s.ticker}
              onMouseDown={e => { e.preventDefault(); pick(s.ticker) }}
              style={{ padding: '.4rem .75rem', fontSize: '.85rem', cursor: 'pointer', color: 'var(--text)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '.5rem' }}
            >
              <span style={{ color: 'var(--text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name !== s.ticker ? s.name : ''}</span>
              <span style={{ fontWeight: 700, flexShrink: 0, color: 'var(--text)' }}>{s.ticker}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function StockModal({ ticker, onClose }: { ticker: string; onClose: () => void }) {
  const [detail, setDetail] = useState<StockDetail | null>(null)
  const [summary, setSummary] = useState<string>('')
  const [chartData, setChartData] = useState<ChartPoint[]>([])
  const [chartLoading, setChartLoading] = useState(false)
  const [period, setPeriod] = useState('3mo')

  useEffect(() => {
    getStockDetail(ticker).then(setDetail).catch(() => {})
    getStockAiSummary(ticker).then(d => setSummary(d.summary)).catch(() => {})
  }, [ticker])

  useEffect(() => {
    setChartLoading(true)
    setChartData([])
    getStockChart(ticker, period)
      .then(setChartData)
      .catch(() => {})
      .finally(() => setChartLoading(false))
  }, [ticker, period])

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }} onClick={onClose}>
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', width: '100%', maxWidth: 620, maxHeight: '88vh', overflow: 'auto', padding: '1.5rem' }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>{ticker}</h2>
            {detail && <p style={{ fontSize: '.85rem', color: 'var(--text-3)' }}>{detail.name} · {detail.sector}</p>}
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.5rem', color: 'var(--text-3)', cursor: 'pointer' }}>×</button>
        </div>

        {/* Metrics */}
        {detail && (
          <div className="grid-3" style={{ marginBottom: '1.25rem' }}>
            {[
              { label: 'Price',      value: `$${detail.price.toFixed(2)}` },
              { label: 'Bull Score', value: String(detail.bull_score) },
              { label: 'Change',     value: `${detail.change_pct >= 0 ? '+' : ''}${detail.change_pct.toFixed(2)}%`, color: detail.change_pct >= 0 ? '#059669' : '#dc2626' },
              { label: '52W High',   value: `$${detail.week_52_high?.toFixed(2) ?? '—'}` },
              { label: '52W Low',    value: `$${detail.week_52_low?.toFixed(2) ?? '—'}` },
              { label: 'P/E',        value: detail.pe_ratio?.toFixed(1) ?? '—' },
              { label: 'Market Cap', value: detail.market_cap ? `$${(detail.market_cap / 1e9).toFixed(1)}B` : '—' },
              { label: 'Sector',     value: detail.sector ?? '—' },
            ].map(m => (
              <div key={m.label} style={{ padding: '.55rem .65rem', background: 'var(--surface-alt)', borderRadius: 6 }}>
                <p style={{ fontSize: '.68rem', color: 'var(--text-3)', marginBottom: '.1rem', textTransform: 'uppercase', letterSpacing: '.03em' }}>{m.label}</p>
                <p style={{ fontWeight: 700, fontSize: '.9rem', color: (m as any).color ?? 'var(--text)' }}>{m.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Chart */}
        <div style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', gap: '.35rem', marginBottom: '.75rem' }}>
            {['1mo', '3mo', '6mo', '1y'].map(p => (
              <button key={p} onClick={() => setPeriod(p)} className="btn btn-outline"
                style={{ fontSize: '.75rem', padding: '.3rem .6rem', background: period === p ? 'var(--primary)' : undefined, color: period === p ? '#fff' : undefined }}>
                {p}
              </button>
            ))}
          </div>
          <div style={{ background: 'var(--surface-alt)', borderRadius: 8, padding: '.75rem', minHeight: 80 }}>
            {chartLoading
              ? <p style={{ textAlign: 'center', fontSize: '.8rem', color: 'var(--text-3)', padding: '1rem 0' }}>Loading chart…</p>
              : chartData.length > 0
                ? <CandlestickChart data={chartData} />
                : <p style={{ textAlign: 'center', fontSize: '.8rem', color: 'var(--text-3)', padding: '1rem 0' }}>Chart unavailable</p>
            }
          </div>
        </div>

        {/* AI summary */}
        {summary && (
          <div style={{ padding: '1rem', background: 'var(--surface-alt)', borderRadius: 8, borderLeft: '3px solid var(--primary)' }}>
            <p style={{ fontSize: '.72rem', fontWeight: 600, color: 'var(--primary)', marginBottom: '.5rem', textTransform: 'uppercase', letterSpacing: '.05em' }}>AI Analysis</p>
            <p style={{ fontSize: '.875rem', lineHeight: 1.7, color: 'var(--text)' }}>{summary}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Analyzer() {
  const [categories, setCategories] = useState<WatchlistCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    getWatchlist()
      .then(setCategories)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <main className="page-enter section">
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1.25rem' }}>Stock Analyzer</h1>

      <SearchBar onSearch={setSelected} />

      {loading && <p style={{ color: 'var(--text-3)', fontSize: '.875rem' }}>Loading watchlist…</p>}

      {categories.map(cat => (
        <div key={cat.category} style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontWeight: 700, marginBottom: '1rem', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.06em', fontSize: '.8rem' }}>
            {cat.category}
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
            {cat.stocks.map(s => (
              <div
                key={s.ticker}
                className="card"
                style={{ cursor: 'pointer', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '.5rem', transition: 'box-shadow .15s' }}
                onClick={() => setSelected(s.ticker)}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <p style={{ fontWeight: 700, fontSize: '.95rem' }}>{s.ticker}</p>
                    <p style={{ fontSize: '.75rem', color: 'var(--text-3)', maxWidth: 100, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.name}</p>
                  </div>
                  <BullRing score={s.bull_score} />
                </div>
                <p style={{ fontSize: '.95rem', fontWeight: 600 }}>${s.price.toFixed(2)}</p>
                <span style={{ color: s.change_pct >= 0 ? '#059669' : '#dc2626', fontSize: '.8rem', fontWeight: 600 }}>
                  {s.change_pct >= 0 ? '+' : ''}{s.change_pct.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}

      {selected && <StockModal ticker={selected} onClose={() => setSelected(null)} />}
    </main>
  )
}
