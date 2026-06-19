import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { BarChart2 } from 'lucide-react'
import { Panel, SectionHeader, EmptyState } from '../primitives'
import { getStockChart, type ChartPoint } from '../../../services/api'
import { fmtMoneyExact, currencyLabel } from '../../../lib/format'

const PERIODS = ['1mo', '3mo', '6mo', '1y'] as const

export function PriceChart({ ticker }: { ticker: string }) {
  const [period, setPeriod] = useState<typeof PERIODS[number]>('3mo')
  const [data, setData] = useState<ChartPoint[]>([])
  const [currency, setCurrency] = useState('EUR')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    setLoading(true)
    getStockChart(ticker, period)
      .then(d => { if (active) { setData(d.points); setCurrency(d.currency) } })
      .catch(() => { if (active) setData([]) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [ticker, period])

  return (
    <Panel>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '.5rem', flexWrap: 'wrap' }}>
        {/* Währung kommt vom Backend (Heimatwährung), nicht hart EUR */}
        <SectionHeader title="Kursverlauf" description={currencyLabel(currency)} />
        <div style={{ display: 'flex', gap: '.3rem' }}>
          {PERIODS.map(p => (
            <button key={p} className="btn btn-outline" onClick={() => setPeriod(p)}
              style={{ fontSize: '.72rem', padding: '.25rem .55rem', background: period === p ? 'var(--brand)' : undefined, color: period === p ? '#fff' : undefined }}>
              {p}
            </button>
          ))}
        </div>
      </div>
      <div style={{ height: 240, marginTop: '.75rem' }}>
        {loading ? (
          <p style={{ textAlign: 'center', color: 'var(--text-3)', fontSize: '.8rem', paddingTop: '4rem' }}>Lädt…</p>
        ) : data.length === 0 ? (
          <EmptyState icon={BarChart2} title="Kein Chart verfügbar" description="Keine Kursdaten für diesen Zeitraum." />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--brand)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--brand)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--text-3)' }} minTickGap={40} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-3)' }} width={50} domain={['auto', 'auto']}
                tickFormatter={(v) => typeof v === 'number' ? fmtMoneyExact(v, currency) : String(v)} />
              <Tooltip formatter={(v) => typeof v === 'number' ? fmtMoneyExact(v, currency) : String(v)} />
              <Area type="monotone" dataKey="close" stroke="var(--brand)" strokeWidth={2} fill="url(#priceFill)" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Panel>
  )
}
