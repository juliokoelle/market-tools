// Portfolio-Snapshot: Top-5 Positionen nach Wert (Ticker, Wert EUR, Gewicht %).
// Reine Präsentation — bekommt fertige Zeilen aus topPositions() als Props.
import { Link } from 'react-router-dom'
import { Panel, SectionHeader } from '../primitives'
import { fmtCurrency } from '../../../lib/format'
import type { SnapshotRow } from './dashboard-data'

export function PortfolioSnapshot({ rows, loading }: { rows: SnapshotRow[]; loading: boolean }) {
  return (
    <Panel>
      <SectionHeader
        eyebrow="Portfolio"
        title="Top-Positionen"
        action={<Link to="/market/portfolio" className="btn btn-outline">Portfolio →</Link>}
      />
      {rows.length === 0 ? (
        <p style={{ marginTop: '1rem', fontSize: '.8rem', color: 'var(--text-3)' }}>
          {loading ? 'Lädt…' : 'Keine Positionen.'}
        </p>
      ) : (
        <ul style={{ listStyle: 'none', margin: '1rem 0 0', padding: 0, display: 'flex', flexDirection: 'column', gap: '.6rem' }}>
          {rows.map(r => (
            <li key={r.ticker} style={{ display: 'flex', alignItems: 'center', gap: '.75rem' }}>
              <span style={{ fontWeight: 700, color: 'var(--brand)', minWidth: 56 }}>{r.ticker}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ height: 4, borderRadius: 999, background: 'var(--surface-3)', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${Math.max(0, Math.min(100, r.weight))}%`, background: 'var(--brand)' }} />
                </div>
              </div>
              <span className="tabular" style={{ fontSize: '.7rem', color: 'var(--text-3)', minWidth: 44, textAlign: 'right' }}>
                {r.weight.toFixed(1).replace('.', ',')}%
              </span>
              <span className="tabular" style={{ fontWeight: 600, color: 'var(--text)', minWidth: 80, textAlign: 'right' }}>
                {fmtCurrency(r.value)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}
