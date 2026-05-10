import { useEffect, useState } from 'react'
import { getBriefingList, getBriefing, type BriefingMeta } from '../services/api'

const BASE = import.meta.env.VITE_API_URL ?? '/api'
const GH_RAW = 'https://raw.githubusercontent.com/juliokoelle/julio-brain/main/10_Daily'

function renderMarkdown(md: string): string {
  const lines = md.split('\n')
  const out: string[] = []
  let para: string[] = []

  const inline = (t: string) =>
    t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
     .replace(/\*(.+?)\*/g, '<em>$1</em>')

  const flushPara = () => {
    if (para.length) {
      out.push(`<p>${inline(para.join(' '))}</p>`)
      para = []
    }
  }

  for (const raw of lines) {
    const line = raw.trimEnd()
    const heading = line.match(/^(#{1,6}) (.+)$/)
    if (heading) {
      flushPara()
      const lvl = heading[1].length
      out.push(`<h${lvl}>${inline(heading[2])}</h${lvl}>`)
    } else if (/^---+$/.test(line)) {
      flushPara()
      out.push('<hr>')
    } else if (line === '') {
      flushPara()
    } else {
      para.push(line)
    }
  }
  flushPara()
  return out.join('\n')
}

async function fetchFromGitHub(date: string): Promise<string> {
  const r = await fetch(`${GH_RAW}/${date}.md`)
  if (!r.ok) throw new Error(`${r.status}`)
  return renderMarkdown(await r.text())
}

export default function Briefing() {
  const today = new Date().toISOString().slice(0, 10)
  const [list, setList]           = useState<BriefingMeta[]>([])
  const [selected, setSelected]   = useState<string | null>(null)
  const [content, setContent]     = useState<string>('')
  const [loading, setLoading]     = useState(false)
  const [fromGitHub, setFromGitHub] = useState(false)

  useEffect(() => {
    getBriefingList()
      .then(data => {
        setList(data)
        setSelected(data.length > 0 ? data[0].date : today)
      })
      .catch(() => setSelected(today))
  }, [today])

  useEffect(() => {
    if (!selected) return
    setLoading(true)
    setFromGitHub(false)
    getBriefing(selected)
      .then(d => setContent(d.html || d.content))
      .catch(() =>
        fetchFromGitHub(selected)
          .then(html => { setContent(html); setFromGitHub(true) })
          .catch(() => setContent('<p style="color:var(--text-muted)">Briefing not available.</p>'))
      )
      .finally(() => setLoading(false))
  }, [selected])

  return (
    <main className="page-enter section">
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '1.5rem' }}>Daily Briefing</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '1.5rem', alignItems: 'start' }}>

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

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
            <div>
              <p style={{ fontSize: '1rem', fontWeight: 700 }}>{selected ?? '—'}</p>
              {fromGitHub && (
                <p style={{ fontSize: '.72rem', color: 'var(--text-muted)', marginTop: '.15rem' }}>
                  Loaded from GitHub (API offline)
                </p>
              )}
            </div>
            {selected && !fromGitHub && (
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
