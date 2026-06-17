import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Panel, SectionHeader, Delta } from '../primitives'
import { ScoreBadge } from '../score'
import { getStockPeers, type PeerRow } from '../../../services/api'
import { sortPeers } from '../../../lib/analyzer'
import { fmtCurrencyExact } from '../../../lib/format'

export function PeerTable({ ticker }: { ticker: string }) {
  const navigate = useNavigate()
  const [peers, setPeers] = useState<PeerRow[] | null>(null)

  useEffect(() => {
    let active = true
    getStockPeers(ticker)
      .then(d => { if (active) setPeers(sortPeers(d)) })
      .catch(() => { if (active) setPeers([]) })
    return () => { active = false }
  }, [ticker])

  if (peers === null) return null
  if (peers.length === 0) return null

  return (
    <Panel>
      {/* SectionHeader has no `sub` prop — use description for sector label */}
      <SectionHeader title="Peers" description="gleicher Sektor" />
      <div className="table-scroll" style={{ marginTop: '.5rem' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.82rem' }}>
          <thead>
            <tr style={{ color: 'var(--text-3)', textAlign: 'left' }}>
              <th style={{ padding: '.4rem .5rem' }}>Titel</th>
              <th style={{ padding: '.4rem .5rem' }}>Score</th>
              <th style={{ padding: '.4rem .5rem', textAlign: 'right' }}>Preis</th>
              <th style={{ padding: '.4rem .5rem', textAlign: 'right' }}>Δ Tag</th>
            </tr>
          </thead>
          <tbody>
            {peers.map(p => (
              <tr key={p.ticker} style={{ cursor: 'pointer', borderTop: '1px solid var(--border)' }}
                onClick={() => navigate(`/market/analyzer/${p.ticker}`)}>
                <td style={{ padding: '.5rem' }}>
                  <span style={{ fontWeight: 700 }}>{p.ticker}</span>
                  <span style={{ color: 'var(--text-3)', marginLeft: '.4rem' }}>{p.name !== p.ticker ? p.name : ''}</span>
                </td>
                <td style={{ padding: '.5rem' }}><ScoreBadge score={p.bull_score} /></td>
                <td className="tabular" style={{ padding: '.5rem', textAlign: 'right' }}>{p.price != null ? fmtCurrencyExact(p.price) : 'n/a'}</td>
                <td style={{ padding: '.5rem', textAlign: 'right' }}>{p.change_pct != null ? <Delta value={p.change_pct} style={{ justifyContent: 'flex-end' }} /> : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
