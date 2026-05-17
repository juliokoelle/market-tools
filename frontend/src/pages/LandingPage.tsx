import { Link } from 'react-router-dom'

const projects = [
  {
    title: 'Market Tools',
    description: 'Personal finance dashboard with daily economic briefings, portfolio analysis, stock screening, and AI-powered market insights.',
    link: '/market',
    external: false,
    tags: ['FastAPI', 'React', 'Finance'],
    status: 'Live',
  },
  {
    title: 'HorseFinder',
    description: 'Equestrian event finder for Germany — search tournaments by discipline, location, and date, powered by nennung-online.de data.',
    link: 'https://horsefinder-v2.vercel.app',
    external: true,
    tags: ['FastAPI', 'React', 'Supabase'],
    status: 'Live',
  },
  {
    title: 'MyWardrobe',
    description: 'Smart wardrobe management app — catalog your clothing, build outfits, and track what you actually wear.',
    link: 'https://mywardrobe-dun.vercel.app',
    external: true,
    tags: ['React Native', 'AI'],
    status: 'Live',
  },
]

export default function LandingPage() {
  return (
    <main className="page-enter">
      {/* Hero */}
      <section style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}>
        <div className="section" style={{ paddingTop: '4rem', paddingBottom: '4rem' }}>
          <p style={{ fontSize: '.875rem', fontWeight: 600, color: 'var(--teal)', marginBottom: '.75rem', letterSpacing: '.05em', textTransform: 'uppercase' }}>
            Hey, I'm
          </p>
          <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3.25rem)', fontWeight: 800, letterSpacing: '-1.5px', lineHeight: 1.1, marginBottom: '1.25rem' }}>
            Julio Koelle
          </h1>
          <p style={{ fontSize: '1.125rem', color: 'var(--text-2)', maxWidth: 540, lineHeight: 1.65, marginBottom: '2rem' }}>
            Engineering student at KIT · Co-founder at a stealth startup in Berlin ·
            Building tools at the intersection of finance, data, and software.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <a
              href="https://www.linkedin.com/in/julio-koelle"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
              </svg>
              LinkedIn
            </a>
            <Link to="/market" className="btn btn-outline">
              Open Market Tools →
            </Link>
          </div>
        </div>
      </section>

      {/* Projects */}
      <section className="section">
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '.4rem' }}>Projects</h2>
        <p style={{ color: 'var(--text-2)', fontSize: '.9rem', marginBottom: '1.75rem' }}>
          Tools I build and use.
        </p>

        <div className="grid-3">
          {projects.map(p => (
            <ProjectCard key={p.title} {...p} />
          ))}
        </div>
      </section>
    </main>
  )
}

function ProjectCard({ title, description, link, external, tags, status }: typeof projects[0]) {
  const isComingSoon = link === '#'

  const CardContent = () => (
    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '.75rem', transition: 'box-shadow .15s, transform .15s', cursor: isComingSoon ? 'default' : 'pointer' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '.5rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>{title}</h3>
        <span className={`badge ${status === 'Live' ? 'badge-teal' : 'badge-gray'}`}>
          {status}
        </span>
      </div>
      <p style={{ fontSize: '.875rem', color: 'var(--text-2)', lineHeight: 1.6, flex: 1 }}>
        {description}
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.35rem' }}>
        {tags.map(t => (
          <span key={t} className="badge badge-gray">{t}</span>
        ))}
      </div>
      {!isComingSoon && (
        <p style={{ fontSize: '.8rem', fontWeight: 600, color: 'var(--teal)' }}>
          {external ? 'Open app →' : 'Open dashboard →'}
        </p>
      )}
    </div>
  )

  if (isComingSoon) return <CardContent />
  if (external) return (
    <a href={link} target="_blank" rel="noopener noreferrer" style={{ display: 'contents' }}>
      <CardContent />
    </a>
  )
  return (
    <Link to={link} style={{ display: 'contents' }}>
      <CardContent />
    </Link>
  )
}
