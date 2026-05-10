import { useEffect, useState } from 'react'
import { getPortfolio, savePortfolio, analyzePortfolio, type Position, type PortfolioAnalysis } from '../services/api'

export default function Portfolio() {
  const [positions, setPositions] = useState<Position[]>([{ ticker: '', investment: 0 }])
  const [analysis, setAnalysis]   = useState<PortfolioAnalysis | null>(null)
  const [saving, setSaving]       = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [toast, setToast]         = useState('')

  useEffect(() => {
    getPortfolio()
      .then(d => { if (d.positions?.length) setPositions(d.positions) })
      .catch(() => {})
  }, [])

  function showToast(msg: string) {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  function addRow() { setPositions(p => [...p, { ticker: '', investment: 0 }]) }
  function removeRow(i: number) { setPositions(p => p.filter((_, j) => j !== i)) }
  function updateRow(i: number, field: keyof Position, value: string | number) {
    setPositions(p => p.map((row, j) => j === i ? { ...row, [field]: value } : row))
  }

  async function handleSave() {
    setSaving(true)
    try {
      await savePortfolio(positions.filter(p => p.ticker))
      showToast('Portfolio saved ✓')
    } catch { showToast('Save failed') }
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

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 160px 40px', gap: '.5rem .75rem', marginBottom: '.75rem' }}>
          <p style={labelStyle}>Ticker</p>
          <p style={labelStyle}>Investment (€)</p>
          <span />
          {positions.map((p, i) => (
            <>
              <input
                key={`t${i}`}
                value={p.ticker}
                onChange={e => updateRow(i, 'ticker', e.target.value.toUpperCase())}
                placeholder="AAPL"
                style={inputStyle}
              />
              <input
                key={`v${i}`}
                type="number"
                value={p.investment || ''}
                onChange={e => updateRow(i, 'investment', parseFloat(e.target.value) || 0)}
                placeholder="5000"
                style={inputStyle}
              />
              <button onClick={() => removeRow(i)} style={{ background: 'none', border: 'none', color: 'var(--text-faint)', fontSize: '1.1rem', cursor: 'pointer' }}>×</button>
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

      {toast && (
        <div className="toast-container">
          <div className="toast toast-info">{toast}</div>
        </div>
      )}
    </main>
  )
}

function AnalysisCard({ a }: { a: PortfolioAnalysis }) {
  const riskLabel = a.volatility < 15 ? 'Conservative' : a.volatility < 25 ? 'Moderate' : 'Aggressive'
  const riskColor = a.volatility < 15 ? '#059669' : a.volatility < 25 ? '#d97706' : '#dc2626'

  return (
    <div className="card">
      <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '1.25rem' }}>Analysis</h2>
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        {[
          { label: 'Total Value', value: `€${a.total_value.toLocaleString('de-DE', { maximumFractionDigits: 0 })}` },
          { label: 'Annual Return', value: `${a.annual_return.toFixed(1)}%`, color: a.annual_return >= 0 ? '#059669' : '#dc2626' },
          { label: 'Volatility', value: `${a.volatility.toFixed(1)}%` },
          { label: 'Risk Profile', value: riskLabel, color: riskColor },
        ].map(m => (
          <div key={m.label} style={{ padding: '.75rem', background: 'var(--surface-alt)', borderRadius: 8 }}>
            <p style={{ fontSize: '.75rem', color: 'var(--text-muted)', marginBottom: '.25rem' }}>{m.label}</p>
            <p style={{ fontSize: '1.1rem', fontWeight: 700, color: m.color }}>{m.value}</p>
          </div>
        ))}
      </div>

      {a.insight && (
        <p style={{ fontSize: '.875rem', color: 'var(--text-muted)', lineHeight: 1.7, marginBottom: '1.25rem', padding: '1rem', background: 'var(--surface-alt)', borderRadius: 8, borderLeft: '3px solid var(--primary)' }}>
          {a.insight}
        </p>
      )}

      {a.positions && (
        <div>
          <p style={{ fontSize: '.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '.5rem', textTransform: 'uppercase', letterSpacing: '.04em' }}>Positions</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.35rem' }}>
            {a.positions.map(p => (
              <div key={p.ticker} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '.875rem', padding: '.4rem 0', borderBottom: '1px solid var(--border)' }}>
                <span style={{ fontWeight: 600 }}>{p.ticker}</span>
                <span style={{ color: 'var(--text-muted)' }}>€{p.value.toLocaleString('de-DE', { maximumFractionDigits: 0 })}</span>
                <span style={{ color: p.gain_pct >= 0 ? '#059669' : '#dc2626', fontWeight: 600 }}>
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

const labelStyle: React.CSSProperties = { fontSize: '.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.04em' }
const inputStyle: React.CSSProperties = { padding: '.45rem .6rem', border: '1px solid var(--border)', borderRadius: 6, fontSize: '.875rem', outline: 'none', width: '100%' }
