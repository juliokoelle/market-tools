const apps = [
  {
    title: 'HorseFinder',
    description: 'Equestrian event finder for Germany. Search tournaments by discipline, location, and date. Data scraped daily from nennung-online.de.',
    url: 'https://horsefinder-v2.vercel.app',
    tags: ['FastAPI', 'React', 'Supabase'],
    status: 'Live' as const,
    emoji: '🐴',
  },
  {
    title: 'MyWardrobe',
    description: 'Smart wardrobe management — catalog your clothing, plan outfits, and discover what you actually wear.',
    url: 'https://mywardrobe-dun.vercel.app',
    tags: ['React Native', 'AI', 'Mobile'],
    status: 'Live' as const,
    emoji: '👔',
  },
  {
    title: 'Cognify IQ',
    description: 'Intelligence quotient estimator using adaptive scoring. Measures reasoning across multiple domains with normalized IQ scoring.',
    url: 'https://cognify-insight-builder.vercel.app',
    tags: ['TanStack', 'Statistics', 'React'],
    status: 'Live' as const,
    emoji: '🧠',
  },
]

export default function Ideas() {
  return (
    <main className="page-enter section">
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '.4rem' }}>Ideas</h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '.9rem', marginBottom: '2rem' }}>
        Side projects and apps I'm building.
      </p>

      <div className="grid-3">
        {apps.map(app => (
          <div key={app.title} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
              <p style={{ fontSize: '2rem' }}>{app.emoji}</p>
              <span className={`badge ${app.status === 'Live' ? 'badge-teal' : 'badge-gray'}`}>
                {app.status}
              </span>
            </div>

            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '.35rem' }}>{app.title}</h2>
              <p style={{ fontSize: '.875rem', color: 'var(--text-secondary)', lineHeight: 1.65 }}>{app.description}</p>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.35rem' }}>
              {app.tags.map(t => <span key={t} className="badge badge-gray">{t}</span>)}
            </div>

            {app.url
              ? <a href={app.url} target="_blank" rel="noopener noreferrer"
                  className="btn btn-primary" style={{ marginTop: 'auto', justifyContent: 'center' }}>
                  Open app →
                </a>
              : <div style={{ position: 'relative', marginTop: 'auto' }} className="coming-soon-wrap">
                  <button disabled className="btn btn-outline"
                    style={{ width: '100%', justifyContent: 'center', cursor: 'not-allowed', opacity: .55 }}>
                    Coming soon
                  </button>
                  <div className="coming-soon-tooltip">In development — stay tuned</div>
                </div>
            }
          </div>
        ))}

        {/* Placeholder */}
        <div className="card" style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          minHeight: 200, border: '2px dashed var(--border)',
          background: 'transparent', boxShadow: 'none', gap: '.5rem', color: 'var(--text-muted)',
        }}>
          <p style={{ fontSize: '1.75rem' }}>+</p>
          <p style={{ fontSize: '.875rem' }}>Next idea</p>
        </div>
      </div>

      <style>{`
        .coming-soon-wrap .coming-soon-tooltip {
          display: none;
          position: absolute;
          bottom: calc(100% + 6px); left: 50%;
          transform: translateX(-50%);
          background: var(--bg-elevated);
          border: 1px solid var(--border);
          border-radius: 6px;
          padding: .35rem .7rem;
          font-size: .75rem;
          color: var(--text-secondary);
          white-space: nowrap;
          box-shadow: var(--shadow-sm);
          pointer-events: none;
        }
        .coming-soon-wrap:hover .coming-soon-tooltip { display: block; }
      `}</style>
    </main>
  )
}
