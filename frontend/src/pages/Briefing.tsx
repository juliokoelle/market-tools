import { useEffect, useState } from 'react'
import { getBriefingList, getBriefing, type BriefingMeta } from '../services/api'

const BASE = import.meta.env.VITE_API_URL ?? '/api'

export default function Briefing() {
  const [list, setList]       = useState<BriefingMeta[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getBriefingList()
      .then(data => {
        setList(data)
        if (data.length > 0) setSelected(data[0].date)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!selected) return
    setLoading(true)
    getBriefing(selected)
      .then(d => setContent(d.html || d.content))
      .catch(() => setContent('Failed to load briefing.'))
      .finally(() => setLoading(false))
  }, [selected])

  return (
    <main className="page-enter section">
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1.5rem' }}>Daily Briefing</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '1.5rem', alignItems: 'start' }}>

        {/* Archive list */}
        <div className="card" style={{ padding: '1rem' }}>
          <p style={{ fontSize: '.75rem', fontWeight: 600, color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: '.75rem' }}>
            Archive
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.15rem' }}>
            {list.length === 0
              ? <p style={{ fontSize: '.8rem', color: 'var(--text-faint)' }}>No briefings yet.</p>
              : list.map(b => (
                <button
                  key={b.date}
                  onClick={() => setSelected(b.date)}
                  style={{
                    textAlign: 'left', padding: '.45rem .6rem', borderRadius: 6,
                    fontSize: '.85rem', border: 'none', cursor: 'pointer',
                    background: selected === b.date ? 'var(--primary-light)' : 'transparent',
                    color: selected === b.date ? 'var(--primary-dark)' : 'var(--text-muted)',
                    fontWeight: selected === b.date ? 600 : 400,
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  }}
                >
                  {b.date}
                  {b.has_pdf && <span style={{ fontSize: '.65rem', color: 'var(--text-faint)' }}>PDF</span>}
                </button>
              ))
            }
          </div>
        </div>

        {/* Briefing content */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
            <p style={{ fontSize: '1rem', fontWeight: 700 }}>{selected ?? '—'}</p>
            {selected && (
              <a
                href={`${BASE}/briefing/${selected}/pdf`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-outline"
                style={{ fontSize: '.8rem' }}
              >
                ↓ PDF
              </a>
            )}
          </div>
          {loading
            ? <p style={{ color: 'var(--text-faint)', fontSize: '.875rem' }}>Loading…</p>
            : <div className="briefing-body" dangerouslySetInnerHTML={{ __html: content }} />
          }
        </div>
      </div>

      <style>{`
        .briefing-body { font-size: .9375rem; line-height: 1.8; color: var(--text); }
        .briefing-body h1 { font-size: 1.4rem; font-weight: 800; margin: 1.5rem 0 .75rem; letter-spacing: -.5px; }
        .briefing-body h2 { font-size: 1.15rem; font-weight: 700; margin: 1.25rem 0 .6rem; border-bottom: 1px solid var(--border); padding-bottom: .3rem; }
        .briefing-body h3 { font-size: 1rem; font-weight: 600; margin: 1rem 0 .4rem; }
        .briefing-body p  { margin-bottom: .9rem; }
        .briefing-body hr { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }
        .briefing-body strong { font-weight: 700; }
        @media (max-width: 700px) {
          .briefing-body { font-size: .875rem; }
        }
      `}</style>
    </main>
  )
}
