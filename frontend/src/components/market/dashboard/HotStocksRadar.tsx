// Hot-Stocks-Radar: 3 Mini-Spalten (Top Gainers / Top Losers / Highest Bull).
// Reine Präsentation — bekommt das fertige Tab-Ranking aus getHotStocks() als Props.
import { Link } from 'react-router-dom'
import { Panel, SectionHeader, Delta } from '../primitives'
import type { Tab, HotStockRow } from '../hot-stocks/hot-data'

type Tabs = Record<Tab, HotStockRow[]>

function Column({ title, rows, mode }: { title: string; rows: HotStockRow[]; mode: 'change' | 'bull' }) {
  return (
    <div style={{ minWidth: 0 }}>
      <p className="eyebrow" style={{ marginBottom: '.5rem' }}>{title}</p>
      {rows.length === 0 ? (
        <p style={{ fontSize: '.75rem', color: 'var(--text-3)' }}>—</p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '.45rem' }}>
          {rows.slice(0, 5).map(r => (
            <li key={r.ticker} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '.5rem' }}>
              <span style={{ fontWeight: 700, color: 'var(--brand)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.ticker}</span>
              {mode === 'change' ? (
                r.changePct != null
                  ? <Delta value={r.changePct} iconSize={10} style={{ fontSize: '.75rem' }} />
                  : <span style={{ fontSize: '.75rem', color: 'var(--text-3)' }}>—</span>
              ) : (
                <span className="tabular" style={{ fontSize: '.78rem', fontWeight: 700, color: 'var(--text)' }}>
                  {r.bull != null ? Math.round(r.bull) : '—'}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function HotStocksRadar({ tabs, loading }: { tabs: Tabs | null; loading: boolean }) {
  return (
    <Panel>
      <SectionHeader
        eyebrow="Hot Stocks"
        title="Markt-Radar"
        action={<Link to="/market/hot-stocks" className="btn btn-outline">Hot Stocks →</Link>}
      />
      {!tabs ? (
        <p style={{ marginTop: '1rem', fontSize: '.8rem', color: 'var(--text-3)' }}>
          {loading ? 'Lädt…' : 'Keine Daten.'}
        </p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '1.25rem', marginTop: '1rem' }}>
          <Column title="Top Gainers" rows={tabs.gainers} mode="change" />
          <Column title="Top Losers" rows={tabs.losers} mode="change" />
          <Column title="Highest Bull" rows={tabs.bull_high} mode="bull" />
        </div>
      )}
    </Panel>
  )
}
