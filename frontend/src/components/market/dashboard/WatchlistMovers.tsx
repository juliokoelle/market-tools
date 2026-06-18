// Watchlist-Movers: größte absolute Tagesbewegungen der Watchlist (Top-5).
// Reine Präsentation — bekommt die fertigen Zeilen aus topMovers() als Props.
import { Link } from 'react-router-dom'
import { Panel, SectionHeader, Delta } from '../primitives'
import type { StockDetail } from '../../../services/api'

export function WatchlistMovers({ rows, loading }: { rows: StockDetail[]; loading: boolean }) {
  return (
    <Panel>
      <SectionHeader
        eyebrow="Watchlist"
        title="Top-Mover"
        action={<Link to="/market/analyzer" className="btn btn-outline">Analyzer →</Link>}
      />
      {rows.length === 0 ? (
        <p style={{ marginTop: '1rem', fontSize: '.8rem', color: 'var(--text-3)' }}>
          {loading ? 'Lädt…' : 'Keine Watchlist-Daten.'}
        </p>
      ) : (
        <ul style={{ listStyle: 'none', margin: '1rem 0 0', padding: 0, display: 'flex', flexDirection: 'column', gap: '.6rem' }}>
          {rows.map(s => (
            <li key={s.ticker} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '.5rem' }}>
              <div style={{ minWidth: 0 }}>
                <p style={{ fontWeight: 700, color: 'var(--brand)' }}>{s.ticker}</p>
                <p style={{ fontSize: '.72rem', color: 'var(--text-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</p>
              </div>
              <Delta value={s.change_pct} iconSize={11} style={{ fontSize: '.8rem' }} />
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}
