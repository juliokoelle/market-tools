import { Panel, MetricCard } from '../primitives'
import { ScoreGauge } from '../score'
import type { StockDetail } from '../../../services/api'

export function ScorePanel({ detail }: { detail: StockDetail }) {
  const c = detail.components
  return (
    <Panel>
      <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <ScoreGauge score={detail.bull_score} label="Bull Score" sublabel="0–100" size={130} />
        <div style={{ flex: 1, minWidth: 240, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '.6rem' }}>
          <MetricCard label="Momentum" value={String(Math.round(c.momentum))} />
          <MetricCard label="Sentiment" value={String(Math.round(c.sentiment))} />
          <MetricCard label="Valuation" value={String(Math.round(c.valuation))} />
          <MetricCard label="Analyst" value={String(Math.round(c.analyst))} />
        </div>
      </div>
    </Panel>
  )
}
