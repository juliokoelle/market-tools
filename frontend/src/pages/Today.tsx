import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { getMarketPrices, getBriefingPreview } from '../services/api'

interface Task {
  id: string
  text: string
  done: boolean
}

function todayStr() { return new Date().toISOString().slice(0, 10) }
function taskKey() { return `jk_tasks_${todayStr()}` }

function loadTasks(): Task[] {
  try { return JSON.parse(localStorage.getItem(taskKey()) ?? '[]') } catch { return [] }
}

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Guten Morgen'
  if (h < 18) return 'Guten Tag'
  return 'Guten Abend'
}

function formatDate() {
  return new Date().toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
}

const MINI_TICKERS = '^GSPC,GC=F,EURUSD=X'
const MINI_META: Record<string, { label: string; prefix: string }> = {
  '^GSPC':    { label: 'S&P 500', prefix: ''  },
  'GC=F':     { label: 'Gold',    prefix: '$' },
  'EURUSD=X': { label: 'EUR/USD', prefix: ''  },
}

const QUICK_NAV = [
  { to: '/market/portfolio',  label: 'Portfolio',  desc: 'P&L & Holdings'  },
  { to: '/market/briefing',   label: 'Briefing',   desc: 'Markt-Analyse'   },
  { to: '/life/training',     label: 'Training',   desc: 'Log & Heatmap'   },
  { to: '/life/podcasts',     label: 'Podcasts',   desc: 'Summaries'       },
]

export default function Today() {
  const [tasks, setTasks] = useState<Task[]>(loadTasks)
  const [input, setInput] = useState('')
  const [prices, setPrices] = useState<Record<string, { price: number; change_pct: number }>>({})
  const [preview, setPreview] = useState<{ preview: string; date: string } | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const [trainedToday] = useState(() => {
    try {
      const entries: Array<{ date: string }> = JSON.parse(localStorage.getItem('jk_training_log') ?? '[]')
      return entries.some(e => e.date === todayStr())
    } catch { return false }
  })

  useEffect(() => {
    getMarketPrices(MINI_TICKERS).then(setPrices).catch(() => {})
    getBriefingPreview().then(setPreview).catch(() => {})
  }, [])

  useEffect(() => {
    localStorage.setItem(taskKey(), JSON.stringify(tasks))
  }, [tasks])

  function addTask() {
    const text = input.trim()
    if (!text) return
    setTasks(t => [...t, { id: crypto.randomUUID(), text, done: false }])
    setInput('')
    inputRef.current?.focus()
  }

  function toggleTask(id: string) {
    setTasks(t => t.map(x => x.id === id ? { ...x, done: !x.done } : x))
  }

  function removeTask(id: string) {
    setTasks(t => t.filter(x => x.id !== id))
  }

  const done = tasks.filter(t => t.done).length
  const total = tasks.length

  return (
    <main className="page page-enter">
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <p style={{ fontSize: '.8rem', fontWeight: 600, color: 'var(--teal)', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: '.3rem' }}>
          {formatDate()}
        </p>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, letterSpacing: '-1px', lineHeight: 1.1 }}>
            {greeting()}, Julio
          </h1>
          {total > 0 && (
            <div style={{ textAlign: 'right' }}>
              <p style={{ fontSize: '1.75rem', fontWeight: 800, lineHeight: 1, color: done === total ? 'var(--positive)' : 'var(--text)' }}>
                {done}/{total}
              </p>
              <p style={{ fontSize: '.7rem', color: 'var(--text-3)', marginTop: '.15rem' }}>Tasks</p>
            </div>
          )}
        </div>
      </div>

      <div className="grid-main-sidebar">
        {/* LEFT: Tasks + Briefing */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

          {/* Tasks */}
          <div className="card">
            <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>Aufgaben heute</h2>
            <div style={{ display: 'flex', gap: '.5rem', marginBottom: tasks.length ? '1rem' : 0 }}>
              <input
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addTask()}
                placeholder="Aufgabe hinzufügen…"
                style={{
                  flex: 1, padding: '.5rem .75rem',
                  border: '1px solid var(--border)', borderRadius: 8,
                  fontSize: '.9rem', background: 'var(--surface-alt)',
                  color: 'var(--text)', fontFamily: 'inherit', outline: 'none',
                }}
              />
              <button onClick={addTask} className="btn btn-primary" style={{ flexShrink: 0, fontSize: '.875rem' }}>
                + Add
              </button>
            </div>

            {tasks.length === 0 && (
              <p style={{ fontSize: '.875rem', color: 'var(--text-3)', padding: '1rem 0', textAlign: 'center' }}>
                Noch keine Aufgaben — leg los!
              </p>
            )}

            {tasks.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '.35rem' }}>
                {tasks.map(task => (
                  <div key={task.id} style={{
                    display: 'flex', alignItems: 'center', gap: '.7rem',
                    padding: '.5rem .6rem', borderRadius: 8,
                    border: '1px solid var(--border)',
                    background: task.done ? 'var(--surface-alt)' : 'transparent',
                  }}>
                    <button
                      onClick={() => toggleTask(task.id)}
                      style={{
                        width: 20, height: 20, borderRadius: 5, flexShrink: 0,
                        border: `2px solid ${task.done ? 'var(--positive)' : 'var(--border)'}`,
                        background: task.done ? 'var(--positive)' : 'transparent',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        cursor: 'pointer', transition: 'all .15s',
                      }}
                    >
                      {task.done && <span style={{ color: '#fff', fontSize: '10px', fontWeight: 900, lineHeight: 1 }}>✓</span>}
                    </button>
                    <span style={{
                      flex: 1, fontSize: '.9rem', lineHeight: 1.4,
                      color: task.done ? 'var(--text-3)' : 'var(--text)',
                      textDecoration: task.done ? 'line-through' : 'none',
                    }}>
                      {task.text}
                    </span>
                    <button
                      onClick={() => removeTask(task.id)}
                      style={{ background: 'none', border: 'none', color: 'var(--text-3)', fontSize: '1.1rem', cursor: 'pointer', lineHeight: 1, padding: '.1rem .3rem', borderRadius: 4 }}
                    >×</button>
                  </div>
                ))}
                {done === total && total > 0 && (
                  <p style={{ fontSize: '.8rem', color: 'var(--positive)', fontWeight: 600, textAlign: 'center', padding: '.5rem', background: 'rgba(22,163,74,.08)', borderRadius: 8, marginTop: '.25rem' }}>
                    Alle Aufgaben erledigt 🎉
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Briefing preview */}
          {preview && (
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '.75rem' }}>
                <h2 style={{ fontSize: '1rem', fontWeight: 700 }}>Market Briefing</h2>
                <Link to="/market/briefing" className="btn btn-outline" style={{ fontSize: '.8rem' }}>Vollständig →</Link>
              </div>
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '.75rem' }} />
              <p style={{
                fontSize: '.875rem', color: 'var(--text-2)', lineHeight: 1.75,
                display: '-webkit-box', WebkitBoxOrient: 'vertical',
                WebkitLineClamp: 5, overflow: 'hidden',
              }}>
                {preview.preview}
              </p>
            </div>
          )}
        </div>

        {/* RIGHT: Market mini + Training + Quick nav */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '.65rem' }}>

          {/* Market mini */}
          {Object.entries(MINI_META).map(([ticker, meta]) => {
            const d = prices[ticker]
            return (
              <Link key={ticker} to="/market" style={{ display: 'block' }}>
                <div className="card card-sm" style={{ cursor: 'pointer' }}>
                  <p className="stat-label">{meta.label}</p>
                  {d ? (
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '.5rem', marginTop: '.3rem' }}>
                      <p style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                        {meta.prefix}
                        {ticker === 'EURUSD=X' ? d.price.toFixed(4) : d.price.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                      </p>
                      <span style={{ fontSize: '.75rem', fontWeight: 700, color: d.change_pct >= 0 ? 'var(--positive)' : 'var(--negative)' }}>
                        {d.change_pct >= 0 ? '▲' : '▼'} {Math.abs(d.change_pct).toFixed(2)}%
                      </span>
                    </div>
                  ) : (
                    <div style={{ height: 26, marginTop: '.3rem', background: 'var(--border-soft)', borderRadius: 6 }} />
                  )}
                </div>
              </Link>
            )
          })}

          {/* Training status */}
          <Link to="/life/training" style={{ display: 'block' }}>
            <div className="card card-sm" style={{ cursor: 'pointer', borderColor: trainedToday ? 'rgba(22,163,74,.4)' : undefined }}>
              <p className="stat-label">Training heute</p>
              {trainedToday ? (
                <p style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--positive)', marginTop: '.3rem' }}>✓ Trainiert!</p>
              ) : (
                <p style={{ fontSize: '.85rem', color: 'var(--text-3)', marginTop: '.3rem' }}>Noch kein Log →</p>
              )}
            </div>
          </Link>

          <div style={{ height: 1, background: 'var(--border)' }} />

          {/* Quick nav */}
          {QUICK_NAV.map(l => (
            <Link key={l.to} to={l.to} style={{ display: 'block' }}>
              <div
                className="card card-sm"
                style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '.75rem' }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--teal-muted)' }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = '' }}
              >
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--teal)', flexShrink: 0 }} />
                <div>
                  <p style={{ fontSize: '.875rem', fontWeight: 600 }}>{l.label}</p>
                  <p style={{ fontSize: '.73rem', color: 'var(--text-3)', marginTop: '.05rem' }}>{l.desc}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </main>
  )
}
