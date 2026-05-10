import { useEffect, useRef, useState } from 'react'
import { getPortfolio, savePortfolio, analyzePortfolio, type Position, type PortfolioAnalysis } from '../services/api'

const UNIVERSE = [
  "AAPL","MSFT","NVDA","GOOG","META","AVGO","AMD","ORCL","CRM","ADBE",
  "INTC","QCOM","TXN","IBM","NOW","SNOW","PLTR","MU","AMAT","LRCX",
  "AMZN","TSLA","HD","MCD","NKE","SBUX","BKNG","LOW","TGT","ABNB",
  "EBAY","GM","F","UBER","LYFT","NFLX","DIS","CMCSA","T","VZ",
  "TMUS","SNAP","PINS","BRK-B","JPM","BAC","WFC","GS","MS","C",
  "AXP","BLK","SCHW","V","MA","PYPL","COF","JNJ","LLY","UNH",
  "PFE","ABBV","MRK","TMO","ABT","DHR","AMGN","GILD","ISRG","CVS",
  "HUM","CAT","HON","GE","BA","LMT","RTX","DE","UPS","FDX",
  "CSX","NSC","XOM","CVX","COP","SLB","EOG","PSX","MPC","PG",
  "KO","PEP","COST","WMT","PM","MO","CL","LIN","APD","FCX",
  "NEM","DOW","AMT","PLD","EQIX","SPG","NEE","DUK","SO","D",
  "VWCE.DE","4GLD.DE","ASML","SAP","BAYN.DE","BMW.DE","SIE.DE",
]

const PORTFOLIO_SEED: Position[] = [
  { ticker: "VWCE.DE", investment: 650 },
  { ticker: "NVDA",    investment: 180 },
  { ticker: "ASML",    investment: 180 },
  { ticker: "MSFT",    investment: 150 },
  { ticker: "GOOGL",   investment: 120 },
  { ticker: "PLTR",    investment: 150 },
  { ticker: "4GLD.DE", investment: 570 },
]

const SEED_KEY = 'mt_portfolio_seed_seen'

function TickerInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [activeIdx, setActiveIdx] = useState(-1)
  const ref = useRef<HTMLDivElement>(null)

  function filter(q: string) {
    const upper = q.toUpperCase()
    setSuggestions(upper ? UNIVERSE.filter(t => t.startsWith(upper)).slice(0, 6) : [])
    setActiveIdx(-1)
  }

  function pick(ticker: string) {
    onChange(ticker)
    setSuggestions([])
  }

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setSuggestions([])
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <input
        value={value}
        onChange={e => { const v = e.target.value.toUpperCase().replace(/\s/g, ''); onChange(v); filter(v) }}
        onKeyDown={e => {
          if (!suggestions.length) return
          if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx(i => Math.min(i + 1, suggestions.length - 1)) }
          else if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIdx(i => Math.max(i - 1, -1)) }
          else if (e.key === 'Enter' && activeIdx >= 0) { e.preventDefault(); pick(suggestions[activeIdx]) }
          else if (e.key === 'Escape') setSuggestions([])
        }}
        placeholder="e.g. AAPL"
        autoComplete="off"
        spellCheck={false}
        style={inputStyle}
      />
      {suggestions.length > 0 && (
        <ul style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
          background: 'var(--bg-elevated)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius-sm)', boxShadow: 'var(--shadow)',
          listStyle: 'none', margin: 0, padding: '.25rem 0',
        }}>
          {suggestions.map((s, i) => (
            <li key={s}
              onMouseDown={e => { e.preventDefault(); pick(s) }}
              style={{
                padding: '.4rem .75rem', fontSize: '.875rem', cursor: 'pointer',
                background: i === activeIdx ? 'var(--accent-lt)' : 'transparent',
                color: i === activeIdx ? 'var(--accent)' : 'var(--text-primary)',
              }}
            >{s}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function SeedModal({ onAccept, onDecline }: { onAccept: () => void; onDecline: () => void }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
      <div className="card" style={{ width: '100%', maxWidth: 380 }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '.4rem' }}>Start with a demo portfolio?</h3>
        <p style={{ fontSize: '.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '1.25rem' }}>
          Load a sample portfolio to explore the analysis features.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '.25rem', marginBottom: '1.25rem', fontSize: '.8rem' }}>
          {PORTFOLIO_SEED.map(p => (
            <div key={p.ticker} style={{ display: 'flex', justifyContent: 'space-between', padding: '.25rem 0', borderBottom: '1px solid var(--border)' }}>
              <span style={{ fontWeight: 700 }}>{p.ticker}</span>
              <span style={{ color: 'var(--text-secondary)' }}>€{p.investment}</span>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '.75rem' }}>
          <button onClick={onAccept} className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }}>Load demo</button>
          <button onClick={onDecline} className="btn btn-outline" style={{ flex: 1, justifyContent: 'center' }}>Skip</button>
        </div>
      </div>
    </div>
  )
}

export default function Portfolio() {
  const [positions, setPositions] = useState<Position[]>([
    { ticker: 'AAPL', investment: 5000 },
    { ticker: 'MSFT', investment: 3000 },
    { ticker: 'TSLA', investment: 2000 },
  ])
  const [analysis, setAnalysis]   = useState<PortfolioAnalysis | null>(null)
  const [saving, setSaving]       = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [toast, setToast]         = useState('')
  const [showSeed, setShowSeed]   = useState(false)

  useEffect(() => {
    getPortfolio()
      .then(d => {
        if (d.positions?.length) {
          setPositions(d.positions)
        } else if (!localStorage.getItem(SEED_KEY)) {
          setShowSeed(true)
        }
      })
      .catch(() => {
        if (!localStorage.getItem(SEED_KEY)) setShowSeed(true)
      })
  }, [])

  function showToast(msg: string) {
    setToast(msg); setTimeout(() => setToast(''), 3000)
  }

  function addRow() { setPositions(p => [...p, { ticker: '', investment: 0 }]) }
  function removeRow(i: number) { setPositions(p => p.filter((_, j) => j !== i)) }
  function updateTicker(i: number, v: string)      { setPositions(p => p.map((r, j) => j === i ? { ...r, ticker: v } : r)) }
  function updateInvestment(i: number, v: number)  { setPositions(p => p.map((r, j) => j === i ? { ...r, investment: v } : r)) }

  function acceptSeed() {
    localStorage.setItem(SEED_KEY, '1')
    setShowSeed(false)
    setPositions(PORTFOLIO_SEED)
  }
  function declineSeed() {
    localStorage.setItem(SEED_KEY, '1')
    setShowSeed(false)
    setPositions([{ ticker: '', investment: 0 }])
  }

  async function handleSave() {
    setSaving(true)
    try { await savePortfolio(positions.filter(p => p.ticker)); showToast('Portfolio saved ✓') }
    catch { showToast('Save failed') }
    finally { setSaving(false) }
  }

  async function handleAnalyze() {
    const valid = positions.filter(p => p.ticker && p.investment > 0)
    if (!valid.length) return
    setAnalyzing(true)
    try { setAnalysis(await analyzePortfolio(valid)) }
    catch { showToast('Analysis failed') }
    finally { setAnalyzing(false) }
  }

  return (
    <main className="page-enter section">
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1.5rem' }}>Portfolio</h1>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>Holdings</h2>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 160px 36px', gap: '.5rem .75rem', marginBottom: '.75rem' }}>
          <p style={labelStyle}>Ticker</p>
          <p style={labelStyle}>Investment (€)</p>
          <span />
          {positions.map((p, i) => (
            <>
              <TickerInput key={`t${i}`} value={p.ticker} onChange={v => updateTicker(i, v)} />
              <input
                key={`v${i}`}
                type="number"
                value={p.investment || ''}
                onChange={e => updateInvestment(i, parseFloat(e.target.value) || 0)}
                placeholder="5000"
                style={inputStyle}
              />
              <button
                key={`d${i}`}
                onClick={() => removeRow(i)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '1.1rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >×</button>
            </>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '.75rem', flexWrap: 'wrap' }}>
          <button onClick={addRow} className="btn btn-outline" style={{ fontSize: '.8rem' }}>+ Add row</button>
          <button onClick={handleSave} disabled={saving} className="btn btn-outline" style={{ fontSize: '.8rem' }}>
            {saving ? 'Saving…' : '↑ Save to GitHub'}
          </button>
          <button onClick={handleAnalyze} disabled={analyzing} className="btn btn-primary" style={{ fontSize: '.8rem' }}>
            {analyzing ? 'Analyzing…' : '⚡ Analyze'}
          </button>
        </div>
      </div>

      {analysis && <AnalysisCard a={analysis} />}

      {showSeed && <SeedModal onAccept={acceptSeed} onDecline={declineSeed} />}

      {toast && (
        <div className="toast-container">
          <div className="toast toast-info">{toast}</div>
        </div>
      )}
    </main>
  )
}

function AnalysisCard({ a }: { a: PortfolioAnalysis }) {
  const vol = a.volatility ?? 0
  const riskLabel = vol < 15 ? 'Conservative' : vol < 25 ? 'Moderate' : 'Aggressive'
  const riskColor = vol < 15 ? 'var(--positive)' : vol < 25 ? 'var(--neutral)' : 'var(--negative)'

  return (
    <div className="card">
      <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '1.25rem' }}>Analysis</h2>
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        {[
          { label: 'Total Value',   value: `€${(a.total_value ?? 0).toLocaleString('de-DE', { maximumFractionDigits: 0 })}`, color: undefined },
          { label: 'Annual Return', value: `${(a.annual_return ?? 0).toFixed(1)}%`, color: (a.annual_return ?? 0) >= 0 ? 'var(--positive)' : 'var(--negative)' },
          { label: 'Volatility',   value: `${(a.volatility ?? 0).toFixed(1)}%`, color: undefined },
          { label: 'Risk Profile', value: riskLabel, color: riskColor },
        ].map(m => (
          <div key={m.label} style={{ padding: '.75rem', background: 'var(--bg-tertiary)', borderRadius: 8 }}>
            <p style={{ fontSize: '.75rem', color: 'var(--text-secondary)', marginBottom: '.25rem' }}>{m.label}</p>
            <p style={{ fontSize: '1.1rem', fontWeight: 700, color: m.color ?? 'var(--text-primary)' }}>{m.value}</p>
          </div>
        ))}
      </div>

      {a.insight && (
        <p style={{ fontSize: '.875rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '1.25rem', padding: '1rem', background: 'var(--accent-lt)', borderRadius: 8, borderLeft: `3px solid var(--accent)` }}>
          {a.insight}
        </p>
      )}

      {a.positions?.length > 0 && (
        <div>
          <p style={{ fontSize: '.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '.5rem', textTransform: 'uppercase', letterSpacing: '.04em' }}>Positions</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.35rem' }}>
            {a.positions.map(p => (
              <div key={p.ticker} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '.875rem', padding: '.4rem 0', borderBottom: '1px solid var(--border)' }}>
                <span style={{ fontWeight: 700 }}>{p.ticker}</span>
                <span style={{ color: 'var(--text-secondary)' }}>€{p.value.toLocaleString('de-DE', { maximumFractionDigits: 0 })}</span>
                <span style={{ color: p.gain_pct >= 0 ? 'var(--positive)' : 'var(--negative)', fontWeight: 600 }}>
                  {p.gain_pct >= 0 ? '+' : ''}{p.gain_pct.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const labelStyle: React.CSSProperties = {
  fontSize: '.75rem', fontWeight: 600, color: 'var(--text-secondary)',
  textTransform: 'uppercase', letterSpacing: '.04em',
}
const inputStyle: React.CSSProperties = {
  padding: '.45rem .6rem', border: '1px solid var(--border)',
  borderRadius: 6, fontSize: '.875rem', outline: 'none', width: '100%',
  background: 'var(--bg-tertiary)', color: 'var(--text-primary)',
}
