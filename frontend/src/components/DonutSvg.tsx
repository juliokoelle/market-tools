export interface DonutSlice { label: string; value: number; pct: number }

// Teal-led palette tuned to the app's light theme
const PALETTE = [
  'var(--teal)', '#3b82f6', '#22c55e', '#f59e0b', '#ec4899', '#8b5cf6',
  '#06b6d4', '#ef4444', '#84cc16', '#a855f7', '#14b8a6', '#64748b',
]

export function DonutSvg({
  slices, size = 188, thickness = 24,
}: { slices: DonutSlice[]; size?: number; thickness?: number }) {
  const clean = slices.filter(s => s.value > 0)
  const total = clean.reduce((s, x) => s + x.value, 0) || 1
  const r = (size - thickness) / 2
  const cx = size / 2
  const cy = size / 2

  let acc = 0
  const arcs = clean.map((s, i) => {
    const frac = s.value / total
    const a0 = acc * 2 * Math.PI - Math.PI / 2
    acc += frac
    const a1 = acc * 2 * Math.PI - Math.PI / 2
    const large = frac > 0.5 ? 1 : 0
    const x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0)
    const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1)
    return {
      d: `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`,
      color: PALETTE[i % PALETTE.length],
      label: s.label,
      pct: s.pct,
    }
  })

  return (
    <div style={{ display: 'flex', gap: '1.1rem', alignItems: 'center', flexWrap: 'wrap' }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ flexShrink: 0 }}>
        {clean.length === 1 ? (
          <circle cx={cx} cy={cy} r={r} fill="none" stroke={PALETTE[0]} strokeWidth={thickness} />
        ) : (
          arcs.map((a, i) => (
            <path key={i} d={a.d} fill="none" stroke={a.color} strokeWidth={thickness} strokeLinecap="butt" />
          ))
        )}
      </svg>
      <ul style={{
        listStyle: 'none', margin: 0, padding: 0, display: 'flex',
        flexDirection: 'column', gap: '.3rem', fontSize: '.78rem', minWidth: 132, flex: 1,
      }}>
        {arcs.map((a, i) => (
          <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: a.color, flexShrink: 0 }} />
            <span style={{ color: 'var(--text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.label}</span>
            <span style={{ marginLeft: 'auto', fontWeight: 700, color: 'var(--text)' }}>{a.pct.toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
