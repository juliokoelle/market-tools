import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Panel, SectionHeader } from '../primitives'
import { getStockFinancials, type FinancialsRow } from '../../../services/api'
import { financialsToBars } from '../../../lib/analyzer'
import { currencyLabel } from '../../../lib/format'

export function FinancialsBars({ ticker }: { ticker: string }) {
  const [rows, setRows] = useState<FinancialsRow[] | null>(null)
  const [currency, setCurrency] = useState('EUR')

  useEffect(() => {
    let active = true
    getStockFinancials(ticker)
      .then(d => { if (active) { setRows(d.rows); setCurrency(d.currency ?? 'EUR') } })
      .catch(() => { if (active) setRows([]) })
    return () => { active = false }
  }, [ticker])

  if (rows === null) return null            // lädt: nichts rendern
  if (rows.length === 0) return null         // keine Daten: Panel ausblenden (nicht mocken)

  const data = financialsToBars(rows)
  return (
    <Panel>
      {/* Währung kommt vom Backend (Heimatwährung des Unternehmens) */}
      <SectionHeader title="Financials" description={`Mio. ${currencyLabel(currency)}`} />
      <div style={{ height: 240, marginTop: '.75rem' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="year" tick={{ fontSize: 11, fill: 'var(--text-3)' }} />
            <YAxis tick={{ fontSize: 10, fill: 'var(--text-3)' }} width={50} />
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="Revenue" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
            <Bar dataKey="EBITDA" fill="var(--chart-2)" radius={[3, 3, 0, 0]} />
            <Bar dataKey="Net Income" fill="var(--chart-3)" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  )
}
