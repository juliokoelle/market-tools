const apps = [
  {
    title: 'HorseFinder',
    description: 'Equestrian event finder for Germany. Search tournaments by discipline, location, and date. Data scraped daily from nennung-online.de.',
    url: 'https://horsefinder-frontend.onrender.com',
    tags: ['FastAPI', 'React', 'Supabase', 'Scraper'],
    status: 'Live' as const,
    emoji: '🐴',
  },
  {
    title: 'MyWardrobe',
    description: 'Smart wardrobe management — catalog your clothing, plan outfits, and discover what you actually wear.',
    url: null,
    tags: ['React Native', 'AI', 'Mobile'],
    status: 'In Progress' as const,
    emoji: '👔',
  },
]

export default function Ideas() {
  return (
    <main className="page-enter section">
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '.4rem' }}>Ideas</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: '.9rem', marginBottom: '2rem' }}>
        Side projects and apps I'm building.
      </p>

      <div className="grid-3">
        {apps.map(app => (
          <div key={app.title} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
              <p style={{ fontSize: '2rem' }}>{app.emoji}</p>
              <span className={`badge ${app.status === 'Live' ? 'badge-green' : 'badge-blue'}`}>
                {app.status}
              </span>
            </div>

            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '.35rem' }}>{app.title}</h2>
              <p style={{ fontSize: '.875rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>{app.description}</p>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.35rem' }}>
              {app.tags.map(t => <span key={t} className="badge badge-gray">{t}</span>)}
            </div>

            {app.url
              ? <a href={app.url} target="_blank" rel="noopener noreferrer" className="btn btn-primary" style={{ marginTop: 'auto', justifyContent: 'center' }}>
                  Open app →
                </a>
              : <button disabled className="btn btn-outline" style={{ marginTop: 'auto', cursor: 'not-allowed', opacity: .5 }}>
                  Coming soon
                </button>
            }
          </div>
        ))}

        {/* Placeholder for future ideas */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 200, border: '2px dashed var(--border)', background: 'transparent', boxShadow: 'none', gap: '.5rem', color: 'var(--text-faint)' }}>
          <p style={{ fontSize: '1.75rem' }}>+</p>
          <p style={{ fontSize: '.875rem' }}>Next idea</p>
        </div>
      </div>
    </main>
  )
}
