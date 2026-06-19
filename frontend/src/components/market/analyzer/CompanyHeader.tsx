import { useNavigate } from 'react-router-dom'
import { Panel, Delta } from '../primitives'
import { fmtMoneyExact, fmtCompact, fmtNumber, currencyLabel } from '../../../lib/format'
import { range52Position, fmtRelVolume } from '../../../lib/analyzer'
import type { StockDetail } from '../../../services/api'

function initials(name: string) {
  return name.split(/\s+/).slice(0, 2).map(w => w[0] ?? '').join('').toUpperCase()
}

export function CompanyHeader({ detail, onWatch, onAddPortfolio }: {
  detail: StockDetail
  onWatch?: () => void
  onAddPortfolio?: () => void
}) {
  const navigate = useNavigate()
  const cur = detail.currency ?? 'EUR'
  const pos = detail.week_52_low > 0 && detail.week_52_high > 0
    ? range52Position(detail.week_52_low, detail.week_52_high, detail.price) : 0
  return (
    <Panel>
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div style={{ width: 52, height: 52, borderRadius: 12, background: 'var(--brand-soft)', color: 'var(--brand)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '1.1rem', flexShrink: 0 }}>
          {initials(detail.name)}
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <h1 style={{ fontSize: '1.3rem', fontWeight: 800, margin: 0 }}>{detail.name}</h1>
          <p style={{ color: 'var(--text-3)', fontSize: '.8rem', margin: '.15rem 0 0' }}>
            {detail.ticker}{detail.sector ? ` · ${detail.sector}` : ''}
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <p className="tabular" style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0 }}>{fmtMoneyExact(detail.price, cur)}</p>
          <Delta value={detail.change_pct} style={{ justifyContent: 'flex-end' }} />
        </div>
      </div>

      <div style={{ marginTop: '1rem', display: 'flex', gap: '1.25rem', flexWrap: 'wrap', fontSize: '.8rem' }}>
        <Stat label="Market Cap" value={detail.market_cap ? `${fmtCompact(detail.market_cap)} ${currencyLabel(cur)}` : '—'} />
        <Stat label="Rel. Volumen" value={fmtRelVolume(detail.rel_volume)} />
        <Stat label="Beta" value={detail.beta != null ? fmtNumber(detail.beta, 2) : '—'} />
        <Stat label="P/E" value={detail.pe_ratio != null ? fmtNumber(detail.pe_ratio, 1) : '—'} />
      </div>

      {detail.week_52_low > 0 && detail.week_52_high > 0 ? (
        <div style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '.7rem', color: 'var(--text-3)' }}>
            <span>{fmtMoneyExact(detail.week_52_low, cur)}</span>
            <span>52-Wochen-Spanne</span>
            <span>{fmtMoneyExact(detail.week_52_high, cur)}</span>
          </div>
          <div style={{ marginTop: '.35rem', height: 6, borderRadius: 999, background: 'var(--surface-3)', position: 'relative' }}>
            <div style={{ position: 'absolute', left: `${pos}%`, top: -2, width: 10, height: 10, borderRadius: '50%', background: 'var(--brand)', transform: 'translateX(-50%)' }} />
          </div>
        </div>
      ) : null}

      <div style={{ marginTop: '1rem', display: 'flex', gap: '.5rem', flexWrap: 'wrap' }}>
        {onWatch && <button className="btn btn-outline" style={{ fontSize: '.8rem' }} onClick={onWatch}>+ Watchlist</button>}
        {onAddPortfolio && <button className="btn btn-outline" style={{ fontSize: '.8rem' }} onClick={onAddPortfolio}>+ Portfolio</button>}
        <a className="btn btn-outline" style={{ fontSize: '.8rem', textDecoration: 'none' }} href={`https://finance.yahoo.com/quote/${encodeURIComponent(detail.ticker)}`} target="_blank" rel="noopener noreferrer">Yahoo ↗</a>
        <button className="btn btn-outline" style={{ fontSize: '.8rem' }} onClick={() => navigate('/market/analyzer')}>← Zurück</button>
      </div>
    </Panel>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="eyebrow" style={{ margin: 0 }}>{label}</p>
      <p className="tabular" style={{ margin: '.15rem 0 0', fontWeight: 700 }}>{value}</p>
    </div>
  )
}
