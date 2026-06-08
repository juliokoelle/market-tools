import { useState, useMemo } from 'react'

type ActivityType = 'run' | 'bike' | 'swim' | 'gym' | 'football' | 'paddle' | 'other'

interface TrainingEntry {
  id: string
  date: string       // YYYY-MM-DD
  type: ActivityType
  duration?: number  // minutes
  distance?: number  // km
  notes?: string
}

const ACTIVITIES: { type: ActivityType; emoji: string; label: string; ironman: boolean }[] = [
  { type: 'run',      emoji: '🏃', label: 'Laufen',    ironman: true  },
  { type: 'bike',     emoji: '🚴', label: 'Radfahren', ironman: true  },
  { type: 'swim',     emoji: '🏊', label: 'Schwimmen', ironman: true  },
  { type: 'gym',      emoji: '🏋️', label: 'Gym',       ironman: false },
  { type: 'football', emoji: '⚽', label: 'Fußball',   ironman: false },
  { type: 'paddle',   emoji: '🏓', label: 'Paddle',    ironman: false },
  { type: 'other',    emoji: '🧘', label: 'Anderes',   ironman: false },
]

const LOG_KEY = 'jk_training_log'

function todayStr() { return new Date().toISOString().slice(0, 10) }

function loadLog(): TrainingEntry[] {
  try { return JSON.parse(localStorage.getItem(LOG_KEY) ?? '[]') } catch { return [] }
}

function saveLog(entries: TrainingEntry[]) {
  localStorage.setItem(LOG_KEY, JSON.stringify(entries))
}

function getLast90Days(): string[] {
  const days: string[] = []
  for (let i = 89; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    days.push(d.toISOString().slice(0, 10))
  }
  return days
}

function activityColor(types: ActivityType[]): string {
  if (!types.length) return 'var(--border-soft)'
  if (types.some(t => ['run', 'bike', 'swim'].includes(t))) return 'rgba(22,163,74,.75)'
  if (types.includes('gym')) return 'rgba(139,26,26,.7)'
  return 'rgba(59,130,246,.6)'
}

function formatDuration(min: number) {
  if (min < 60) return `${min}min`
  return `${Math.floor(min / 60)}h${min % 60 ? ` ${min % 60}min` : ''}`
}

function dateLabel(date: string) {
  return new Date(date + 'T12:00:00').toLocaleDateString('de-DE', { weekday: 'short', day: 'numeric', month: 'short' })
}

interface LogModalProps {
  preselected: ActivityType | null
  onSave: (entry: Omit<TrainingEntry, 'id'>) => void
  onClose: () => void
}

function LogModal({ preselected, onSave, onClose }: LogModalProps) {
  const [type, setType] = useState<ActivityType>(preselected ?? 'run')
  const [duration, setDuration] = useState('')
  const [distance, setDistance] = useState('')
  const [notes, setNotes] = useState('')
  const [date, setDate] = useState(todayStr())

  function submit() {
    onSave({
      date,
      type,
      duration: duration ? parseInt(duration) : undefined,
      distance: distance ? parseFloat(distance.replace(',', '.')) : undefined,
      notes: notes.trim() || undefined,
    })
    onClose()
  }

  const showDistance = ['run', 'bike', 'swim'].includes(type)

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}
      onClick={onClose}
    >
      <div className="card" style={{ width: '100%', maxWidth: 420 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Workout loggen</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.3rem', color: 'var(--text-3)', cursor: 'pointer' }}>×</button>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.4rem', marginBottom: '1.1rem' }}>
          {ACTIVITIES.map(a => (
            <button
              key={a.type}
              onClick={() => setType(a.type)}
              style={{
                padding: '.35rem .7rem', borderRadius: 20, fontSize: '.8rem', fontWeight: 600,
                border: `2px solid ${type === a.type ? 'var(--teal)' : 'var(--border)'}`,
                background: type === a.type ? 'var(--teal-light)' : 'transparent',
                color: type === a.type ? 'var(--teal)' : 'var(--text-2)',
                cursor: 'pointer',
              }}
            >
              {a.emoji} {a.label}
            </button>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '.75rem', marginBottom: '1rem' }}>
          <div>
            <label style={labelSt}>Datum</label>
            <input type="date" value={date} onChange={e => setDate(e.target.value)} style={inputSt} />
          </div>
          <div>
            <label style={labelSt}>Dauer (min)</label>
            <input type="number" value={duration} onChange={e => setDuration(e.target.value)} placeholder="z.B. 45" style={inputSt} />
          </div>
          {showDistance && (
            <div>
              <label style={labelSt}>Distanz (km)</label>
              <input type="number" step="0.1" value={distance} onChange={e => setDistance(e.target.value)} placeholder="z.B. 10" style={inputSt} />
            </div>
          )}
          <div style={{ gridColumn: showDistance ? 'auto' : '1 / -1' }}>
            <label style={labelSt}>Notizen</label>
            <input type="text" value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional…" style={inputSt} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '.75rem' }}>
          <button onClick={submit} className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }}>Speichern</button>
          <button onClick={onClose} className="btn btn-outline" style={{ flex: 1, justifyContent: 'center' }}>Abbrechen</button>
        </div>
      </div>
    </div>
  )
}

export default function Training() {
  const [log, setLog] = useState<TrainingEntry[]>(loadLog)
  const [modal, setModal] = useState<{ open: boolean; preselected: ActivityType | null }>({ open: false, preselected: null })

  function openModal(type: ActivityType | null = null) {
    setModal({ open: true, preselected: type })
  }

  function addEntry(entry: Omit<TrainingEntry, 'id'>) {
    const newLog = [{ ...entry, id: crypto.randomUUID() }, ...log].sort((a, b) => b.date.localeCompare(a.date))
    setLog(newLog)
    saveLog(newLog)
  }

  function removeEntry(id: string) {
    const newLog = log.filter(e => e.id !== id)
    setLog(newLog)
    saveLog(newLog)
  }

  const days90 = useMemo(() => getLast90Days(), [])
  const today = todayStr()

  const byDate = useMemo(() => {
    const map: Record<string, ActivityType[]> = {}
    log.forEach(e => {
      if (!map[e.date]) map[e.date] = []
      map[e.date].push(e.type)
    })
    return map
  }, [log])

  const now = new Date()
  const thisMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const monthEntries = log.filter(e => e.date.startsWith(thisMonth))

  const ironmanThis = monthEntries.filter(e => ['run', 'bike', 'swim'].includes(e.type)).length
  const totalRunKm   = log.filter(e => e.type === 'run'  && e.distance).reduce((s, e) => s + (e.distance ?? 0), 0)
  const totalBikeKm  = log.filter(e => e.type === 'bike' && e.distance).reduce((s, e) => s + (e.distance ?? 0), 0)
  const totalSwimKm  = log.filter(e => e.type === 'swim' && e.distance).reduce((s, e) => s + (e.distance ?? 0), 0)

  let streak = 0
  for (let i = 0; i < 90; i++) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const ds = d.toISOString().slice(0, 10)
    if (byDate[ds]?.length > 0) streak++
    else if (ds !== today) break
  }

  const weeks: string[][] = []
  let week: string[] = []
  days90.forEach((d, i) => {
    week.push(d)
    if (week.length === 7 || i === days90.length - 1) { weeks.push(week); week = [] }
  })

  return (
    <main className="page page-enter">
      <div className="page-header">
        <div>
          <h1 className="page-title">Training</h1>
          <p className="page-subtitle">Ironman-Vorbereitung & Aktivitäten</p>
        </div>
        <button onClick={() => openModal()} className="btn btn-primary">+ Workout loggen</button>
      </div>

      {/* Stats */}
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        {[
          { label: 'Streak',         value: `${streak} Tage`,              sub: 'am Stück'         },
          { label: 'Ironman (Mnt)',  value: String(ironmanThis),            sub: 'Swim / Bike / Run' },
          { label: 'Gelaufen',       value: `${totalRunKm.toFixed(0)} km`, sub: 'gesamt'           },
          { label: 'Radgefahren',    value: `${totalBikeKm.toFixed(0)} km`,sub: 'gesamt'           },
        ].map(s => (
          <div key={s.label} className="card card-sm">
            <p className="stat-label">{s.label}</p>
            <p style={{ fontSize: '1.5rem', fontWeight: 800, marginTop: '.25rem' }}>{s.value}</p>
            <p style={{ fontSize: '.7rem', color: 'var(--text-3)', marginTop: '.15rem' }}>{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Quick log */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '.85rem', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '.85rem' }}>
          Schnell loggen
        </h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.5rem' }}>
          {ACTIVITIES.map(a => (
            <button
              key={a.type}
              onClick={() => openModal(a.type)}
              style={{
                padding: '.5rem 1rem', borderRadius: 20, fontSize: '.875rem', fontWeight: 600,
                border: `1px solid ${a.ironman ? 'var(--teal-muted)' : 'var(--border)'}`,
                background: a.ironman ? 'var(--teal-light)' : 'transparent',
                color: a.ironman ? 'var(--teal)' : 'var(--text-2)',
                cursor: 'pointer',
              }}
            >
              {a.emoji} {a.label}
            </button>
          ))}
        </div>
        <p style={{ fontSize: '.72rem', color: 'var(--text-3)', marginTop: '.6rem' }}>Rot markiert = Ironman-Disziplinen</p>
      </div>

      <div className="grid-main-sidebar">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

          {/* Heatmap */}
          <div className="card">
            <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>Letzte 90 Tage</h2>
            <div style={{ display: 'flex', gap: 3, overflowX: 'auto', paddingBottom: '.25rem' }}>
              {weeks.map((wk, wi) => (
                <div key={wi} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {wk.map(d => {
                    const types = byDate[d] ?? []
                    return (
                      <div
                        key={d}
                        title={`${dateLabel(d)}${types.length ? ': ' + types.map(t => ACTIVITIES.find(a => a.type === t)?.emoji).join(' ') : ''}`}
                        style={{
                          width: 14, height: 14, borderRadius: 3,
                          background: activityColor(types),
                          outline: d === today ? '2px solid var(--teal)' : 'none',
                          outlineOffset: 1,
                        }}
                      />
                    )
                  })}
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '.75rem', fontSize: '.7rem', color: 'var(--text-3)', flexWrap: 'wrap' }}>
              <span>⬜ Kein Training</span>
              <span style={{ color: 'rgba(22,163,74,.9)' }}>■ Ironman</span>
              <span style={{ color: 'rgba(139,26,26,.9)' }}>■ Gym</span>
              <span style={{ color: 'rgba(59,130,246,.9)' }}>■ Anderes</span>
            </div>
          </div>

          {/* Log */}
          <div className="card">
            <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>Letzte Workouts</h2>
            {log.length === 0 ? (
              <p style={{ color: 'var(--text-3)', fontSize: '.875rem', padding: '1.5rem 0', textAlign: 'center' }}>
                Noch keine Einträge — leg los!
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '.4rem' }}>
                {log.slice(0, 20).map(entry => {
                  const act = ACTIVITIES.find(a => a.type === entry.type)
                  return (
                    <div key={entry.id} style={{
                      display: 'flex', alignItems: 'center', gap: '.85rem',
                      padding: '.6rem .75rem', borderRadius: 10, border: '1px solid var(--border)',
                    }}>
                      <span style={{ fontSize: '1.3rem', lineHeight: 1 }}>{act?.emoji}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem' }}>
                          <span style={{ fontSize: '.875rem', fontWeight: 600 }}>{act?.label}</span>
                          {act?.ironman && (
                            <span className="badge badge-teal" style={{ fontSize: '.6rem', padding: '.1rem .35rem' }}>Ironman</span>
                          )}
                        </div>
                        <p style={{ fontSize: '.75rem', color: 'var(--text-3)', marginTop: '.1rem' }}>
                          {dateLabel(entry.date)}
                          {entry.duration ? ` · ${formatDuration(entry.duration)}` : ''}
                          {entry.distance ? ` · ${entry.distance} km` : ''}
                          {entry.notes ? ` · ${entry.notes}` : ''}
                        </p>
                      </div>
                      <button
                        onClick={() => removeEntry(entry.id)}
                        style={{ background: 'none', border: 'none', color: 'var(--text-3)', cursor: 'pointer', fontSize: '1rem', lineHeight: 1 }}
                      >×</button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>

          {/* Ironman progress */}
          <div className="card">
            <h2 style={{ fontSize: '.85rem', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '1rem' }}>
              Ironman Distanzen
            </h2>
            {[
              { emoji: '🏊', label: 'Geschwommen', km: totalSwimKm,  target: 3.8  },
              { emoji: '🚴', label: 'Geradelt',    km: totalBikeKm,  target: 180  },
              { emoji: '🏃', label: 'Gelaufen',    km: totalRunKm,   target: 42.2 },
            ].map(s => (
              <div key={s.label} style={{ marginBottom: '.9rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '.3rem' }}>
                  <span style={{ fontSize: '.85rem', fontWeight: 600 }}>{s.emoji} {s.label}</span>
                  <span style={{ fontSize: '.8rem', color: 'var(--text-3)' }}>{s.km.toFixed(1)} / {s.target} km</span>
                </div>
                <div style={{ height: 6, background: 'var(--border-soft)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', borderRadius: 3, background: 'var(--teal)',
                    width: `${Math.min(100, (s.km / s.target) * 100).toFixed(1)}%`,
                  }} />
                </div>
              </div>
            ))}
            <p style={{ fontSize: '.7rem', color: 'var(--text-3)' }}>Full Ironman: 3,8 km / 180 km / 42,2 km</p>
          </div>

          {/* This month breakdown */}
          <div className="card">
            <h2 style={{ fontSize: '.85rem', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: '.85rem' }}>
              Dieser Monat
            </h2>
            {monthEntries.length === 0 ? (
              <p style={{ fontSize: '.85rem', color: 'var(--text-3)' }}>Noch keine Einträge</p>
            ) : (
              ACTIVITIES.filter(a => monthEntries.some(e => e.type === a.type)).map(a => (
                <div key={a.type} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '.5rem' }}>
                  <span style={{ fontSize: '.875rem' }}>{a.emoji} {a.label}</span>
                  <span style={{ fontSize: '.875rem', fontWeight: 700 }}>
                    {monthEntries.filter(e => e.type === a.type).length}×
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {modal.open && (
        <LogModal
          preselected={modal.preselected}
          onSave={addEntry}
          onClose={() => setModal({ open: false, preselected: null })}
        />
      )}
    </main>
  )
}

const labelSt: React.CSSProperties = {
  fontSize: '.75rem', fontWeight: 600, color: 'var(--text-3)',
  textTransform: 'uppercase', letterSpacing: '.04em', display: 'block', marginBottom: '.3rem',
}
const inputSt: React.CSSProperties = {
  width: '100%', padding: '.45rem .6rem',
  border: '1px solid var(--border)', borderRadius: 6,
  fontSize: '.875rem', background: 'var(--surface-alt)',
  color: 'var(--text)', fontFamily: 'inherit', outline: 'none',
}
