// Score-Darstellung — Badge + Ring-Gauge. Ton: <45 rot, 45–69 gelb, ≥70 grün.
import type { CSSProperties } from 'react'
import { scoreTone } from '../../lib/format'

function toneColor(score: number) {
  const t = scoreTone(score)
  return t === 'high' ? 'var(--gain)' : t === 'mid' ? 'var(--warn)' : 'var(--loss)'
}

/** Kompaktes Score-Chip mit optionalem Kürzel (z.B. "B" für Bull). */
export function ScoreBadge({ score, label, style }: { score: number; label?: string; style?: CSSProperties }) {
  const color = toneColor(score)
  return (
    <span
      className="tabular"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '.3rem',
        borderRadius: 'var(--radius-xs)',
        border: `1px solid color-mix(in srgb, ${color} 35%, transparent)`,
        background: `color-mix(in srgb, ${color} 14%, transparent)`,
        color,
        padding: '.1rem .4rem',
        fontSize: '.7rem',
        fontWeight: 700,
        ...style,
      }}
    >
      {label && <span style={{ opacity: 0.7 }}>{label}</span>}
      {Math.round(score)}
    </span>
  )
}

/** Ring-Gauge 0–100 mit Zentralwert + Label. */
export function ScoreGauge({
  score,
  label,
  size = 120,
  sublabel,
}: {
  score: number
  label: string
  size?: number
  sublabel?: string
}) {
  const color = toneColor(score)
  const r = (size - 16) / 2
  const c = 2 * Math.PI * r
  const filled = (Math.max(0, Math.min(100, score)) / 100) * c
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '.5rem' }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
          <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--surface-3)" strokeWidth={8} fill="none" />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            stroke={color}
            strokeWidth={8}
            strokeLinecap="round"
            fill="none"
            strokeDasharray={`${filled} ${c}`}
            style={{ transition: 'stroke-dasharray .6s cubic-bezier(.2,.7,.2,1)' }}
          />
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
          <span className="tabular" style={{ fontSize: size >= 130 ? '1.7rem' : '1.4rem', fontWeight: 800, color }}>{Math.round(score)}</span>
          {sublabel && <span style={{ fontSize: '.6rem', letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-3)' }}>{sublabel}</span>}
        </div>
      </div>
      <p className="eyebrow" style={{ color: 'var(--text-2)' }}>{label}</p>
    </div>
  )
}
