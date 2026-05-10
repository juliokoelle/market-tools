import { useState, useRef, useEffect } from 'react'
import { NavLink, Link, useLocation } from 'react-router-dom'

const marketLinks = [
  { to: '/market',            label: 'Dashboard' },
  { to: '/market/briefing',   label: 'Briefing' },
  { to: '/market/portfolio',  label: 'Portfolio' },
  { to: '/market/hot-stocks', label: 'Hot Stocks' },
  { to: '/market/analyzer',   label: 'Stock Analyzer' },
]

const ideaLinks = [
  { to: '/ideas', label: 'All Ideas' },
]

function Dropdown({ label, links, isActive }: { label: string; links: { to: string; label: string }[]; isActive: boolean }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        className={`nav-btn${isActive ? ' nav-btn--active' : ''}`}
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        {label}
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ marginLeft: 2, transition: 'transform .15s', transform: open ? 'rotate(180deg)' : 'none' }}>
          <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
      {open && (
        <div className="nav-dropdown" onClick={() => setOpen(false)}>
          {links.map(l => (
            <NavLink key={l.to} to={l.to} className={({ isActive }) => `nav-dropdown-item${isActive ? ' active' : ''}`} end={l.to === '/market'}>
              {l.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Navigation() {
  const location = useLocation()
  const isMarket = location.pathname.startsWith('/market')
  const isIdeas  = location.pathname.startsWith('/ideas')

  return (
    <>
      <nav className="nav">
        <div className="nav-inner">
          <Link to="/" className="nav-logo">JK</Link>

          <div className="nav-links">
            <Dropdown label="Market Tools" links={marketLinks} isActive={isMarket} />
            <Dropdown label="Ideas" links={ideaLinks} isActive={isIdeas} />
          </div>
        </div>
      </nav>
      <style>{`
        .nav {
          position: sticky; top: 0; z-index: 100;
          background: rgba(255,255,255,.9);
          backdrop-filter: blur(12px);
          border-bottom: 1px solid var(--border);
        }
        .nav-inner {
          max-width: 1200px; margin: 0 auto; padding: 0 1.5rem;
          height: 56px; display: flex; align-items: center; gap: 2rem;
        }
        .nav-logo {
          font-size: 1.1rem; font-weight: 700; color: var(--primary);
          letter-spacing: -.5px;
        }
        .nav-links { display: flex; align-items: center; gap: .25rem; }
        .nav-btn {
          display: flex; align-items: center; gap: .3rem;
          padding: .4rem .75rem; border-radius: var(--radius-sm);
          font-size: .875rem; font-weight: 500;
          background: none; border: none; color: var(--text-muted);
          transition: background .15s, color .15s;
        }
        .nav-btn:hover { background: var(--surface-alt); color: var(--text); }
        .nav-btn--active { color: var(--primary); }
        .nav-dropdown {
          position: absolute; top: calc(100% + .5rem); left: 0;
          background: var(--surface); border: 1px solid var(--border);
          border-radius: var(--radius-sm); box-shadow: var(--shadow-md);
          min-width: 180px; overflow: hidden;
          animation: fadeIn .15s ease;
        }
        .nav-dropdown-item {
          display: block; padding: .6rem 1rem;
          font-size: .875rem; color: var(--text-muted);
          transition: background .1s, color .1s;
        }
        .nav-dropdown-item:hover { background: var(--surface-alt); color: var(--text); }
        .nav-dropdown-item.active { color: var(--primary); font-weight: 500; background: var(--primary-light); }
      `}</style>
    </>
  )
}
