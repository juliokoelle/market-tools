// Market-UI Primitives — Lovable-Bauweise, in unserem Look (CSS-Variablen, Light/Dark).
// Bewusst Inline-Styles + var(--…), konsistent mit dem Rest der Codebase (kein Tailwind).
import type { CSSProperties, ReactNode, ComponentType } from 'react'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { fmtPct } from '../../lib/format'

/** Karten-Container. `padded={false}` für Tabellen/Listen ohne Innenabstand. */
export function Panel({
  children,
  padded = true,
  style,
  className,
}: {
  children: ReactNode
  padded?: boolean
  style?: CSSProperties
  className?: string
}) {
  return (
    <div
      className={className}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        boxShadow: 'var(--shadow-sm)',
        padding: padded ? '1.25rem' : 0,
        ...style,
      }}
    >
      {children}
    </div>
  )
}

/** Abschnitts-Kopf mit Eyebrow, Titel, Beschreibung und optionaler Aktion rechts. */
export function SectionHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', justifyContent: 'space-between', gap: '.75rem' }}>
      <div style={{ minWidth: 0 }}>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2 style={{ marginTop: eyebrow ? '.25rem' : 0, fontSize: '1.05rem', fontWeight: 700, letterSpacing: '-.3px', color: 'var(--text)' }}>{title}</h2>
        {description && <p style={{ marginTop: '.25rem', fontSize: '.8rem', color: 'var(--text-3)' }}>{description}</p>}
      </div>
      {action && <div style={{ flexShrink: 0 }}>{action}</div>}
    </div>
  )
}

/** Prozentuale Veränderung, grün/rot mit Richtungspfeil. */
export function Delta({
  value,
  iconSize = 12,
  showIcon = true,
  style,
}: {
  value: number
  iconSize?: number
  showIcon?: boolean
  style?: CSSProperties
}) {
  const up = value >= 0
  return (
    <span
      className="tabular"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '.2rem',
        fontSize: '.8rem',
        fontWeight: 600,
        color: up ? 'var(--gain)' : 'var(--loss)',
        ...style,
      }}
    >
      {showIcon && (up ? <ArrowUp size={iconSize} strokeWidth={2.5} /> : <ArrowDown size={iconSize} strokeWidth={2.5} />)}
      {fmtPct(value)}
    </span>
  )
}

/** Mini-Trendlinie aus Zahlenreihe (SVG, Gradient-Füllung). */
export function Sparkline({
  values,
  width = 96,
  height = 28,
  positive,
}: {
  values: number[]
  width?: number
  height?: number
  positive?: boolean
}) {
  if (!values.length) return null
  const up = positive ?? values[values.length - 1] >= values[0]
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const step = width / (values.length - 1 || 1)
  const points = values.map((v, i) => `${i * step},${height - ((v - min) / range) * height}`).join(' ')
  const color = up ? 'var(--gain)' : 'var(--loss)'
  const gradId = `spark-${up ? 'u' : 'd'}-${values.length}-${Math.round(values[0])}`
  return (
    <svg width={width} height={height} style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.3} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
      <polygon points={`0,${height} ${points} ${width},${height}`} fill={`url(#${gradId})`} />
    </svg>
  )
}

/** Große Kennzahl-Kachel mit Delta + Subtext. `accent` für Hervorhebung. */
export function MetricCard({
  label,
  value,
  delta,
  sub,
  accent,
}: {
  label: string
  value: string
  delta?: number
  sub?: string
  accent?: boolean
}) {
  return (
    <Panel style={accent ? { position: 'relative', overflow: 'hidden', background: 'var(--brand-soft)' } : undefined}>
      <p className="eyebrow">{label}</p>
      <p className="tabular" style={{ marginTop: '.5rem', fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-.6px', color: 'var(--text)', lineHeight: 1 }}>{value}</p>
      {(delta !== undefined || sub) && (
        <div style={{ marginTop: '.5rem', display: 'flex', alignItems: 'center', gap: '.5rem', fontSize: '.75rem', flexWrap: 'wrap' }}>
          {delta !== undefined && <Delta value={delta} iconSize={11} />}
          {sub && <span style={{ color: 'var(--text-3)' }}>{sub}</span>}
        </div>
      )}
    </Panel>
  )
}

/** Kompakte Kennzahl. Optionaler Farbton für den Wert. */
export function MiniStat({
  label,
  value,
  sub,
  tone,
}: {
  label: string
  value: string
  sub?: string
  tone?: 'gain' | 'warn' | 'loss'
}) {
  const color = tone === 'gain' ? 'var(--gain)' : tone === 'warn' ? 'var(--warn)' : tone === 'loss' ? 'var(--loss)' : 'var(--text)'
  return (
    <Panel>
      <p className="eyebrow">{label}</p>
      <p className="tabular" style={{ marginTop: '.5rem', fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-.5px', color }}>{value}</p>
      {sub && <p style={{ marginTop: '.25rem', fontSize: '.75rem', color: 'var(--text-3)' }}>{sub}</p>}
    </Panel>
  )
}

/** Risiko-Balken 0–100 (grün/gelb/rot je nach Höhe) mit Label + Notiz. */
export function RiskBar({ label, value, note }: { label: string; value: number; note?: string }) {
  const color = value > 65 ? 'var(--loss)' : value > 45 ? 'var(--warn)' : 'var(--gain)'
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '.78rem' }}>
        <span style={{ color: 'var(--text-2)' }}>{label}</span>
        {note && <span className="tabular" style={{ color: 'var(--text)' }}>{note}</span>}
      </div>
      <div style={{ marginTop: '.4rem', height: 6, borderRadius: 999, background: 'var(--surface-3)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${Math.max(0, Math.min(100, value))}%`, borderRadius: 999, background: color, transition: 'width .4s var(--ease-out)' }} />
      </div>
    </div>
  )
}

/** Leerzustand mit Icon, Titel, Beschreibung. */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: ComponentType<{ size?: number }>
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '.75rem', borderRadius: 'var(--radius)', border: '1px dashed var(--border)', background: 'var(--surface-alt)', padding: '2.5rem 1.5rem', textAlign: 'center' }}>
      <div style={{ display: 'grid', placeItems: 'center', width: 40, height: 40, borderRadius: 'var(--radius-sm)', background: 'var(--surface-3)', color: 'var(--text-3)' }}>
        <Icon size={20} />
      </div>
      <div>
        <p style={{ fontSize: '.85rem', fontWeight: 600, color: 'var(--text)' }}>{title}</p>
        <p style={{ marginTop: '.25rem', maxWidth: 360, fontSize: '.75rem', color: 'var(--text-3)' }}>{description}</p>
      </div>
      {action}
    </div>
  )
}
