// Portfolio-Cockpit Panels — Metric-Strip, Performance (vs S&P 500), Allocation-Donut, Risk.
// Recharts + unsere Primitives/Tokens. Phase 2 des Market-Intelligence-Redesigns.
import { useState } from 'react'
import {
  Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Panel, SectionHeader, Delta, MetricCard, MiniStat, RiskBar } from './primitives'
import { fmtCurrency, fmtPct, fmtCurrencyExact } from '../../lib/format'
import type { Position, AllocationData, PortfolioAnalysis, PerfData } from '../../services/api'

const CHART_COLORS = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-4)', 'var(--chart-5)', 'var(--brand-mid)']
const PERIODS = ['1M', '3M', '6M', '1Y', 'All'] as const

export type PnlItem = {
  ticker: string
  hasQty: boolean
  price?: number
  change_pct?: number
  shares?: number
  avg_buy?: number
  investment: number
  cost: number
  value: number
  pnl: number
  pnlPct: number
  day: number
}

export type PnlStats = {
  items: PnlItem[]
  totalCost: number
  totalValue: number
  totalPnl: number
  totalPnlPct: number
  dayPnl: number
  dayPnlPct: number
  anyPnl: boolean
}

/**
 * Leitet P&L aus Positionen + Live-Kursen ab. Positionen mit Stück+Ø-Kauf
 * bekommen echte P&L; Positionen ohne fallen auf den Investmentbetrag zurück.
 * FX-Hinweis: Kurse kommen in Heimatwährung (USD bei US-Titeln) — die EUR-P&L
 * für US-Positionen ist daher noch eine Näherung (sauberer FX-Fix folgt).
 */
export function computePnl(
  positions: Position[],
  prices: Record<string, { price: number; change_pct: number }>,
): PnlStats {
  let totalCost = 0, totalValue = 0, dayPnl = 0, anyPnl = false
  const items: PnlItem[] = positions
    .filter(p => p.ticker)
    .map(p => {
      const px = prices[p.ticker]
      const hasQty = !!(p.shares && p.avg_buy)
      const live = !!(hasQty && px?.price)
      const cost = hasQty ? (p.shares ?? 0) * (p.avg_buy ?? 0) : p.investment
      const value = live ? (px!.price) * (p.shares ?? 0) : p.investment
      const pnl = live ? value - cost : 0
      const pnlPct = live && cost > 0 ? (pnl / cost) * 100 : 0
      const day = px?.price ? value * ((px.change_pct ?? 0) / 100) : 0
      if (live) anyPnl = true
      totalCost += cost; totalValue += value; dayPnl += day
      return { ...p, hasQty, price: px?.price, change_pct: px?.change_pct, cost, value, pnl, pnlPct, day }
    })
  const totalPnl = totalValue - totalCost
  const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0
  const dayPnlPct = totalValue > 0 ? (dayPnl / totalValue) * 100 : 0
  return { items, totalCost, totalValue, totalPnl, totalPnlPct, dayPnl, dayPnlPct, anyPnl }
}

/** Kennzahl-Strip oben im Cockpit. */
export function MetricStrip({ stats, analysis }: { stats: PnlStats; analysis: PortfolioAnalysis | null }) {
  const div = analysis ? Math.round((analysis.diversification_score ?? 0) * 100) : null
  const vol = analysis ? (analysis.annualized_volatility ?? 0) * 100 : null
  const sectors = analysis?.assets?.length ?? stats.items.length
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '.75rem', marginBottom: '1.25rem' }}>
      <MetricCard
        label="Depotwert"
        value={fmtCurrency(stats.totalValue)}
        delta={stats.anyPnl ? stats.dayPnlPct : undefined}
        sub={stats.anyPnl ? `${stats.dayPnl >= 0 ? '+' : ''}${fmtCurrency(stats.dayPnl)} heute` : 'Investiert'}
        accent
      />
      <MetricCard
        label="Gesamt G/V"
        value={stats.anyPnl ? `${stats.totalPnl >= 0 ? '+' : ''}${fmtCurrency(stats.totalPnl)}` : '—'}
        delta={stats.anyPnl ? stats.totalPnlPct : undefined}
        sub={stats.anyPnl ? `Einstand ${fmtCurrency(stats.totalCost)}` : 'Stück + Ø-Kauf eintragen'}
      />
      <MiniStat label="Positionen" value={String(stats.items.length)} sub={`${sectors} Werte`} />
      <MiniStat
        label="Diversifikation"
        value={div != null ? `${div}` : '—'}
        sub={div != null ? '/ 100' : 'Analyse starten'}
        tone={div != null ? (div >= 65 ? 'gain' : div >= 40 ? 'warn' : 'loss') : undefined}
      />
      <MiniStat
        label="Volatilität p.a."
        value={vol != null ? `${vol.toFixed(1).replace('.', ',')}%` : '—'}
        sub={vol != null ? (vol < 15 ? 'konservativ' : vol < 25 ? 'moderat' : 'aggressiv') : 'Analyse starten'}
        tone={vol != null ? (vol < 15 ? 'gain' : vol < 25 ? 'warn' : 'loss') : undefined}
      />
    </div>
  )
}

/** Performance-Kurve: aktuelle Allokation vs. S&P 500. */
export function PerformancePanel({
  data, period, onPeriod, loading,
}: {
  data: PerfData | null
  period: string
  onPeriod: (p: string) => void
  loading: boolean
}) {
  const hasData = !!data && data.series.length > 0
  return (
    <Panel>
      <SectionHeader
        eyebrow="Performance"
        title="Portfolio vs. S&P 500"
        description="Gewichteter Verlauf der aktuellen Allokation."
        action={
          <div style={{ display: 'inline-flex', border: '1px solid var(--border)', background: 'var(--surface-alt)', borderRadius: 'var(--radius-xs)', padding: 2, fontSize: '.7rem', fontWeight: 600 }}>
            {PERIODS.map(p => (
              <button
                key={p}
                onClick={() => onPeriod(p)}
                style={{
                  border: 'none', borderRadius: 4, padding: '.2rem .5rem', cursor: 'pointer',
                  background: period === p ? 'var(--surface-3)' : 'transparent',
                  color: period === p ? 'var(--text)' : 'var(--text-3)',
                }}
              >{p}</button>
            ))}
          </div>
        }
      />
      <div style={{ height: 256, marginTop: '1rem' }}>
        {loading ? (
          <div style={{ height: '100%', display: 'grid', placeItems: 'center', color: 'var(--text-3)', fontSize: '.8rem' }}>Lädt…</div>
        ) : !hasData ? (
          <div style={{ height: '100%', display: 'grid', placeItems: 'center', color: 'var(--text-3)', fontSize: '.8rem' }}>Keine Kursdaten verfügbar.</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data!.series} margin={{ top: 5, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="perfGrad" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="var(--brand)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--brand)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--hairline)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 10 }} axisLine={false} tickLine={false} minTickGap={48} />
              <YAxis tick={{ fill: 'var(--text-3)', fontSize: 10 }} axisLine={false} tickLine={false} width={52} tickFormatter={(v: number) => `${Math.round(v / 1000)}k €`} domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12, color: 'var(--text)' }}
                labelStyle={{ color: 'var(--text-3)' }}
                formatter={(v, name) => [fmtCurrencyExact(Number(v)), name === 'benchmark' ? 'S&P 500' : 'Portfolio']}
              />
              <Area type="monotone" dataKey="benchmark" stroke="var(--text-3)" strokeDasharray="3 3" strokeWidth={1.5} fill="none" />
              <Area type="monotone" dataKey="value" stroke="var(--brand)" strokeWidth={2} fill="url(#perfGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
      <div style={{ display: 'flex', gap: '1.25rem', marginTop: '.5rem', fontSize: '.72rem', color: 'var(--text-3)' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '.35rem' }}><span style={{ width: 14, height: 2, background: 'var(--brand)', display: 'inline-block' }} /> Portfolio</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '.35rem' }}><span style={{ width: 14, height: 0, borderTop: '2px dashed var(--text-3)', display: 'inline-block' }} /> S&P 500</span>
      </div>
    </Panel>
  )
}

type AllocDim = 'bySector' | 'byContinent' | 'byMarket' | 'byHolding'
const DIM_LABELS: Record<AllocDim, string> = { bySector: 'Sektor', byContinent: 'Kontinent', byMarket: 'Markt', byHolding: 'Position' }

/** Allocation-Donut mit Umschalter (Sektor/Kontinent/Markt/Position). */
export function AllocationDonut({ alloc }: { alloc: AllocationData }) {
  const [dim, setDim] = useState<AllocDim>('bySector')
  const slices = alloc[dim] ?? []
  return (
    <Panel>
      <SectionHeader
        eyebrow="Allocation"
        title={`Nach ${DIM_LABELS[dim]}`}
        action={
          <div style={{ display: 'inline-flex', border: '1px solid var(--border)', background: 'var(--surface-alt)', borderRadius: 'var(--radius-xs)', padding: 2, fontSize: '.68rem', fontWeight: 600 }}>
            {(Object.keys(DIM_LABELS) as AllocDim[]).map(d => (
              <button
                key={d}
                onClick={() => setDim(d)}
                style={{ border: 'none', borderRadius: 4, padding: '.2rem .45rem', cursor: 'pointer', background: dim === d ? 'var(--surface-3)' : 'transparent', color: dim === d ? 'var(--text)' : 'var(--text-3)' }}
              >{DIM_LABELS[d]}</button>
            ))}
          </div>
        }
      />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
        <div style={{ height: 168 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={slices} dataKey="value" nameKey="label" innerRadius={42} outerRadius={74} paddingAngle={2} stroke="var(--surface)">
                {slices.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
              </Pie>
              <Tooltip
                contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12, color: 'var(--text)' }}
                formatter={(v, label) => [`${fmtCurrency(Number(v))} · ${((Number(v) / (alloc.total || 1)) * 100).toFixed(1).replace('.', ',')}%`, label]}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '.4rem', fontSize: '.78rem' }}>
          {slices.slice(0, 6).map((s, i) => (
            <li key={s.label} style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
              <span style={{ width: 9, height: 9, borderRadius: 2, flexShrink: 0, background: CHART_COLORS[i % CHART_COLORS.length] }} />
              <span style={{ color: 'var(--text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.label}</span>
              <span className="tabular" style={{ marginLeft: 'auto', color: 'var(--text)', fontWeight: 600 }}>{s.pct.toFixed(1).replace('.', ',')}%</span>
            </li>
          ))}
        </ul>
      </div>
    </Panel>
  )
}

/** Risiko-Panel aus den Analyse-Kennzahlen. */
export function RiskPanel({ analysis, stats }: { analysis: PortfolioAnalysis | null; stats: PnlStats }) {
  const largest = analysis ? (analysis.largest_position ?? 0) * 100 : (stats.items.length ? Math.max(...stats.items.map(i => (i.value / (stats.totalValue || 1)) * 100)) : 0)
  const vol = analysis ? (analysis.annualized_volatility ?? 0) * 100 : 0
  const div = analysis ? (analysis.diversification_score ?? 0) * 100 : 0
  const rows = [
    { l: 'Konzentration (größte Position)', v: largest, note: `${largest.toFixed(1).replace('.', ',')}%` },
    { l: 'Volatilität (annualisiert)', v: Math.min(100, vol * 2), note: `${vol.toFixed(1).replace('.', ',')}%` },
    { l: 'Diversifikations-Lücke', v: 100 - div, note: `${div.toFixed(0)}/100 div.` },
  ]
  return (
    <Panel>
      <SectionHeader eyebrow="Risiko" title="Diversifikation & Exposure" />
      {!analysis ? (
        <p style={{ marginTop: '1rem', fontSize: '.8rem', color: 'var(--text-3)' }}>„Analyze" starten für Volatilität & Diversifikation.</p>
      ) : (
        <ul style={{ listStyle: 'none', margin: '1rem 0 0', padding: 0, display: 'flex', flexDirection: 'column', gap: '.9rem' }}>
          {rows.map(r => <li key={r.l}><RiskBar label={r.l} value={r.v} note={r.note} /></li>)}
        </ul>
      )}
    </Panel>
  )
}

/** Reiche Holdings-Tabelle mit Kurs, Wert, P&L, Gewicht. */
export function HoldingsTable({ stats }: { stats: PnlStats }) {
  if (!stats.items.length) return null
  const head = ['Ticker', 'Stück', 'Ø Kauf', 'Kurs', 'Wert', 'Tag', 'G/V', 'Gewicht']
  return (
    <Panel padded={false} style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', padding: '.85rem 1.25rem' }}>
        <h3 style={{ fontSize: '.9rem', fontWeight: 700 }}>Holdings</h3>
        <span className="eyebrow">{stats.items.length} Positionen · {fmtCurrency(stats.totalValue)}</span>
      </div>
      <div className="table-scroll">
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 640 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              {head.map((h, i) => (
                <th key={h} style={{ padding: '.5rem .75rem', textAlign: i > 0 ? 'right' : 'left', fontSize: '.62rem', fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--text-3)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stats.items.map(it => {
              const weight = stats.totalValue > 0 ? (it.value / stats.totalValue) * 100 : 0
              return (
                <tr key={it.ticker} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '.6rem .75rem', fontWeight: 700, color: 'var(--brand)' }}>{it.ticker}</td>
                  <td className="tabular" style={{ padding: '.6rem .75rem', textAlign: 'right', color: 'var(--text-2)' }}>{it.hasQty ? it.shares : '—'}</td>
                  <td className="tabular" style={{ padding: '.6rem .75rem', textAlign: 'right', color: 'var(--text-2)' }}>{it.hasQty ? fmtCurrencyExact(it.avg_buy ?? 0) : '—'}</td>
                  <td className="tabular" style={{ padding: '.6rem .75rem', textAlign: 'right', fontWeight: 600 }}>{it.price ? it.price.toFixed(2).replace('.', ',') : '···'}</td>
                  <td className="tabular" style={{ padding: '.6rem .75rem', textAlign: 'right' }}>{fmtCurrency(it.value)}</td>
                  <td style={{ padding: '.6rem .75rem', textAlign: 'right' }}>{it.change_pct != null ? <Delta value={it.change_pct} iconSize={9} style={{ justifyContent: 'flex-end', fontSize: '.75rem' }} /> : '—'}</td>
                  <td className="tabular" style={{ padding: '.6rem .75rem', textAlign: 'right', fontWeight: 700, color: it.hasQty && it.price ? (it.pnl >= 0 ? 'var(--gain)' : 'var(--loss)') : 'var(--text-3)' }}>
                    {it.hasQty && it.price ? `${it.pnl >= 0 ? '+' : ''}${fmtCurrency(it.pnl)}` : '—'}
                    {it.hasQty && it.price ? <span style={{ display: 'block', fontSize: '.65rem', fontWeight: 600, opacity: .8 }}>{fmtPct(it.pnlPct)}</span> : null}
                  </td>
                  <td style={{ padding: '.6rem .75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', justifyContent: 'flex-end' }}>
                      <div style={{ width: 48, height: 4, borderRadius: 999, background: 'var(--surface-3)', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${weight}%`, background: 'var(--brand)' }} />
                      </div>
                      <span className="tabular" style={{ fontSize: '.7rem', color: 'var(--text-3)' }}>{weight.toFixed(1).replace('.', ',')}%</span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
