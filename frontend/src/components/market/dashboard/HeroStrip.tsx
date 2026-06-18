// Hero-Strip: Begrüßung + Datum + Tape-Status und 4 Kennzahl-Kacheln.
// Reine Präsentation — nimmt fertige Werte als Props (kein Fetch, keine Berechnung).
import { MetricCard } from '../primitives'
import { fmtCurrency, fmtPrice } from '../../../lib/format'

export interface MarketQuote { price: number; change_pct: number }

/** Tageszeit-Begrüßung auf Deutsch (lokale Uhrzeit). */
function greeting(d = new Date()): string {
  const h = d.getHours()
  if (h < 11) return 'Guten Morgen'
  if (h < 18) return 'Guten Tag'
  return 'Guten Abend'
}

/**
 * Tape-Status aus der NYSE-Handelszeit (Mo–Fr 9:30–16:00 ET). Bewusst simpel
 * abgeleitet, kein Börsen-Kalender-Endpoint (Feiertage werden nicht erkannt).
 */
export function tapeStatus(now = new Date()): { open: boolean; label: string } {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(now)
  const wd = parts.find(p => p.type === 'weekday')?.value ?? ''
  const hour = Number(parts.find(p => p.type === 'hour')?.value ?? '0')
  const min = Number(parts.find(p => p.type === 'minute')?.value ?? '0')
  const isWeekday = !['Sat', 'Sun'].includes(wd)
  const mins = hour * 60 + min
  const open = isWeekday && mins >= 9 * 60 + 30 && mins < 16 * 60
  return { open, label: open ? 'Börse offen' : 'Börse geschlossen' }
}

export interface HeroStripProps {
  totalValue: number
  totalPnl: number
  totalPnlPct: number
  anyPnl: boolean
  sp?: MarketQuote
  vix?: MarketQuote
}

export function HeroStrip({ totalValue, totalPnl, totalPnlPct, anyPnl, sp, vix }: HeroStripProps) {
  const today = new Date().toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  const tape = tapeStatus()
  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: '.75rem', marginBottom: '1rem' }}>
        <h1 className="page-title" style={{ margin: 0 }}>{greeting()}</h1>
        <span style={{ color: 'var(--text-3)', fontSize: '.9rem' }}>{today}</span>
        <span
          className={`badge ${tape.open ? 'badge-teal' : 'badge-gray'}`}
          style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: '.4rem' }}
        >
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: tape.open ? 'var(--gain)' : 'var(--text-3)' }} />
          {tape.label}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '.75rem' }}>
        <MetricCard
          label="Depotwert"
          value={fmtCurrency(totalValue)}
          accent
        />
        <MetricCard
          label="Gesamt G/V"
          value={anyPnl ? `${totalPnl >= 0 ? '+' : ''}${fmtCurrency(totalPnl)}` : '—'}
          delta={anyPnl ? totalPnlPct : undefined}
          sub={anyPnl ? undefined : 'Stück + Ø-Kauf eintragen'}
        />
        <MetricCard
          label="S&P 500"
          value={sp ? fmtPrice(sp.price) : '—'}
          delta={sp ? sp.change_pct : undefined}
        />
        <MetricCard
          label="VIX"
          value={vix ? fmtPrice(vix.price) : '—'}
          delta={vix ? vix.change_pct : undefined}
        />
      </div>
    </div>
  )
}
